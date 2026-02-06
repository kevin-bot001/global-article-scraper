# -*- coding: utf-8 -*-
"""
Hotelier Indonesia 爬虫 (Sitemap 模式)
https://hotelier.id/
印尼酒店行业资讯
"""
import json
import re
from typing import List, Optional, Generator
from xml.etree import ElementTree as ET

from base_scraper import BaseScraper, Article
from config import SITE_CONFIGS


class HotelierScraper(BaseScraper):
    """
    Hotelier Indonesia 爬虫

    WordPress + Yoast SEO
    Sitemap: post-sitemap.xml ~ post-sitemap4.xml

    特性:
    - 印尼酒店行业资讯
    - 旅游目的地介绍
    - 印尼语内容
    """

    CONFIG_KEY = "hotelier"

    def __init__(self, use_proxy: bool = False):
        config = SITE_CONFIGS.get(self.CONFIG_KEY, {})

        super().__init__(
            name=config.get("name", "Hotelier Indonesia"),
            base_url=config.get("base_url", "https://hotelier.id"),
            delay=config.get("delay", 0.5),
            use_proxy=use_proxy,
            country=config.get("country", "Indonesia"),
            city=config.get("city", ""),
        )

    def get_article_list_urls(self) -> Generator[str, None, None]:
        yield "sitemap://"

    def parse_article_list(self, html: str, list_url: str) -> List[str]:
        return []

    def fetch_urls_from_sitemap(self) -> List[tuple]:
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
        if not url or "hotelier.id" not in url:
            return False

        exclude_patterns = [
            "/category/", "/tag/", "/author/", "/page/",
            "/about", "/contact", "/privacy",
            "/wp-admin/", "/wp-content/",
            "wp-json", "feed",
        ]
        url_lower = url.lower()
        if any(p in url_lower for p in exclude_patterns):
            return False

        from urllib.parse import urlparse
        parsed = urlparse(url)
        path = parsed.path.strip("/")
        if not path:
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
                                # 从 articleSection 提取分类
                                if graph_item.get("articleSection"):
                                    sections = graph_item["articleSection"]
                                    if isinstance(sections, list) and sections:
                                        result["category"] = sections[0]
                                    elif isinstance(sections, str):
                                        result["category"] = sections
                            if graph_item.get("@type") == "Person":
                                result["author"] = graph_item.get("name", "")

            except (json.JSONDecodeError, TypeError, KeyError):
                continue
        return result

    def extract_content(self, html: str) -> str:
        soup = self.parse_html(html)
        for selector in [".entry-content", ".post-content", "article"]:
            content_el = soup.select_one(selector)
            if content_el:
                for tag in content_el.find_all(["script", "style", "nav", "aside", "iframe"]):
                    tag.decompose()
                for css_sel in [".share", ".social", ".ad", ".related"]:
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
            title_el = soup.select_one("h1")
            if title_el:
                title = self.clean_text(title_el.get_text())

        if not title:
            og_title = soup.select_one("meta[property='og:title']")
            if og_title:
                title = og_title.get("content", "")

        if not title:
            return None

        content = self.extract_content(html)
        author = json_ld.get("author", "")
        publish_date = json_ld.get("datePublished", "")

        if not publish_date:
            date_el = soup.select_one("time[datetime]")
            if date_el:
                publish_date = date_el.get("datetime", "")

        # 分类：优先 JSON-LD，备选从 article class 提取
        category = json_ld.get("category", "")
        if not category:
            # 从文章容器的 class 提取 category-xxx
            article_el = soup.select_one("article[class*='category-'], .hentry[class*='category-']")
            if article_el:
                classes = " ".join(article_el.get("class", []))
                cat_match = re.search(r'category-([a-z0-9-]+)', classes)
                if cat_match:
                    # 转换 slug 为可读名称
                    cat_slug = cat_match.group(1)
                    category_map = {
                        "wisata": "Destinasi Wisata",
                        "restoran": "Restoran",
                        "best-hotel": "Best Hotel",
                        "lifestyle": "Lifestyle",
                        "general": "General",
                        "nomor-apa": "Nomor Apa",
                    }
                    category = category_map.get(cat_slug, cat_slug.replace("-", " ").title())

        tags = []
        for tag_el in soup.select(".tag-links a, a[rel='tag']"):
            tag = self.clean_text(tag_el.get_text())
            if tag and tag not in tags:
                tags.append(tag)

        images = []
        for img in soup.select(".entry-content img, article img"):
            src = img.get("src") or img.get("data-src")
            if src and not src.endswith(".svg"):
                images.append(self.absolute_url(src))

        return Article(
            url=url,
            title=title,
            content=content,
            author=author or "Hotelier Indonesia",
            publish_date=publish_date,
            category=category,
            tags=tags,
            images=images[:10],
            language="id",
            country="Indonesia",
            city=self.city,
        )
