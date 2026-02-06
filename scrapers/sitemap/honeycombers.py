# -*- coding: utf-8 -*-
"""
The Honeycombers 爬虫 (Sitemap 模式)
https://thehoneycombers.com/
亚洲生活方式指南，多城市版本
"""
import json
from typing import List, Optional, Generator
from xml.etree import ElementTree as ET

from base_scraper import BaseScraper, Article
from config import SITE_CONFIGS


class HoneycombersScraper(BaseScraper):
    """
    The Honeycombers 爬虫

    WordPress + Yoast SEO
    多城市版本: singapore, bali, hong-kong

    特性:
    - 亚洲生活方式指南
    - 餐厅、活动、生活推荐
    - 英语内容
    - 支持多城市参数
    """

    CONFIG_KEY = "honeycombers"

    def __init__(self, city: str = None, use_proxy: bool = False):
        config = SITE_CONFIGS.get(self.CONFIG_KEY, {})

        # 多城市支持
        cities_config = config.get("cities", {})
        city_slug = city or "singapore"  # URL 中用的 slug (hong-kong)
        self.city_slug = city_slug  # 保留原始 slug 用于 URL 匹配

        # 获取城市对应的国家
        country = cities_config.get(city_slug, "Singapore")
        # 城市显示名称 (Hong Kong)
        city_display = city_slug.replace("-", " ").title()

        super().__init__(
            name=config.get("name", "The Honeycombers"),
            base_url=f"https://thehoneycombers.com/{city_slug}",
            delay=config.get("delay", 0.5),
            use_proxy=use_proxy,
            country=country,
            city=city_display,
        )

        # sitemap 数量配置
        self.max_sitemaps = config.get("max_sitemaps", 8)

    def get_article_list_urls(self) -> Generator[str, None, None]:
        yield "sitemap://"

    def parse_article_list(self, html: str, list_url: str) -> List[str]:
        return []

    def fetch_urls_from_sitemap(self) -> List[tuple]:
        """从多个 post-sitemap 获取文章URL"""
        all_urls = []
        ns = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}

        # 获取 sitemap index
        index_url = f"{self.base_url}/sitemap_index.xml"
        response = self.fetch(index_url)
        if not response:
            return all_urls

        # 解析 sitemap index，获取所有 post-sitemap
        sitemap_urls = []
        try:
            root = ET.fromstring(response.text)
            for sitemap_el in root.findall(".//ns:sitemap", ns):
                loc = sitemap_el.find("ns:loc", ns)
                if loc is not None and loc.text and "post-sitemap" in loc.text:
                    sitemap_urls.append(loc.text.strip())
        except ET.ParseError as e:
            self.logger.error(f"解析 sitemap index 失败: {e}")
            # Fallback: 使用默认模式
            sitemap_urls = [f"{self.base_url}/post-sitemap.xml"]
            for i in range(2, self.max_sitemaps + 1):
                sitemap_urls.append(f"{self.base_url}/post-sitemap{i}.xml")

        # 获取每个 sitemap 的文章
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
        # 用 city_slug (hong-kong) 匹配 URL，不是 city (Hong Kong)
        if not url or f"thehoneycombers.com/{self.city_slug}" not in url.lower():
            return False

        exclude_patterns = [
            "/category/", "/tag/", "/author/", "/page/",
            "/about", "/contact", "/privacy", "/terms",
            "/events/", "/event-category/", "/job_listing/",
            "/local-legends/", "/local-legends-category/",
            "/wp-admin/", "/wp-content/",
            "wp-json", "feed",
        ]
        url_lower = url.lower()
        if any(p in url_lower for p in exclude_patterns):
            return False

        from urllib.parse import urlparse
        parsed = urlparse(url)
        path = parsed.path.strip("/")

        # 至少需要 city/slug 格式
        parts = path.split("/")
        if len(parts) < 2:
            return False

        return True

    def _parse_json_ld(self, soup) -> dict:
        result = {}
        for script in soup.select('script[type="application/ld+json"]'):
            try:
                data = json.loads(script.string or "")
                items = data if isinstance(data, list) else [data]

                for item in items:
                    if "@graph" in item:
                        for graph_item in item["@graph"]:
                            if graph_item.get("@type") in ["Article", "BlogPosting"]:
                                if graph_item.get("datePublished"):
                                    result["datePublished"] = graph_item["datePublished"]
                                if graph_item.get("headline"):
                                    result["headline"] = graph_item["headline"]
                            if graph_item.get("@type") == "Person":
                                result["author"] = graph_item.get("name", "")

            except (json.JSONDecodeError, TypeError, KeyError):
                continue
        return result

    def extract_content(self, html: str) -> str:
        soup = self.parse_html(html)
        for selector in [".entry-content", ".post-content", "article .content", "article"]:
            content_el = soup.select_one(selector)
            if content_el:
                for tag in content_el.find_all(["script", "style", "nav", "aside", "iframe"]):
                    tag.decompose()
                for css_sel in [".share", ".social", ".ad", ".related", ".newsletter", ".author-box"]:
                    for el in content_el.select(css_sel):
                        el.decompose()
                content = content_el.decode_contents()
                if len(content) > 200:
                    return content
        return ""

    def parse_article(self, html: str, url: str) -> Optional[Article]:
        soup = self.parse_html(html)
        json_ld = self._parse_json_ld(soup)

        title = json_ld.get("headline", "")
        if not title:
            title_el = soup.select_one("h1.entry-title, h1.post-title, h1")
            if title_el:
                title = self.clean_text(title_el.get_text())

        if not title:
            return None

        content = self.extract_content(html)
        author = json_ld.get("author", "")
        publish_date = json_ld.get("datePublished", "")

        if not author:
            author_el = soup.select_one(".author-name, .byline a")
            if author_el:
                author = self.clean_text(author_el.get_text())

        if not publish_date:
            date_el = soup.select_one("time[datetime], .entry-date")
            if date_el:
                publish_date = date_el.get("datetime") or self.clean_text(date_el.get_text())

        category = ""
        cat_el = soup.select_one(".cat-links a, a[rel='category tag']")
        if cat_el:
            category = self.clean_text(cat_el.get_text())

        tags = []
        for tag_el in soup.select(".tag-links a, a[rel='tag']"):
            tag = self.clean_text(tag_el.get_text())
            if tag and tag not in tags:
                tags.append(tag)

        images = []
        featured = soup.select_one(".post-thumbnail img, .featured-image img")
        if featured:
            src = featured.get("src") or featured.get("data-src")
            if src:
                images.append(self.absolute_url(src))

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
            author=author or "The Honeycombers",
            publish_date=publish_date,
            category=category,
            tags=tags,
            images=images[:10],
            language="en",
            country=self.country,
            city=self.city,
        )
