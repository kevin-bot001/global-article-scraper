# -*- coding: utf-8 -*-
"""
Bangkok Foodies Scraper (Sitemap Mode)
https://www.bangkokfoodies.com/
Bangkok food & restaurant guide blog covering reviews, events, and dining guides.
"""
import json
import re
from typing import List, Optional, Generator
from xml.etree import ElementTree as ET

from base_scraper import BaseScraper, Article
from config import SITE_CONFIGS


class BangkokFoodiesScraper(BaseScraper):
    """
    Bangkok Foodies Scraper

    WordPress + Yoast SEO Premium
    Sitemap: post-sitemap.xml (single file, ~494 articles)

    Notes:
    - Sitemap XML has PHP deprecation warnings before the XML declaration;
      we strip them before parsing.
    - JSON-LD uses Yoast @graph format with Article type.
    - Content container: div.postcontent.content
    - Title: h1.title.entry-title
    - English content, covering Bangkok and other Thai/Asian cities.
    """

    CONFIG_KEY = "bangkok_foodies"

    def __init__(self, use_proxy: bool = False):
        config = SITE_CONFIGS.get(self.CONFIG_KEY, {})

        super().__init__(
            name=config.get("name", "Bangkok Foodies"),
            base_url=config.get("base_url", "https://www.bangkokfoodies.com"),
            delay=config.get("delay", 0.5),
            use_proxy=use_proxy,
            country=config.get("country", "Thailand"),
            city=config.get("city", "Bangkok"),
        )

    def get_article_list_urls(self) -> Generator[str, None, None]:
        """Return sitemap marker"""
        yield "sitemap://"

    def parse_article_list(self, html: str, list_url: str) -> List[str]:
        """Not used in sitemap mode"""
        return []

    def fetch_urls_from_sitemap(self) -> List[tuple]:
        """Fetch article URLs from sitemap"""
        sitemap_url = f"{self.base_url}/post-sitemap.xml"

        all_urls = []
        ns = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}

        response = self.fetch(sitemap_url)
        if not response:
            self.logger.error(f"Failed to fetch sitemap: {sitemap_url}")
            return all_urls

        try:
            # Strip PHP warnings/errors before the XML declaration
            text = response.text
            xml_start = text.find("<?xml")
            if xml_start > 0:
                text = text[xml_start:]

            root = ET.fromstring(text)
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

        self.logger.info(f"Found {len(all_urls)} articles from Sitemap")
        return all_urls

    def is_valid_article_url(self, url: str) -> bool:
        """Check if URL is a valid article"""
        if not url or "bangkokfoodies.com" not in url:
            return False

        exclude_patterns = [
            "/category/", "/tag/", "/author/", "/page/",
            "/about", "/contact", "/privacy", "/terms",
            "/wp-admin/", "/wp-content/", "/wp-includes/",
            "wp-json", "feed", "xmlrpc",
            "/events/", "/mec-events/", "/section/",
            "/foodies-directory/", "/advertise",
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

        return True

    def _parse_json_ld(self, soup) -> dict:
        """Extract structured data from JSON-LD (Yoast SEO @graph format)"""
        result = {}

        for script in soup.select('script[type="application/ld+json"]'):
            try:
                data = json.loads(script.string or "")
                items = data if isinstance(data, list) else [data]

                for item in items:
                    # @graph format (Yoast SEO)
                    if "@graph" in item:
                        for graph_item in item["@graph"]:
                            item_type = graph_item.get("@type")
                            # Handle list types like ["Article", "..."]
                            if isinstance(item_type, list):
                                type_set = set(item_type)
                            else:
                                type_set = {item_type}

                            if type_set & {"Article", "NewsArticle", "BlogPosting"}:
                                if graph_item.get("datePublished"):
                                    result["datePublished"] = graph_item["datePublished"]
                                if graph_item.get("headline"):
                                    result["headline"] = graph_item["headline"]
                                # articleSection -> category
                                if graph_item.get("articleSection"):
                                    sections = graph_item["articleSection"]
                                    if isinstance(sections, str):
                                        # "What's News,Hanoi Foodies" -> first section
                                        parts = [s.strip() for s in sections.split(",")]
                                        result["category"] = parts[0]
                                    elif isinstance(sections, list) and sections:
                                        result["category"] = sections[0]
                                # keywords -> tags
                                if graph_item.get("keywords"):
                                    keywords = graph_item["keywords"]
                                    if isinstance(keywords, str):
                                        result["keywords"] = [k.strip() for k in keywords.split(",")]
                                    elif isinstance(keywords, list):
                                        result["keywords"] = keywords

                            if item_type == "Person" or (isinstance(item_type, list) and "Person" in item_type):
                                result["author"] = graph_item.get("name", "")

            except (json.JSONDecodeError, TypeError, KeyError):
                continue

        return result

    def extract_content(self, html: str) -> str:
        """Extract article body content"""
        soup = self.parse_html(html)

        # Bangkok Foodies uses div.postcontent.content
        content_selectors = [
            ".postcontent.content",
            ".postcontent",
            ".entry-content",
            ".post-content",
            "article .content",
        ]

        for selector in content_selectors:
            content_el = soup.select_one(selector)
            if content_el:
                # Remove unwanted elements
                for tag in content_el.find_all([
                    "script", "style", "nav", "aside", "iframe",
                    "noscript", "button", "form"
                ]):
                    tag.decompose()
                for css_sel in [
                    ".share", ".social", ".ad", ".advertisement",
                    ".related", ".newsletter", ".comments",
                    ".post-sharing", ".post-tags",
                    ".sharingwrap", ".sharing",
                    ".fca_eoi", ".mec-wrap",
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

        # Title - prefer JSON-LD headline
        title = json_ld.get("headline", "")
        if not title:
            title_el = soup.select_one("h1.title.entry-title, h1.entry-title, h1")
            if title_el:
                title = self.clean_text(title_el.get_text())

        if not title:
            og_title = soup.select_one("meta[property='og:title']")
            if og_title:
                title = og_title.get("content", "")
                # Remove site name suffix
                title = re.sub(r'\s*[-|]\s*Bangkok food guide\s*\|?\s*Bangkok Foodies\s*$', '', title).strip()

        if not title:
            return None

        # Content
        content = self.extract_content(html)

        # Author
        author = json_ld.get("author", "")
        if not author:
            author_el = soup.select_one(".authorinfo .fn a, a[rel='author'], .vcard .fn a")
            if author_el:
                author = self.clean_text(author_el.get_text())

        # Publish date
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
            cat_el = soup.select_one(".authorinfo a[class*='category-'], a[rel='category tag']")
            if cat_el:
                category = self.clean_text(cat_el.get_text())

        # Tags - prefer JSON-LD keywords
        tags = json_ld.get("keywords", [])
        if not tags:
            for tag_el in soup.select(".post-tags a, .tag-links a, a[rel='tag']"):
                tag = self.clean_text(tag_el.get_text())
                if tag and tag not in tags and tag.lower() != "tags":
                    tags.append(tag)

        # Images
        images = []
        # Featured image
        featured = soup.select_one(".featuredimage img, .post-thumbnail img, .featured-image img")
        if featured:
            src = featured.get("src") or featured.get("data-src")
            if src:
                images.append(self.absolute_url(src))

        # OG image as fallback
        if not images:
            og_img = soup.select_one("meta[property='og:image']")
            if og_img:
                src = og_img.get("content", "")
                if src:
                    images.append(self.absolute_url(src))

        # Content images
        for img in soup.select(".postcontent img, .entry-content img"):
            src = img.get("src") or img.get("data-src")
            if src and not src.endswith(".svg"):
                full_src = self.absolute_url(src)
                if full_src not in images:
                    images.append(full_src)

        return Article(
            url=url,
            title=title,
            content=content,
            author=author or "Bangkok Foodies",
            publish_date=publish_date,
            category=category,
            tags=tags,
            images=images[:10],
            language="en",
            country="Thailand",
            city="Bangkok",
        )
