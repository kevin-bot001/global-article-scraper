# -*- coding: utf-8 -*-
"""
KL Foodie 爬虫 (Sitemap 模式)
https://klfoodie.com/
马来西亚吉隆坡美食评测网站
"""
import json
from typing import List, Optional, Generator
from xml.etree import ElementTree as ET

from base_scraper import BaseScraper, Article
from config import SITE_CONFIGS


class KLFoodieScraper(BaseScraper):
    """
    KL Foodie 爬虫

    WordPress + Yoast SEO + Jannah Theme
    Sitemap: sitemap_index.xml -> post-sitemap.xml ~ post-sitemap4.xml

    特性:
    - 马来西亚吉隆坡美食评测
    - 咖啡馆、餐厅、美食指南
    - 英语内容
    """

    CONFIG_KEY = "kl_foodie"

    def __init__(self, use_proxy: bool = False):
        config = SITE_CONFIGS.get(self.CONFIG_KEY, {})

        super().__init__(
            name=config.get("name", "KL Foodie"),
            base_url=config.get("base_url", "https://klfoodie.com"),
            delay=config.get("delay", 0.5),
            use_proxy=use_proxy,
            country=config.get("country", "Malaysia"),
            city=config.get("city", "Kuala Lumpur"),
        )

    def get_article_list_urls(self) -> Generator[str, None, None]:
        """返回 sitemap 标记"""
        yield "sitemap://"

    def parse_article_list(self, html: str, list_url: str) -> List[str]:
        """不使用列表页模式"""
        return []

    def fetch_urls_from_sitemap(self) -> List[tuple]:
        """从 Sitemap 获取文章URL"""
        # post-sitemap.xml ~ post-sitemap4.xml
        sitemap_urls = [
            f"{self.base_url}/post-sitemap.xml",
            f"{self.base_url}/post-sitemap2.xml",
            f"{self.base_url}/post-sitemap3.xml",
            f"{self.base_url}/post-sitemap4.xml",
        ]

        all_urls = []
        ns = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}

        for sitemap_url in sitemap_urls:
            response = self.fetch(sitemap_url)
            if not response:
                continue

            try:
                root = ET.fromstring(response.text)
                for url_el in root.findall(".//ns:url", ns):
                    loc = url_el.find("ns:loc", ns)
                    lastmod = url_el.find("ns:lastmod", ns)

                    if loc is not None and loc.text:
                        url = loc.text.strip()
                        if self.is_valid_article_url(url):
                            mod_date = lastmod.text.strip() if lastmod is not None and lastmod.text else ""
                            all_urls.append((url, mod_date))

            except ET.ParseError as e:
                self.logger.error(f"解析 sitemap 失败: {sitemap_url} - {e}")

        self.logger.info(f"从 Sitemap 获取到 {len(all_urls)} 篇文章")
        return all_urls

    def is_valid_article_url(self, url: str) -> bool:
        """检查是否为有效的文章URL"""
        if not url or "klfoodie.com" not in url:
            return False

        exclude_patterns = [
            "/category/", "/tag/", "/author/", "/page/",
            "/about", "/contact", "/privacy", "/terms",
            "/wp-admin/", "/wp-content/", "/wp-includes/",
            "wp-json", "feed", "xmlrpc",
            "/shop/", "/cart/", "/checkout/",
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

    def _parse_json_ld(self, soup) -> dict:
        """从 JSON-LD 提取结构化数据 (Yoast SEO @graph 格式)"""
        result = {}

        for script in soup.select('script[type="application/ld+json"]'):
            try:
                data = json.loads(script.string or "")
                items = data if isinstance(data, list) else [data]

                for item in items:
                    # @graph 格式 (Yoast SEO)
                    if "@graph" in item:
                        for graph_item in item["@graph"]:
                            item_type = graph_item.get("@type")
                            # Article 或 WebPage 类型
                            if item_type in ("Article", "WebPage", "NewsArticle", "BlogPosting"):
                                if graph_item.get("datePublished"):
                                    result["datePublished"] = graph_item["datePublished"]
                                if graph_item.get("headline"):
                                    result["headline"] = graph_item["headline"]
                                # articleSection 提取分类
                                if graph_item.get("articleSection"):
                                    sections = graph_item["articleSection"]
                                    if isinstance(sections, list) and sections:
                                        result["category"] = sections[0]
                                    elif isinstance(sections, str):
                                        result["category"] = sections
                            # Person 类型提取作者
                            if item_type == "Person":
                                if graph_item.get("name"):
                                    result["author"] = graph_item["name"]

            except (json.JSONDecodeError, TypeError, KeyError):
                continue

        return result

    def extract_content(self, html: str) -> str:
        """提取正文内容"""
        soup = self.parse_html(html)

        # Jannah Theme 使用 entry-content
        content_selectors = [
            ".entry-content",
            "div[itemprop='articleBody']",
            ".post-content",
            "article",
        ]

        for selector in content_selectors:
            content_el = soup.select_one(selector)
            if content_el:
                # 移除无用元素
                for tag in content_el.find_all([
                    "script", "style", "nav", "aside", "iframe",
                    "noscript", "button", "form"
                ]):
                    tag.decompose()
                # 移除广告和社交分享
                for css_sel in [
                    ".share", ".social", ".ad", ".advertisement",
                    ".related", ".newsletter", ".comments",
                    ".code-block", ".ez-toc-container",
                    "[id^='div-gpt-ad']",
                ]:
                    for el in content_el.select(css_sel):
                        el.decompose()
                content = content_el.decode_contents()
                if len(content) > 200:
                    return content
        return ""

    def parse_article(self, html: str, url: str) -> Optional[Article]:
        """解析文章详情页"""
        soup = self.parse_html(html)
        json_ld = self._parse_json_ld(soup)

        # 标题：优先 JSON-LD，备选 meta og:title
        title = json_ld.get("headline", "")
        if not title:
            og_title = soup.select_one("meta[property='og:title']")
            if og_title:
                title = og_title.get("content", "")
                # 移除站点名后缀 " - KL Foodie"
                if " - KL Foodie" in title:
                    title = title.replace(" - KL Foodie", "").strip()

        if not title:
            title_el = soup.select_one("h1.post-title, h1.entry-title, h1")
            if title_el:
                title = self.clean_text(title_el.get_text())

        if not title:
            return None

        # 内容
        content = self.extract_content(html)

        # 作者：优先 meta name=author，备选 JSON-LD
        author = ""
        author_meta = soup.select_one("meta[name='author']")
        if author_meta:
            author = author_meta.get("content", "")
        if not author:
            author = json_ld.get("author", "")
        if not author:
            author_el = soup.select_one(".author-name a, a[rel='author']")
            if author_el:
                author = self.clean_text(author_el.get_text())

        # 发布日期：优先 meta article:published_time，备选 JSON-LD
        publish_date = ""
        date_meta = soup.select_one("meta[property='article:published_time']")
        if date_meta:
            publish_date = date_meta.get("content", "")
        if not publish_date:
            publish_date = json_ld.get("datePublished", "")
        if not publish_date:
            date_el = soup.select_one("time[datetime], .entry-date")
            if date_el:
                publish_date = date_el.get("datetime") or self.clean_text(date_el.get_text())

        # 分类
        category = json_ld.get("category", "")
        if not category:
            cat_el = soup.select_one(".post-cat a, .entry-category a, a[rel='category tag']")
            if cat_el:
                category = self.clean_text(cat_el.get_text())

        # 标签
        tags = []
        for tag_el in soup.select(".post-tags a, .tag-links a, a[rel='tag']"):
            tag = self.clean_text(tag_el.get_text())
            if tag and tag not in tags and tag.lower() != "tags":
                tags.append(tag)

        # 图片
        images = []
        # 特色图片
        featured = soup.select_one(".single-featured-image img, .post-thumbnail img, .wp-post-image")
        if featured:
            src = featured.get("src") or featured.get("data-src")
            if src:
                images.append(self.absolute_url(src))
        # 正文图片
        for img in soup.select(".entry-content img"):
            src = img.get("src") or img.get("data-src")
            if src and not src.endswith(".svg"):
                full_src = self.absolute_url(src)
                if full_src not in images:
                    images.append(full_src)

        return Article(
            url=url,
            title=title,
            content=content,
            author=author or "KL Foodie",
            publish_date=publish_date,
            category=category,
            tags=tags,
            images=images[:10],
            language="en",
            country="Malaysia",
            city="Kuala Lumpur",
        )
