# -*- coding: utf-8 -*-
"""
Will Fly For Food scraper (Sitemap mode)
https://www.willflyforfood.net/
Asian and global food travel guide covering restaurants, street food, and cooking experiences
"""
import json
from typing import List, Optional, Generator
from xml.etree import ElementTree as ET

from base_scraper import BaseScraper, Article
from config import SITE_CONFIGS


class WillFlyForFoodScraper(BaseScraper):
    """
    Will Fly For Food scraper

    WordPress site with standard sitemap.xml (single file, not sitemap index)
    JSON-LD @graph format with Article type

    Features:
    - Cross-regional food travel blog (Asia, Europe, Americas, etc.)
    - Restaurant guides, street food tours, cooking classes, recipes
    - English content
    - Country/city auto-detected from title/URL via detect_location_from_title
    """

    CONFIG_KEY = "will_fly_for_food"

    def __init__(self, use_proxy: bool = False):
        config = SITE_CONFIGS.get(self.CONFIG_KEY, {})

        super().__init__(
            name=config.get("name", "Will Fly For Food"),
            base_url=config.get("base_url", "https://www.willflyforfood.net"),
            delay=config.get("delay", 0.5),
            use_proxy=use_proxy,
            country=config.get("country", ""),
            city=config.get("city", ""),
        )

    def get_article_list_urls(self) -> Generator[str, None, None]:
        """Return sitemap marker"""
        yield "sitemap://"

    def parse_article_list(self, html: str, list_url: str) -> List[str]:
        """Not used in sitemap mode"""
        return []

    def fetch_urls_from_sitemap(self) -> List[tuple]:
        """Fetch article URLs from sitemap.xml (single file, not sitemap index)"""
        sitemap_url = f"{self.base_url}/sitemap.xml"

        all_urls = []
        ns = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}

        response = self.fetch(sitemap_url)
        if not response:
            self.logger.error(f"Failed to fetch sitemap: {sitemap_url}")
            return all_urls

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

        self.logger.info(f"Fetched {len(all_urls)} article URLs from sitemap")
        return all_urls

    def is_valid_article_url(self, url: str) -> bool:
        """Check if URL is a valid article (filter out non-article pages)"""
        if not url or "willflyforfood.net" not in url:
            return False

        # Exclude non-article pages
        exclude_patterns = [
            "/category/", "/tag/", "/author/", "/page/",
            "/about", "/contact", "/privacy", "/terms",
            "/disclaimer", "/blog/",
            "/wp-admin/", "/wp-content/", "/wp-includes/",
            "wp-json", "feed", "xmlrpc",
        ]
        url_lower = url.lower()
        if any(p in url_lower for p in exclude_patterns):
            return False

        # Exclude homepage
        from urllib.parse import urlparse
        parsed = urlparse(url)
        path = parsed.path.strip("/")
        if not path:
            return False

        # Exclude region/continent index pages (single segment like /asia/, /europe/)
        # These are category-like pages, not articles
        non_article_slugs = {
            "africa", "asia", "europe", "north-america", "south-america", "oceania",
            "the-traveleaters", "privacy-policy",
        }
        if path in non_article_slugs:
            return False

        return True

    def _parse_json_ld(self, soup) -> dict:
        """Extract structured data from JSON-LD (@graph format)"""
        result = {}

        for script in soup.select('script[type="application/ld+json"]'):
            try:
                data = json.loads(script.string or "")
                items = data if isinstance(data, list) else [data]

                for item in items:
                    # @graph format
                    if "@graph" in item:
                        for graph_item in item["@graph"]:
                            item_type = graph_item.get("@type")
                            # Article types
                            if item_type in ("Article", "NewsArticle", "BlogPosting"):
                                if graph_item.get("datePublished"):
                                    result["datePublished"] = graph_item["datePublished"]
                                if graph_item.get("headline"):
                                    result["headline"] = graph_item["headline"]
                                if graph_item.get("articleSection"):
                                    sections = graph_item["articleSection"]
                                    if isinstance(sections, list) and sections:
                                        result["category"] = sections[0]
                                    elif isinstance(sections, str):
                                        result["category"] = sections
                                if graph_item.get("keywords"):
                                    keywords = graph_item["keywords"]
                                    if isinstance(keywords, str):
                                        result["keywords"] = [k.strip() for k in keywords.split(",")]
                                    elif isinstance(keywords, list):
                                        result["keywords"] = keywords
                            # Standalone Article (non-graph)
                            if item_type in ("Article", "NewsArticle", "BlogPosting") and "@graph" not in item:
                                if item.get("datePublished"):
                                    result["datePublished"] = item["datePublished"]
                                if item.get("headline"):
                                    result["headline"] = item["headline"]
                                if item.get("author"):
                                    author = item["author"]
                                    if isinstance(author, dict):
                                        result["author"] = author.get("name", "")
                                    elif isinstance(author, list) and author:
                                        result["author"] = author[0].get("name", "")
                            if item_type == "Person":
                                result["author"] = graph_item.get("name", "")

            except (json.JSONDecodeError, TypeError, KeyError):
                continue

        return result

    def extract_content(self, html: str) -> str:
        """Extract article body content"""
        soup = self.parse_html(html)

        # Will Fly For Food uses .entry-content
        content_selectors = [
            ".entry-content",
            ".mvt-content",
            ".post-content",
            "article .content",
        ]

        for selector in content_selectors:
            content_el = soup.select_one(selector)
            if content_el:
                # Remove unnecessary elements
                for tag in content_el.find_all([
                    "script", "style", "nav", "aside", "iframe",
                    "noscript", "button", "form"
                ]):
                    tag.decompose()
                for css_sel in [
                    ".share", ".social", ".ad", ".advertisement",
                    ".related", ".newsletter", ".comments",
                    ".post-sharing", ".post-tags",
                    ".yarpp-related",  # Yet Another Related Posts Plugin
                ]:
                    for el in content_el.select(css_sel):
                        el.decompose()
                content = content_el.decode_contents()
                if len(content) > 200:
                    return content
        return ""

    def parse_article(self, html: str, url: str) -> Optional[Article]:
        """Parse article detail page"""
        soup = self.parse_html(html)
        json_ld = self._parse_json_ld(soup)

        # Title: JSON-LD headline > h1 > og:title
        title = json_ld.get("headline", "")
        if not title:
            title_el = soup.select_one("h1.article-heading, h1.entry-title, h1")
            if title_el:
                title = self.clean_text(title_el.get_text())

        if not title:
            og_title = soup.select_one("meta[property='og:title']")
            if og_title:
                title = og_title.get("content", "")
                # Remove site name suffix
                if title and " | " in title:
                    title = title.rsplit(" | ", 1)[0].strip()

        if not title:
            return None

        # Content
        content = self.extract_content(html)

        # Author: JSON-LD > byline elements
        author = json_ld.get("author", "")
        if not author:
            author_el = soup.select_one(".author-name a, a[rel='author'], .byline a, .post-author a")
            if author_el:
                author = self.clean_text(author_el.get_text())

        # Publish date: JSON-LD > meta tag > time element
        publish_date = json_ld.get("datePublished", "")
        if not publish_date:
            meta_date = soup.select_one("meta[property='article:published_time']")
            if meta_date:
                publish_date = meta_date.get("content", "")
        if not publish_date:
            date_el = soup.select_one("time[datetime], .entry-date, .post-date")
            if date_el:
                publish_date = date_el.get("datetime") or self.clean_text(date_el.get_text())

        # Category
        category = json_ld.get("category", "")
        if not category:
            cat_el = soup.select_one(".entry-category a, a[rel='category tag'], .post-category a")
            if cat_el:
                category = self.clean_text(cat_el.get_text())

        # Tags: JSON-LD keywords > tag links
        tags = json_ld.get("keywords", [])
        if not tags:
            for tag_el in soup.select(".post-tags a, .tag-links a, a[rel='tag']"):
                tag = self.clean_text(tag_el.get_text())
                if tag and tag not in tags and tag.lower() != "tags":
                    tags.append(tag)

        # Images
        images = []
        # Featured image
        featured = soup.select_one(".post-thumbnail img, .featured-image img, article img")
        if featured:
            src = featured.get("src") or featured.get("data-src")
            if src:
                images.append(self.absolute_url(src))

        # Content images
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
            author=author or "Will Fly for Food",
            publish_date=publish_date,
            category=category,
            tags=tags,
            images=images[:10],
            language="en",
            # country and city left empty - auto-detected by detect_location_from_title
        )
