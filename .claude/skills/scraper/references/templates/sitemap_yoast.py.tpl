# -*- coding: utf-8 -*-
"""
${site_name} Scraper (Sitemap Mode)
${base_url}
WordPress + Yoast SEO
"""
import json
from typing import List, Optional, Generator
from xml.etree import ElementTree as ET

from base_scraper import BaseScraper, Article
from config import SITE_CONFIGS


class ${class_name}(BaseScraper):
    """
    ${site_name} Scraper

    WordPress + Yoast SEO
    Sitemap: post-sitemap.xml (may have multiple: post-sitemap2.xml, etc.)

    Features:
    - JSON-LD @graph structured data
    - ${feature_1}
    """

    CONFIG_KEY = "${config_key}"

    def __init__(self, use_proxy: bool = False):
        config = SITE_CONFIGS.get(self.CONFIG_KEY, {})

        super().__init__(
            name=config.get("name", "${site_name}"),
            base_url=config.get("base_url", "${base_url}"),
            delay=config.get("delay", 0.5),
            use_proxy=use_proxy,
            country=config.get("country", "${country}"),
            default_city=config.get("default_city", "${default_city}"),
        )

        # Number of post-sitemap files to check
        self.max_sitemaps = config.get("max_sitemaps", 5)

    def get_article_list_urls(self) -> Generator[str, None, None]:
        yield "sitemap://"

    def parse_article_list(self, html: str, list_url: str) -> List[str]:
        return []

    def fetch_urls_from_sitemap(self) -> List[tuple]:
        """Fetch article URLs from multiple post-sitemaps"""
        all_urls = []
        ns = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}

        # Try sitemap index first
        index_url = f"{self.base_url}/sitemap_index.xml"
        response = self.fetch(index_url)

        sitemap_urls = []
        if response:
            try:
                root = ET.fromstring(response.text)
                for sitemap_el in root.findall(".//ns:sitemap", ns):
                    loc = sitemap_el.find("ns:loc", ns)
                    if loc is not None and loc.text and "post-sitemap" in loc.text:
                        sitemap_urls.append(loc.text.strip())
            except ET.ParseError:
                pass

        # Fallback to default pattern
        if not sitemap_urls:
            sitemap_urls = [f"{self.base_url}/post-sitemap.xml"]
            for i in range(2, self.max_sitemaps + 1):
                sitemap_urls.append(f"{self.base_url}/post-sitemap{i}.xml")

        # Fetch each sitemap
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
                self.logger.error(f"Failed to parse sitemap: {sitemap_url} - {e}")

        self.logger.info(f"Found {len(all_urls)} articles from sitemap")
        return all_urls

    def is_valid_article_url(self, url: str) -> bool:
        if not url or "${domain}" not in url:
            return False

        exclude_patterns = [
            "/category/", "/tag/", "/author/", "/page/",
            "/about", "/contact", "/privacy", "/terms",
            "/wp-admin/", "/wp-content/", "/wp-includes/",
            "wp-json", "feed", "xmlrpc",
        ]
        url_lower = url.lower()
        if any(p in url_lower for p in exclude_patterns):
            return False

        return True

    def _parse_json_ld(self, soup) -> dict:
        """Parse Yoast SEO JSON-LD @graph structure"""
        result = {}

        for script in soup.select('script[type="application/ld+json"]'):
            try:
                data = json.loads(script.string or "")
                items = data if isinstance(data, list) else [data]

                for item in items:
                    # Direct format
                    if item.get("@type") in ["Article", "BlogPosting", "NewsArticle"]:
                        if item.get("datePublished"):
                            result["datePublished"] = item["datePublished"]
                        if item.get("headline"):
                            result["headline"] = item["headline"]

                    # Author in direct format
                    if "author" in item:
                        author = item["author"]
                        if isinstance(author, dict):
                            result["author"] = author.get("name", "")
                        elif isinstance(author, str):
                            result["author"] = author

                    # @graph format (Yoast SEO)
                    if "@graph" in item:
                        for graph_item in item["@graph"]:
                            if graph_item.get("@type") in ["Article", "BlogPosting", "NewsArticle"]:
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

        # Title - prefer JSON-LD
        title = json_ld.get("headline", "")
        if not title:
            title_el = soup.select_one("h1.entry-title, h1.post-title, h1")
            if title_el:
                title = self.clean_text(title_el.get_text())

        if not title:
            return None

        content = self.extract_content(html)

        # Author - prefer JSON-LD
        author = json_ld.get("author", "")
        if not author:
            author_el = soup.select_one(".author-name, .byline a")
            if author_el:
                author = self.clean_text(author_el.get_text())

        # Date - prefer JSON-LD
        publish_date = json_ld.get("datePublished", "")
        if not publish_date:
            date_el = soup.select_one("time[datetime], .entry-date")
            if date_el:
                publish_date = date_el.get("datetime") or self.clean_text(date_el.get_text())

        # Category
        category = ""
        cat_el = soup.select_one(".cat-links a, a[rel='category tag']")
        if cat_el:
            category = self.clean_text(cat_el.get_text())

        # Tags
        tags = []
        for tag_el in soup.select(".tag-links a, a[rel='tag']"):
            tag = self.clean_text(tag_el.get_text())
            if tag and tag not in tags:
                tags.append(tag)

        # Images
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
            author=author or "${default_author}",
            publish_date=publish_date,
            category=category,
            tags=tags,
            images=images[:10],
            language="${language}",
            country=self.country,
            city=self.default_city,
        )
