# -*- coding: utf-8 -*-
"""
Bali Food & Travel 爬虫 (Sitemap 模式)
https://www.balifoodandtravel.com/

巴厘岛美食旅游网站，使用 Rank Math SEO + Elementor 构建
"""
import json
import re
from typing import List, Optional, Generator, Tuple

from base_scraper import BaseScraper, Article
from config import SITE_CONFIGS


class BaliFoodTravelScraper(BaseScraper):
    """
    Bali Food & Travel 爬虫

    Sitemap:
    - Index: /sitemap_index.xml (Rank Math SEO)
    - Posts: /post-sitemap1.xml, /post-sitemap2.xml

    URL模式:
    - 文章: /[slug]/ (直接在根目录下)
    - 排除: /place/, /package/, /page/, /category/, /user_package/, /invoice/
    """

    CONFIG_KEY = "bali_food_travel"

    def __init__(self, use_proxy: bool = False):
        config = SITE_CONFIGS.get(self.CONFIG_KEY, {})

        super().__init__(
            name=config.get("name", "Bali Food & Travel"),
            base_url=config.get("base_url", "https://www.balifoodandtravel.com"),
            delay=config.get("delay", 1.0),
            use_proxy=use_proxy,
            country=config.get("country", "Indonesia"),
            city=config.get("city", "Bali"),
        )

    def get_article_list_urls(self) -> Generator[str, None, None]:
        """生成列表页URL - 使用 sitemap 标记"""
        yield "sitemap://bali_food_travel"

    def parse_article_list(self, html: str, list_url: str) -> List[str]:
        """解析文章列表页 - sitemap 模式不使用"""
        return []

    def fetch_urls_from_sitemap(self) -> List[Tuple[str, str]]:
        """从 sitemap 获取所有文章 URL"""
        url_with_dates = []
        seen_urls = set()

        # Rank Math 生成的 post sitemap 文件
        sitemap_files = [
            f"{self.base_url}/post-sitemap1.xml",
            f"{self.base_url}/post-sitemap2.xml",
        ]

        # 解析 XML - 提取 loc 和 lastmod
        loc_pattern = re.compile(r'<url>\s*<loc>([^<]+)</loc>(?:\s*<lastmod>([^<]+)</lastmod>)?', re.DOTALL)

        for sitemap_url in sitemap_files:
            self.logger.info(f"Fetching sitemap: {sitemap_url}")
            try:
                resp = self.session.get(sitemap_url, timeout=30)
                if resp.status_code != 200:
                    self.logger.warning(f"Failed to fetch {sitemap_url}: {resp.status_code}")
                    continue

                for match in loc_pattern.finditer(resp.text):
                    url = match.group(1).strip()
                    lastmod = match.group(2).strip() if match.group(2) else ""
                    if self.is_valid_article_url(url) and url not in seen_urls:
                        url_with_dates.append((url, lastmod))
                        seen_urls.add(url)

            except Exception as e:
                self.logger.warning(f"Error fetching {sitemap_url}: {e}")
                continue

        # 按 lastmod 倒序排列
        url_with_dates.sort(key=lambda x: x[1] if x[1] else "", reverse=True)
        self.logger.info(f"Found {len(url_with_dates)} article URLs from sitemaps")
        return url_with_dates

    def is_valid_article_url(self, url: str) -> bool:
        """检查是否为有效的文章URL"""
        if not url or "balifoodandtravel.com" not in url:
            return False

        # 排除非文章页面
        exclude_patterns = [
            "/place/", "/place-city/",
            "/package/", "/user_package/",
            "/page/", "/category/", "/tag/",
            "/invoice/", "/event/", "/events/",
            "/author/", "/shop/", "/cart/", "/checkout/",
            "/my-account/", "/product/",
            "/wp-admin/", "/wp-content/", "/wp-includes/",
            "wp-json", "feed", "xmlrpc", "sitemap",
            "add-to-cart",
        ]
        url_lower = url.lower()
        if any(p in url_lower for p in exclude_patterns):
            return False

        # 排除首页
        from urllib.parse import urlparse
        parsed = urlparse(url)
        path = parsed.path.strip("/")

        if not path:
            return False

        return True

    def extract_content(self, html: str) -> str:
        """从原始 HTML 提取正文内容"""
        soup = self.parse_html(html)

        # Elementor 构建的内容区域
        content_selectors = [
            ".elementor-widget-theme-post-content",
            ".elementor-widget-text-editor .elementor-widget-container",
            ".entry-content",
            ".post-content",
            "article .content",
            "article",
        ]

        for selector in content_selectors:
            content_el = soup.select_one(selector)
            if content_el:
                # 移除不需要的元素
                for tag in content_el.find_all([
                    "script", "style", "nav", "aside", "iframe",
                    "noscript", "button", "form"
                ]):
                    tag.decompose()
                for css_sel in [
                    ".share", ".social", ".ad", ".advertisement",
                    ".related", ".newsletter", ".optin", ".cta",
                    ".elementor-toc", ".tableofcontents",
                    ".wp-block-button", ".swiper",
                    ".elementor-swiper-button",
                    ".swiper-pagination",
                ]:
                    for el in content_el.select(css_sel):
                        el.decompose()
                content = content_el.decode_contents()
                if len(content) > 200:
                    return content
        return ""

    def _parse_json_ld(self, soup) -> dict:
        """从 JSON-LD 提取结构化数据 (Rank Math SEO)"""
        result = {}

        for script in soup.select('script[type="application/ld+json"]'):
            try:
                data = json.loads(script.string or "")
                items = data if isinstance(data, list) else [data]

                for item in items:
                    if item.get("@type") in ["Article", "BlogPosting", "WebPage"]:
                        if item.get("datePublished"):
                            result["datePublished"] = item["datePublished"]
                        if item.get("dateModified"):
                            result["dateModified"] = item["dateModified"]

                    if "author" in item:
                        author = item["author"]
                        if isinstance(author, dict):
                            if author.get("name"):
                                result["author"] = author["name"]
                        elif isinstance(author, str):
                            result["author"] = author

                    # Rank Math @graph 格式
                    if "@graph" in item:
                        for graph_item in item["@graph"]:
                            if graph_item.get("@type") in ["Article", "BlogPosting", "WebPage"]:
                                if graph_item.get("datePublished"):
                                    result["datePublished"] = graph_item["datePublished"]
                            if graph_item.get("@type") == "Person" and graph_item.get("name"):
                                result["author"] = graph_item["name"]

            except (json.JSONDecodeError, TypeError, KeyError):
                continue

        return result

    def parse_article(self, html: str, url: str) -> Optional[Article]:
        """解析文章详情页"""
        soup = self.parse_html(html)

        json_ld = self._parse_json_ld(soup)

        # 标题 - 优先使用 og:title
        title = ""
        og_title = soup.select_one("meta[property='og:title']")
        if og_title:
            title = og_title.get("content", "")
            # 移除网站名称后缀
            if " - Bali Food and Travel" in title:
                title = title.replace(" - Bali Food and Travel", "")

        if not title:
            title_selectors = [
                "h1.entry-title",
                "h1.elementor-heading-title",
                ".entry-header h1",
                "article h1",
                "h1",
            ]
            for selector in title_selectors:
                title_el = soup.select_one(selector)
                if title_el:
                    title = self.clean_text(title_el.get_text())
                    if title:
                        break

        if not title:
            return None

        # 内容
        content = self.extract_content(html)

        # 作者 - 优先从 JSON-LD 获取
        author = json_ld.get("author", "")
        if not author:
            # 从 twitter:data1 获取
            twitter_author = soup.select_one("meta[name='twitter:data1']")
            if twitter_author:
                author = twitter_author.get("content", "")

        if not author:
            author_selectors = [
                "a[href*='/author/']",
                ".author-name",
                ".byline a",
                ".entry-author",
            ]
            for selector in author_selectors:
                author_el = soup.select_one(selector)
                if author_el:
                    author = self.clean_text(author_el.get_text())
                    if author:
                        break

        # 发布日期 - 优先从 JSON-LD 获取
        publish_date = json_ld.get("datePublished", "")
        if not publish_date:
            # 从 meta 标签获取
            date_meta = soup.select_one("meta[property='article:published_time']")
            if date_meta:
                publish_date = date_meta.get("content", "")

        if not publish_date:
            date_selectors = [
                "time[datetime]",
                ".entry-date",
                ".post-date",
            ]
            for selector in date_selectors:
                date_el = soup.select_one(selector)
                if date_el:
                    publish_date = date_el.get("datetime") or self.clean_text(date_el.get_text())
                    if publish_date:
                        break

        # 分类 - 从 article:section 获取
        category = ""
        section_meta = soup.select_one("meta[property='article:section']")
        if section_meta:
            category = section_meta.get("content", "")

        if not category:
            cat_selectors = [
                ".cat-links a",
                ".entry-categories a",
                "a[rel='category tag']",
            ]
            for selector in cat_selectors:
                cat_el = soup.select_one(selector)
                if cat_el:
                    category = self.clean_text(cat_el.get_text())
                    if category:
                        break

        # 标签 - 从 article:tag 获取
        tags = []
        for tag_meta in soup.select("meta[property='article:tag']"):
            tag = tag_meta.get("content", "")
            if tag and tag not in tags:
                tags.append(tag)

        if not tags:
            for tag_el in soup.select(".tag-links a, .tags a, a[rel='tag']"):
                tag = self.clean_text(tag_el.get_text())
                if tag and tag not in tags:
                    tags.append(tag)

        # 图片 - 优先从 og:image 获取
        images = []
        og_image = soup.select_one("meta[property='og:image']")
        if og_image:
            src = og_image.get("content", "")
            if src:
                images.append(src)

        # 从文章内容获取更多图片
        for img in soup.select(".elementor-widget-container img, article img"):
            src = img.get("src") or img.get("data-src") or img.get("data-lazy-src")
            if src and not src.endswith(".svg") and "data:image" not in src:
                full_src = self.absolute_url(src)
                if full_src not in images:
                    images.append(full_src)

        # 从 Elementor carousel 获取图片
        for carousel_img in soup.select(".elementor-carousel-image"):
            src = carousel_img.get("data-bg")
            if src and src not in images:
                images.append(src)

        return Article(
            url=url,
            title=title,
            content=content,
            author=author or "Bali Food & Travel",
            publish_date=publish_date,
            category=category,
            tags=tags,
            images=images[:10],
            language="en",
            country="Indonesia",
            city="Bali",
        )
