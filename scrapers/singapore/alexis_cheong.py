# -*- coding: utf-8 -*-
"""
Alexis Cheong Scraper (Sitemap Mode)
https://www.alexischeong.com
Singapore Food Blog (Blogger platform)

Blogger (Google) platform
Sitemap Index: /sitemap.xml -> /sitemap.xml?page=1, /sitemap.xml?page=2
URL Pattern: /YYYY/MM/post-slug.html

No JSON-LD structured data.
Date from .entry-meta text: "Monday, 29 December 2025"
Content in div.post-body
"""
import re
from typing import List, Optional, Generator, Tuple
from xml.etree import ElementTree

from base_scraper import BaseScraper, Article
from config import SITE_CONFIGS


class AlexisCheongScraper(BaseScraper):
    """
    Alexis Cheong Scraper (Sitemap Mode)

    Blogger platform - no JSON-LD, no Yoast SEO
    - Date from .entry-meta text (e.g. "Monday, 29 December 2025")
    - Content in div.post-body
    - Images hosted on blogger.googleusercontent.com

    URL Pattern: /YYYY/MM/post-slug.html
    """

    CONFIG_KEY = "alexis_cheong"

    def __init__(self, use_proxy: bool = False):
        config = SITE_CONFIGS.get(self.CONFIG_KEY, {})
        super().__init__(
            name=config.get("name", "Alexis Cheong"),
            base_url=config.get("base_url", "https://www.alexischeong.com"),
            delay=config.get("delay", 0.5),
            use_proxy=use_proxy,
            country=config.get("country", "Singapore"),
            city=config.get("city", "Singapore"),
        )
        self._article_urls_cache = None

    def get_article_list_urls(self) -> Generator[str, None, None]:
        """Generate list page URLs - use special marker for sitemap mode"""
        yield "sitemap://alexis_cheong"

    def parse_article_list(self, html: str, list_url: str) -> List[str]:
        """Parse article list page - not used in sitemap mode"""
        return []

    def fetch_urls_from_sitemap(self) -> List[Tuple[str, str]]:
        """
        Fetch article URLs from Blogger paginated sitemaps

        Blogger sitemap structure:
        - /sitemap.xml -> sitemap index with /sitemap.xml?page=1, ?page=2, etc.
        - Each page sitemap contains <url> entries with <loc> and <lastmod>

        Returns:
            [(url, lastmod), ...] sorted by lastmod descending
        """
        if self._article_urls_cache is not None:
            return self._article_urls_cache

        url_with_dates = []
        ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

        # Fetch sitemap index
        index_url = f"{self.base_url}/sitemap.xml"
        response = self.fetch(index_url)

        sitemap_urls = []
        if response:
            try:
                root = ElementTree.fromstring(response.content)
                # Check if this is a sitemap index (contains <sitemap> elements)
                for sitemap_el in root.findall(".//sm:sitemap", ns):
                    loc = sitemap_el.find("sm:loc", ns)
                    if loc is not None and loc.text:
                        sitemap_urls.append(loc.text.strip())
            except ElementTree.ParseError:
                pass

        # Fallback: try paginated sitemaps directly
        if not sitemap_urls:
            sitemap_urls = [
                f"{self.base_url}/sitemap.xml?page=1",
                f"{self.base_url}/sitemap.xml?page=2",
            ]

        self.logger.info(f"Found {len(sitemap_urls)} sitemaps")

        # Fetch each sitemap page
        for sitemap_url in sitemap_urls:
            response = self.fetch(sitemap_url)
            if not response:
                continue

            try:
                root = ElementTree.fromstring(response.content)
                for url_el in root.findall(".//sm:url", ns):
                    loc = url_el.find("sm:loc", ns)
                    lastmod = url_el.find("sm:lastmod", ns)

                    if loc is not None and loc.text:
                        url = loc.text.strip()
                        if self.is_valid_article_url(url):
                            mod_date = lastmod.text.strip() if lastmod is not None and lastmod.text else ""
                            url_with_dates.append((url, mod_date))

            except ElementTree.ParseError as e:
                self.logger.error(f"Failed to parse sitemap: {sitemap_url} - {e}")

        # Sort by lastmod descending (newest first)
        url_with_dates.sort(key=lambda x: x[1] if x[1] else "", reverse=True)
        self._article_urls_cache = url_with_dates

        self.logger.info(f"Found {len(url_with_dates)} articles from sitemap")
        return url_with_dates

    def is_valid_article_url(self, url: str) -> bool:
        """
        Check if URL is a valid article URL

        Valid Blogger article URLs match: /YYYY/MM/slug.html
        """
        if not url or "alexischeong.com" not in url:
            return False

        # Must match Blogger post URL pattern: /YYYY/MM/slug.html
        if not re.search(r'/\d{4}/\d{2}/[\w-]+\.html', url):
            return False

        # Exclude non-article pages
        exclude_patterns = [
            "/search/", "/search?", "/feeds/", "/p/",
            "/share-widget",
        ]
        url_lower = url.lower()
        if any(p in url_lower for p in exclude_patterns):
            return False

        return True

    def _parse_date_from_meta(self, soup) -> str:
        """
        Parse publish date from Blogger .entry-meta text

        Blogger displays date as: "Monday, 29 December 2025"
        Also try: "29 December 2025", "December 29, 2025"

        Returns:
            Date string or empty string
        """
        # Try .entry-meta element
        meta_el = soup.select_one(".entry-meta")
        if meta_el:
            meta_text = self.clean_text(meta_el.get_text())
            # Pattern: "Weekday, DD Month YYYY" or "DD Month YYYY"
            date_match = re.search(
                r'(\d{1,2}\s+(?:January|February|March|April|May|June|July|'
                r'August|September|October|November|December)\s+\d{4})',
                meta_text,
                re.IGNORECASE,
            )
            if date_match:
                return date_match.group(1)

        # Fallback: try to extract from URL (/YYYY/MM/)
        return ""

    def _extract_date_from_url(self, url: str) -> str:
        """
        Extract approximate date from Blogger URL pattern /YYYY/MM/

        Returns:
            "YYYY-MM-01" or empty string
        """
        match = re.search(r'/(\d{4})/(\d{2})/', url)
        if match:
            return f"{match.group(1)}-{match.group(2)}-01"
        return ""

    def extract_content(self, html: str) -> str:
        """
        Extract main content from Blogger post HTML

        Blogger uses div.post-body as the main content container
        """
        soup = self.parse_html(html)

        content_selectors = [
            "div.post-body",
            ".post-body",
            ".entry-content",
            "article",
        ]

        for selector in content_selectors:
            content_el = soup.select_one(selector)
            if content_el:
                # Remove unwanted elements
                for tag in content_el.find_all([
                    "script", "style", "nav", "aside", "iframe",
                    "button", "form", "noscript"
                ]):
                    tag.decompose()

                # Remove Blogger-specific unwanted elements
                for css_sel in [
                    ".post-share", ".share-buttons", ".social-share",
                    ".related-wrap", ".related-posts",
                    ".post-footer", ".post-labels",
                    ".separator[style*='clear: both']",
                ]:
                    for el in content_el.select(css_sel):
                        el.decompose()

                content = content_el.decode_contents()
                # Remove HTML comments
                content = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)
                # Clean up excessive whitespace
                content = re.sub(r'\n{3,}', '\n\n', content)
                content = content.strip()
                if len(content) > 100:
                    return content

        return ""

    def parse_article(self, html: str, url: str) -> Optional[Article]:
        """Parse Blogger article detail page"""
        soup = self.parse_html(html)

        # Title
        title = ""
        title_selectors = [
            "h1.post-title",
            ".post-title",
            "h1",
        ]
        for selector in title_selectors:
            title_el = soup.select_one(selector)
            if title_el:
                title = self.clean_text(title_el.get_text())
                if title:
                    break

        if not title:
            # Fallback to og:title
            og_title = soup.select_one("meta[property='og:title']")
            if og_title:
                title = og_title.get("content", "")

        if not title:
            return None

        # Content
        content = self.extract_content(html)

        # Author - Blogger single-author blog
        author = "Alexis Cheong"

        # Publish date - from .entry-meta text
        publish_date = self._parse_date_from_meta(soup)
        if not publish_date:
            # Fallback to URL-based date
            publish_date = self._extract_date_from_url(url)

        # Category / Labels from Blogger label links
        category = ""
        labels = soup.select(".top-labels a, .post-labels a, a[rel='tag']")
        if labels:
            category = self.clean_text(labels[0].get_text())

        # Tags from all label links
        tags = []
        for label_el in labels:
            tag = self.clean_text(label_el.get_text())
            if tag and tag not in tags:
                tags.append(tag)

        # Images
        images = []
        # Content images from post-body
        for img in soup.select(".post-body img"):
            src = img.get("src") or img.get("data-src")
            if src and not src.endswith(".svg"):
                # Blogger images: normalize to full size
                full_src = self.absolute_url(src)
                if full_src not in images:
                    images.append(full_src)

        return Article(
            url=url,
            title=title,
            content=content,
            author=author,
            publish_date=publish_date,
            category=category,
            tags=tags,
            images=images[:10],
            language="en",
            country=self.country,
            city=self.city,
        )
