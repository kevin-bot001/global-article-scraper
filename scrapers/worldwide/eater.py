# -*- coding: utf-8 -*-
"""
Eater Scraper (Sitemap Mode)
https://www.eater.com

Vox Media food publication covering restaurants, dining, food news worldwide.
Supports city subdomains (ny.eater.com, la.eater.com, etc.)

Sitemap Index: /sitemaps (contains links to child sitemaps)
  -> child sitemaps at /sitemaps/entries/YYYY/M, /sitemaps/groups, etc.

JSON-LD @type: NewsArticle with headline, datePublished, author, articleSection, keywords
Content: .duet--layout--entry-body-container

URL Patterns (articles):
  - /category/numericid/slug  (e.g. /dining-out/940702/slug)
  - /numericid/slug           (e.g. /22904373/slug, legacy format)
  - /YYYY/M/D/numericid/slug  (e.g. /2025/3/12/24383517/slug)

Non-article URLs to exclude:
  - /venue/id/slug        (restaurant venue pages, ~97% of sitemap)
  - /neighborhood/id/slug (neighborhood listing pages, ~1%)
"""
import json
import re
from typing import List, Optional, Tuple, Generator
from xml.etree import ElementTree as ET

from base_scraper import BaseScraper, Article
from config import SITE_CONFIGS


