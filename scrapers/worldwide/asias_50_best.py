# -*- coding: utf-8 -*-
"""
Asia's 50 Best Restaurants Scraper (Sitemap Mode)
https://www.theworlds50best.com/stories/

World's 50 Best - Stories section
Sitemap: /stories/sitemap.xml (1600+ articles)
JSON-LD @type: Article structured data
Content in div.content within div.article
"""
import json
import re
from typing import List, Optional, Generator, Tuple
from xml.etree import ElementTree as ET

from base_scraper import BaseScraper, Article
from config import SITE_CONFIGS


class Asias50BestScraper(BaseScraper):
    """
    Asia's 50 Best Restaurants Scraper (Sitemap Mode)

    WebPuzzle CMS platform
    - Stories sitemap at /stories/sitemap.xml
    - JSON-LD @type: Article with datePublished, author, headline
    - Content in div.content inside div.article
    - Author and date in div.lead-meta (format: "Author - DD/MM/YYYY")
    - Tags in div.tags

    URL Pattern: /stories/News/<slug>.html
    """

    CONFIG_KEY = "asias_50_best"

    def __init__(self, use_proxy: bool = False):
        config = SITE_CONFIGS.get(self.CONFIG_KEY, {})
        super().__init__(
            name=config.get("name", "Asia's 50 Best Restaurants"),
            base_url=config.get("base_url", "https://www.theworlds50best.com"),
            delay=config.get("delay", 1.0),
            use_proxy=use_proxy,
            country=config.get("country", ""),
            city=config.get("city", ""),
        )
        self._article_urls_cache = None

    def get_article_list_urls(self) -> Generator[str, None, None]:
        """Return sitemap marker for sitemap mode"""
        yield "sitemap://asias_50_best"

    def parse_article_list(self, html: str, list_url: str) -> List[str]:
        """Not used in sitemap mode"""
        return []

    def fetch_urls_from_sitemap(self) -> List[Tuple[str, str]]:
        """
        Fetch article URLs from /stories/sitemap.xml

        Returns:
            [(url, lastmod), ...] sorted by lastmod descending
        """
        if self._article_urls_cache is not None:
            return self._article_urls_cache

        url_with_dates = []
        ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

        sitemap_url = f"{self.base_url}/stories/sitemap.xml"
        response = self.fetch(sitemap_url)
        if not response:
            self.logger.error(f"Failed to fetch sitemap: {sitemap_url}")
            return url_with_dates

        try:
            root = ET.fromstring(response.content)
            for url_el in root.findall(".//sm:url", ns):
                loc = url_el.find("sm:loc", ns)
                lastmod = url_el.find("sm:lastmod", ns)

                if loc is not None and loc.text:
                    url = loc.text.strip()
                    if self.is_valid_article_url(url):
                        mod_date = lastmod.text.strip() if lastmod is not None and lastmod.text else ""
                        url_with_dates.append((url, mod_date))

        except ET.ParseError as e:
            self.logger.error(f"Failed to parse sitemap: {e}")

        # Sort by lastmod descending (newest first)
        url_with_dates.sort(key=lambda x: x[1] if x[1] else "", reverse=True)
        self._article_urls_cache = url_with_dates

        self.logger.info(f"Found {len(url_with_dates)} articles from sitemap")
        return url_with_dates

    def is_valid_article_url(self, url: str) -> bool:
        """Check if URL is a valid article URL"""
        if not url or "theworlds50best.com" not in url:
            return False

        # Must be a stories article
        if "/stories/" not in url:
            return False

        # Must end with .html
        if not url.endswith(".html"):
            return False

        # Exclude non-article pages
        exclude_patterns = [
            "/Authors.html",
            "/thank-you.html",
            "/partners/",
            "/filestore/",
            "/tags/",
            "/dashboard",
        ]
        if any(p in url for p in exclude_patterns):
            return False

        return True

    def _parse_json_ld(self, soup) -> dict:
        """
        Parse JSON-LD structured data

        Returns:
            Dict with headline, datePublished, author, description, image
        """
        result = {}

        for script in soup.select('script[type="application/ld+json"]'):
            try:
                data = json.loads(script.string or "")
                if not isinstance(data, dict):
                    continue

                # Direct Article format
                if data.get("@type") == "Article":
                    if data.get("headline"):
                        result["headline"] = data["headline"]
                    if data.get("datePublished"):
                        result["datePublished"] = data["datePublished"]
                    if data.get("description"):
                        result["description"] = data["description"]
                    if data.get("image"):
                        result["image"] = data["image"]

                    # Author
                    author = data.get("author")
                    if isinstance(author, dict):
                        result["author"] = author.get("name", "")
                    elif isinstance(author, str):
                        result["author"] = author

            except (json.JSONDecodeError, TypeError, KeyError):
                continue

        return result

    def extract_content(self, html: str) -> str:
        """
        Extract main content from HTML

        Content structure: div.article > div.content > p tags
        """
        soup = self.parse_html(html)

        content_el = soup.select_one("div.article div.content")
        if not content_el:
            content_el = soup.select_one("div.content")

        if content_el:
            # Remove unwanted elements
            for tag in content_el.find_all([
                "script", "style", "nav", "aside", "iframe",
                "noscript", "button", "form"
            ]):
                tag.decompose()

            # Remove newsletter, tags, social elements
            for css_sel in [
                ".newsletter-wrapper", ".tags", ".social",
                ".share", ".newsletter", ".bookmark-btn-container",
                ".ad", ".advertisement",
            ]:
                for el in content_el.select(css_sel):
                    el.decompose()

            content = content_el.decode_contents()
            # Remove HTML comments
            content = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)
            content = re.sub(r'\n{3,}', '\n\n', content)
            content = content.strip()
            if len(content) > 100:
                return content

        return ""

    def parse_article(self, html: str, url: str) -> Optional[Article]:
        """Parse article detail page"""
        soup = self.parse_html(html)

        # Parse JSON-LD structured data
        json_ld = self._parse_json_ld(soup)

        # Title - prefer JSON-LD, fallback to h1, then og:title
        title = json_ld.get("headline", "")
        if not title:
            h1 = soup.find("h1")
            if h1:
                title = self.clean_text(h1.get_text())

        if not title:
            og_title = soup.select_one("meta[property='og:title']")
            if og_title:
                title = og_title.get("content", "")

        if not title:
            return None

        # Content
        content = self.extract_content(html)

        # Author - prefer JSON-LD, fallback to lead-meta
        author = json_ld.get("author", "")
        if not author:
            lead_meta = soup.find("div", class_="lead-meta")
            if lead_meta:
                meta_text = lead_meta.get_text().strip()
                # Format: "Author Name - DD/MM/YYYY"
                if " - " in meta_text:
                    author = meta_text.rsplit(" - ", 1)[0].strip()

        # Publish date - prefer JSON-LD, fallback to lead-meta
        publish_date = json_ld.get("datePublished", "")
        if not publish_date:
            lead_meta = soup.find("div", class_="lead-meta")
            if lead_meta:
                meta_text = lead_meta.get_text().strip()
                # Format: "Author Name - DD/MM/YYYY"
                if " - " in meta_text:
                    date_str = meta_text.rsplit(" - ", 1)[1].strip()
                    # Convert DD/MM/YYYY to YYYY-MM-DD
                    match = re.match(r'(\d{2})/(\d{2})/(\d{4})', date_str)
                    if match:
                        day, month, year = match.groups()
                        publish_date = f"{year}-{month}-{day}"

        # Category - derive from URL path
        category = ""
        if "/stories/News/" in url:
            category = "News"
        elif "/stories/Events/" in url:
            category = "Events"

        # Tags
        tags = []
        tags_div = soup.find("div", class_="tags")
        if tags_div:
            for tag_a in tags_div.find_all("a"):
                tag = self.clean_text(tag_a.get_text())
                if tag and tag not in tags:
                    tags.append(tag)

        # Images
        images = []
        # JSON-LD image
        json_ld_image = json_ld.get("image", "")
        if json_ld_image:
            if isinstance(json_ld_image, str):
                images.append(json_ld_image)
            elif isinstance(json_ld_image, list) and json_ld_image:
                images.append(json_ld_image[0])

        # og:image fallback
        if not images:
            og_image = soup.select_one("meta[property='og:image']")
            if og_image and og_image.get("content"):
                images.append(og_image["content"])

        # Hero image
        hero_img = soup.find("img", class_="vibrant-image")
        if hero_img:
            src = hero_img.get("src", "")
            if src:
                # Fix protocol-relative URLs
                if src.startswith("//"):
                    src = "https:" + src
                if src not in images:
                    images.append(src)

        # Content images
        content_div = soup.select_one("div.article div.content")
        if content_div:
            for img in content_div.find_all("img"):
                src = img.get("src") or img.get("data-src")
                if src:
                    if src.startswith("//"):
                        src = "https:" + src
                    elif not src.startswith("http"):
                        src = self.absolute_url(src)
                    if src not in images and not src.endswith(".svg"):
                        images.append(src)

        return Article(
            url=url,
            title=title,
            content=content,
            author=author or "50 Best",
            publish_date=publish_date,
            category=category,
            tags=tags,
            images=images[:10],
            language="en",
            country="",  # International site, detect from title/url
            city="",
        )
