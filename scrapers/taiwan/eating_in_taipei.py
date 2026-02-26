# -*- coding: utf-8 -*-
"""
Eating in Taipei 爬虫 (Sitemap 模式)
https://eatingintaipei.com/
台北美食博客，英国人在台湾的美食探索指南
使用 curl_cffi 绕过 Cloudflare
"""
import json
import re
from typing import List, Optional, Generator, Tuple

from base_scraper import BaseScraper, Article
from config import SITE_CONFIGS


class EatingInTaipeiScraper(BaseScraper):
    """
    Eating in Taipei 爬虫

    Sitemap:
    - Index: /sitemap_index.xml (Rank Math SEO)
    - Posts: /post-sitemap1.xml, /post-sitemap2.xml

    URL模式:
    - 详情页: /[slug]/ (文章直接在根目录下)
    """

    CONFIG_KEY = "eating_in_taipei"

    def __init__(self, use_proxy: bool = False):
        config = SITE_CONFIGS.get(self.CONFIG_KEY, {})

        super().__init__(
            name=config.get("name", "Eating in Taipei"),
            base_url=config.get("base_url", "https://eatingintaipei.com"),
            delay=config.get("delay", 1.0),
            use_proxy=use_proxy,
            country=config.get("country", "Taiwan"),
            city=config.get("city", "Taipei"),
        )

    def get_article_list_urls(self) -> Generator[str, None, None]:
        """生成列表页URL - 使用 sitemap 标记"""
        yield "sitemap://eating_in_taipei"

    def parse_article_list(self, html: str, list_url: str) -> List[str]:
        """解析文章列表页 - sitemap 模式不使用"""
        return []

    def fetch_urls_from_sitemap(self) -> List[Tuple[str, str]]:
        """从 sitemap 获取所有文章 URL"""
        url_with_dates = []
        seen_urls = set()

        # Rank Math SEO 生成的 post-sitemap 文件
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
        if not url or "eatingintaipei.com" not in url:
            return False

        # 排除非文章页
        exclude_patterns = [
            "/category/", "/author/", "/tag/",
            "/about-me/", "/contact/", "/posts/",
            "/privacy-policy/", "/page/",
            "/wp-admin/", "/wp-content/", "/wp-includes/",
            "wp-json", "feed", "xmlrpc", "sitemap",
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

        content_selectors = [
            ".entry-content",
            ".post-content",
            "article .content",
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
                # 移除常见的广告、分享、订阅等元素
                for css_sel in [
                    ".share", ".social", ".ad", ".advertisement",
                    ".related", ".newsletter", ".optin", ".cta",
                    ".rank-math-toc", ".tableofcontents", ".toc",
                    ".wp-block-button", ".swiper",
                    ".ast-single-related-posts-container",
                    ".a2a_kit", ".addtoany",  # 分享按钮
                    "[class*='convertkit']",  # 邮件订阅
                    ".post-navigation", ".nav-links",  # 导航
                    ".comments-area",  # 评论区
                    "ins.adsbygoogle",  # Google 广告
                ]:
                    for el in content_el.select(css_sel):
                        el.decompose()
                content = content_el.decode_contents()
                if len(content) > 200:
                    return content
        return ""

    def _parse_json_ld(self, soup) -> dict:
        """从 JSON-LD 提取结构化数据"""
        result = {}

        for script in soup.select('script[type="application/ld+json"]'):
            try:
                data = json.loads(script.string or "")
                items = data if isinstance(data, list) else [data]

                for item in items:
                    # 跳过非字典类型
                    if not isinstance(item, dict):
                        continue

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
                        elif isinstance(author, list) and len(author) > 0 and isinstance(author[0], dict):
                            if author[0].get("name"):
                                result["author"] = author[0]["name"]
                        elif isinstance(author, str):
                            result["author"] = author

                    # Rank Math SEO @graph 格式
                    if "@graph" in item:
                        for graph_item in item["@graph"]:
                            if not isinstance(graph_item, dict):
                                continue
                            if graph_item.get("@type") in ["Article", "BlogPosting", "WebPage"]:
                                if graph_item.get("datePublished"):
                                    result["datePublished"] = graph_item["datePublished"]
                                if graph_item.get("dateModified"):
                                    result["dateModified"] = graph_item["dateModified"]
                            if graph_item.get("@type") == "Person" and graph_item.get("name"):
                                result["author"] = graph_item["name"]

            except (json.JSONDecodeError, TypeError, KeyError, AttributeError):
                continue

        return result

    def parse_article(self, html: str, url: str) -> Optional[Article]:
        """解析文章详情页"""
        soup = self.parse_html(html)

        json_ld = self._parse_json_ld(soup)

        # 标题
        title = ""
        title_selectors = [
            "h1.entry-title",
            "article h1",
            ".entry-header h1",
            "h1",
        ]
        for selector in title_selectors:
            title_el = soup.select_one(selector)
            if title_el:
                title = self.clean_text(title_el.get_text())
                if title:
                    break

        if not title:
            og_title = soup.select_one("meta[property='og:title']")
            if og_title:
                title = og_title.get("content", "")

        if not title:
            return None

        # 内容
        content = self.extract_content(html)

        # 作者
        author = json_ld.get("author", "")
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

        # 发布日期
        publish_date = json_ld.get("datePublished", "")
        if not publish_date:
            date_selectors = [
                "time[datetime]",
                ".entry-date",
                ".post-date",
                "meta[property='article:published_time']",
            ]
            for selector in date_selectors:
                date_el = soup.select_one(selector)
                if date_el:
                    publish_date = date_el.get("datetime") or date_el.get("content") or self.clean_text(date_el.get_text())
                    if publish_date:
                        break

        # 分类 - 从面包屑或分类链接获取
        category = ""
        # 优先从面包屑获取
        breadcrumb = soup.select(".rank-math-breadcrumb a, nav.breadcrumbs a, .ast-breadcrumbs-crumbs a")
        if len(breadcrumb) >= 2:
            # 第二个面包屑通常是分类
            category = self.clean_text(breadcrumb[1].get_text())
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

        # 标签
        tags = []
        for tag_el in soup.select(".tag-links a, .tags a, a[rel='tag']"):
            tag = self.clean_text(tag_el.get_text())
            if tag and tag not in tags:
                tags.append(tag)

        # 图片
        images = []
        # 特色图片
        featured = soup.select_one(".post-thumbnail img, .featured-image img, .wp-post-image")
        if featured:
            src = featured.get("src") or featured.get("data-src")
            if src:
                images.append(self.absolute_url(src))

        # 内容中的图片
        for img in soup.select(".entry-content img, article img, figure img"):
            src = img.get("src") or img.get("data-src") or img.get("data-lazy-src")
            if src and not src.endswith(".svg"):
                full_src = self.absolute_url(src)
                if full_src not in images:
                    images.append(full_src)

        return Article(
            url=url,
            title=title,
            content=content,
            author=author or "Eating in Taipei",
            publish_date=publish_date,
            category=category,
            tags=tags,
            images=images[:10],
            language="en",
            country="Taiwan",
            city="Taipei",
        )