class EaterScraper(BaseScraper):
    """
    Eater Scraper (Sitemap Mode)

    Vox Media platform with monthly article sitemaps.
    JSON-LD NewsArticle for structured metadata.
    Content in .duet--layout--entry-body-container.
    """

    CONFIG_KEY = "eater"

    def __init__(self, use_proxy: bool = False):
        config = SITE_CONFIGS.get(self.CONFIG_KEY, {})
        super().__init__(
            name=config.get("name", "Eater"),
            base_url=config.get("base_url", "https://www.eater.com"),
            delay=config.get("delay", 0.5),
            use_proxy=use_proxy,
            country=config.get("country", ""),
            city=config.get("city", ""),
        )
        self._article_urls_cache = None

    def get_article_list_urls(self) -> Generator[str, None, None]:
        """Sitemap mode - not used for list URLs"""
        yield "sitemap://eater"

    def parse_article_list(self, html: str, list_url: str) -> List[str]:
        """Not used in sitemap mode"""
        return []

    def fetch_urls_from_sitemap(self) -> List[Tuple[str, str]]:
        """
        Fetch article URLs from sitemap index -> monthly sitemaps.

        Returns:
            [(url, lastmod), ...] sorted by lastmod descending
        """
        if self._article_urls_cache is not None:
            return self._article_urls_cache

        ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        url_with_dates = []

        # Step 1: Fetch sitemap index
        index_url = f"{self.base_url}/sitemaps"
        response = self.fetch(index_url)
        if not response:
            self.logger.error(f"Failed to fetch sitemap index: {index_url}")
            return url_with_dates

        try:
            root = ET.fromstring(response.content)
        except ET.ParseError as e:
            self.logger.error(f"Failed to parse sitemap index: {e}")
            return url_with_dates

        # Collect monthly sitemap URLs
        sitemap_urls = []
        for sitemap_el in root.findall(".//sm:sitemap", ns):
            loc = sitemap_el.find("sm:loc", ns)
            if loc is not None and loc.text:
                sitemap_urls.append(loc.text.strip())

        self.logger.info(f"Found {len(sitemap_urls)} monthly sitemaps")

        # Sort by date (newest first) - filenames are article-YYYY-MM.xml
        sitemap_urls.sort(reverse=True)

        # Step 2: Fetch each monthly sitemap (limit to recent ones for efficiency)
        max_sitemaps = SITE_CONFIGS.get(self.CONFIG_KEY, {}).get("max_sitemaps", 24)
        for i, sitemap_url in enumerate(sitemap_urls[:max_sitemaps]):
            self.logger.info(
                f"Fetching sitemap {i + 1}/{min(len(sitemap_urls), max_sitemaps)}: "
                f"{sitemap_url.split('/')[-1]}"
            )
            resp = self.fetch(sitemap_url)
            if not resp:
                continue

            try:
                sm_root = ET.fromstring(resp.content)
                for url_el in sm_root.findall(".//sm:url", ns):
                    loc = url_el.find("sm:loc", ns)
                    lastmod = url_el.find("sm:lastmod", ns)

                    if loc is not None and loc.text:
                        url = loc.text.strip()
                        if self.is_valid_article_url(url):
                            mod_date = (
                                lastmod.text.strip()
                                if lastmod is not None and lastmod.text
                                else ""
                            )
                            url_with_dates.append((url, mod_date))
            except ET.ParseError as e:
                self.logger.error(f"Failed to parse sitemap {sitemap_url}: {e}")

        # Sort by lastmod descending
        url_with_dates.sort(key=lambda x: x[1] if x[1] else "", reverse=True)
        self._article_urls_cache = url_with_dates

        self.logger.info(f"Found {len(url_with_dates)} articles from sitemaps")
        return url_with_dates

    def is_valid_article_url(self, url: str) -> bool:
        """Check if URL is a valid Eater article (not venue/neighborhood)"""
        if not url or "eater.com" not in url:
            return False

        # Exclude non-article page types (venue/neighborhood are 98%+ of sitemap)
        exclude_patterns = [
            "/venue/",
            "/neighborhood/",
            "/authors/",
            "/pages/",
            "/about",
            "/contact",
            "/privacy",
            "/terms",
            "/advertise",
            "/newsletters",
            "/rss",
            "/archives",
            "/press",
        ]
        if any(p in url for p in exclude_patterns):
            return False

        # Must have a numeric ID in path (article pattern: /section/numericid/slug)
        if re.search(r"/\d{4,}/", url):
            return True

        return False

    def _parse_json_ld(self, soup) -> dict:
        """Extract data from JSON-LD NewsArticle schema"""
        for script in soup.select('script[type="application/ld+json"]'):
            try:
                data = json.loads(script.string or "")
                if not isinstance(data, dict):
                    continue
                if data.get("@type") == "NewsArticle":
                    return data
            except (json.JSONDecodeError, TypeError, KeyError):
                continue
        return {}

    def extract_content(self, html: str) -> str:
        """
        Extract article body from .duet--layout--entry-body-container
        """
        soup = self.parse_html(html)

        content_el = soup.select_one(".duet--layout--entry-body-container")
        if not content_el:
            # Fallback
            content_el = soup.select_one("article")

        if content_el:
            # Remove unwanted elements
            for tag in content_el.find_all([
                "script", "style", "nav", "aside", "iframe",
                "noscript", "button", "form", "footer",
            ]):
                tag.decompose()

            # Remove ads, newsletter, related content
            for css_sel in [
                ".newsletter", ".ad", ".advertisement", ".related",
                ".social", ".share", "[data-concert-ads]",
            ]:
                for el in content_el.select(css_sel):
                    el.decompose()

            content = content_el.decode_contents()
            # Clean up excessive whitespace
            content = re.sub(r"\n{3,}", "\n\n", content)
            content = content.strip()
            if len(content) > 200:
                return content

        return ""

    def parse_article(self, html: str, url: str) -> Optional[Article]:
        """Parse Eater article page"""
        soup = self.parse_html(html)

        # Extract JSON-LD metadata
        json_ld = self._parse_json_ld(soup)

        # Title
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

        # Author - from JSON-LD (array format)
        author = ""
        authors_data = json_ld.get("author", [])
        if isinstance(authors_data, list) and authors_data:
            author = authors_data[0].get("name", "")
        elif isinstance(authors_data, dict):
            author = authors_data.get("name", "")
        if not author:
            author_meta = soup.select_one("meta[name='author']")
            if author_meta:
                author = author_meta.get("content", "")

        # Publish date
        publish_date = json_ld.get("datePublished", "")
        if not publish_date:
            date_meta = soup.select_one("meta[property='article:published_time']")
            if date_meta:
                publish_date = date_meta.get("content", "")

        # Category - from articleSection
        category = json_ld.get("articleSection", "")

        # Tags - from keywords
        tags = []
        keywords = json_ld.get("keywords", [])
        if isinstance(keywords, list):
            tags = [k for k in keywords if k]
        elif isinstance(keywords, str):
            tags = [k.strip() for k in keywords.split(",") if k.strip()]

        # Images - from JSON-LD
        images = []
        img_data = json_ld.get("image", [])
        if isinstance(img_data, list):
            for img in img_data:
                if isinstance(img, dict):
                    img_url = img.get("url", "")
                    if img_url and img_url not in images:
                        images.append(img_url)
                elif isinstance(img, str) and img not in images:
                    images.append(img)
        elif isinstance(img_data, dict):
            img_url = img_data.get("url", "")
            if img_url:
                images.append(img_url)

        # og:image fallback
        og_image = soup.select_one("meta[property='og:image']")
        if og_image:
            img_url = og_image.get("content", "")
            if img_url and img_url not in images:
                images.append(img_url)

        return Article(
            url=url,
            title=title,
            content=content,
            author=author or "Eater",
            publish_date=publish_date,
            category=category,
            tags=tags,
            images=images[:10],
            language="en",
            country="",  # International site
            city="",
        )
