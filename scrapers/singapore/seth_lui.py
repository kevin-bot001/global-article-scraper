# -*- coding: utf-8 -*-
"""
SethLui.com Scraper (Sitemap Mode)
https://sethlui.com/
Singapore top food blog with detailed restaurant reviews

WordPress + Yoast SEO
Sitemap Index: /sitemap_index.xml
Article Sitemaps: /post-sitemap.xml ~ /post-sitemap14.xml

curl_cffi can bypass Cloudflare without Playwright
"""
import json
import re
from typing import List, Optional, Generator, Tuple
from xml.etree import ElementTree

from base_scraper import BaseScraper, Article
from config import SITE_CONFIGS


class SethLuiScraper(BaseScraper):
    """
    SethLui.com Scraper (Sitemap Mode)

    WordPress + Yoast SEO
    - JSON-LD @graph structured data
    - Multiple post-sitemaps (post-sitemap.xml ~ post-sitemap14.xml)
    - Content in .entry-content
    - curl_cffi bypasses Cloudflare TLS fingerprinting

    URL Pattern: /[article-slug]/
    """

    CONFIG_KEY = "seth_lui"

    def __init__(self, use_proxy: bool = False):
        config = SITE_CONFIGS.get(self.CONFIG_KEY, {})
        super().__init__(
            name=config.get("name", "SethLui.com"),
            base_url=config.get("base_url", "https://sethlui.com"),
            delay=config.get("delay", 1.0),
            use_proxy=use_proxy,
            country=config.get("country", "Singapore"),
            city=config.get("city", ""),
        )
        self._article_urls_cache = None

    def get_article_list_urls(self) -> Generator[str, None, None]:
        """Generate list page URLs - use special marker for sitemap mode"""
        yield "sitemap://seth_lui"

    def parse_article_list(self, html: str, list_url: str) -> List[str]:
        """Parse article list page - not used in sitemap mode"""
        return []

    def fetch_urls_from_sitemap(self) -> List[Tuple[str, str]]:
        """
        Fetch article URLs from Yoast SEO post-sitemaps

        Returns:
            [(url, lastmod), ...] sorted by lastmod descending
        """
        if self._article_urls_cache is not None:
            return self._article_urls_cache

        url_with_dates = []
        ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

        # Fetch sitemap index
        index_url = f"{self.base_url}/sitemap_index.xml"
        response = self.fetch(index_url)

        sitemap_urls = []
        if response:
            try:
                root = ElementTree.fromstring(response.content)
                for sitemap_el in root.findall(".//sm:sitemap", ns):
                    loc = sitemap_el.find("sm:loc", ns)
                    if loc is not None and loc.text and "post-sitemap" in loc.text:
                        sitemap_urls.append(loc.text.strip())
            except ElementTree.ParseError:
                pass

        # Fallback
        if not sitemap_urls:
            sitemap_urls = [f"{self.base_url}/post-sitemap.xml"]

        self.logger.info(f"Found {len(sitemap_urls)} post-sitemaps")

        # Fetch each sitemap
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
        """Check if URL is a valid article URL"""
        if not url or "sethlui.com" not in url:
            return False

        # Exclude non-article pages
        exclude_patterns = [
            "/wp-admin/", "/wp-content/", "/wp-includes/",
            "/tag/", "/category/", "/author/", "/page/",
            "/search/", "/attachment/", "/feed/",
            "/about", "/contact", "/privacy", "/terms",
            "/shop/", "/product/", "/cart/", "/checkout/",
            "/careers", "/advertise",
        ]
        url_lower = url.lower()
        if any(p in url_lower for p in exclude_patterns):
            return False

        # Exclude category-only pages
        from urllib.parse import urlparse
        parsed = urlparse(url)
        path = parsed.path.strip("/")

        if not path:
            return False

        # Exclude top-level country/category paths
        parts = path.split("/")
        if len(parts) == 1 and parts[0] in ["singapore", "malaysia", "video", "careers-work"]:
            return False
        if len(parts) == 2 and parts[0] in ["singapore", "malaysia"]:
            if parts[1] in ["food", "travel", "lifestyle", "nightlife"]:
                return False

        return True

    def _parse_json_ld(self, soup) -> dict:
        """
        Parse Yoast SEO JSON-LD @graph structure

        Returns:
            Dict with datePublished, dateModified, author, headline
        """
        result = {}

        for script in soup.select('script[type="application/ld+json"]'):
            try:
                data = json.loads(script.string or "")
                items = data if isinstance(data, list) else [data]

                for item in items:
                    # Direct Article format
                    if item.get("@type") in ["Article", "BlogPosting", "NewsArticle"]:
                        if item.get("datePublished"):
                            result["datePublished"] = item["datePublished"]
                        if item.get("dateModified"):
                            result["dateModified"] = item["dateModified"]
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
                                if graph_item.get("dateModified"):
                                    result["dateModified"] = graph_item["dateModified"]
                                if graph_item.get("headline"):
                                    result["headline"] = graph_item["headline"]
                                # Elementor sites: category in articleSection
                                if graph_item.get("articleSection"):
                                    sections = graph_item["articleSection"]
                                    if isinstance(sections, list) and sections:
                                        result["category"] = sections[0]
                                    elif isinstance(sections, str):
                                        result["category"] = sections
                                # Keywords as tags
                                if graph_item.get("keywords"):
                                    kw = graph_item["keywords"]
                                    if isinstance(kw, list):
                                        result["keywords"] = kw
                                    elif isinstance(kw, str):
                                        result["keywords"] = [k.strip() for k in kw.split(",")]
                            if graph_item.get("@type") == "Person" and graph_item.get("name"):
                                result["author"] = graph_item["name"]

            except (json.JSONDecodeError, TypeError, KeyError):
                continue

        return result

    def extract_content(self, html: str) -> str:
        """
        Extract main content from WordPress article HTML

        SethLui uses .entry-content as main content container
        """
        soup = self.parse_html(html)

        content_selectors = [
            ".elementor-widget-theme-post-content .elementor-widget-container",
            ".entry-content",
            ".post-content",
            ".article-content",
            "article .content",
            "main article",
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

                # Remove social/ad/related elements
                for css_sel in [
                    ".share-container", ".share", ".ad", ".advertisement",
                    ".related", ".related-posts", ".newsletter", ".optin",
                    ".social-share", ".author-box", ".tableofcontent",
                    ".instagram-feed", ".newsletter-signup",
                    ".sharedaddy", ".jp-relatedposts",
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
        """Parse article detail page"""
        soup = self.parse_html(html)

        # Parse JSON-LD structured data
        json_ld = self._parse_json_ld(soup)

        # Title - prefer JSON-LD
        title = json_ld.get("headline", "")
        if not title:
            title_selectors = [
                "h1.entry-title",
                "h1.post-title",
                ".entry-header h1",
                "h1",
            ]
            for selector in title_selectors:
                title_el = soup.select_one(selector)
                if title_el:
                    title = self.clean_text(title_el.get_text())
                    if title and len(title) > 5:
                        break

        if not title:
            og_title = soup.select_one("meta[property='og:title']")
            if og_title:
                title = og_title.get("content", "")

        if not title:
            return None

        # Content
        content = self.extract_content(html)

        # Author - prefer JSON-LD
        author = json_ld.get("author", "")
        if not author:
            author_el = soup.select_one("a[href*='/author/']")
            if author_el:
                author = self.clean_text(author_el.get_text())

        # Publish date - prefer JSON-LD
        publish_date = json_ld.get("datePublished", "")
        if not publish_date:
            meta_date = soup.select_one("meta[property='article:published_time']")
            if meta_date:
                publish_date = meta_date.get("content", "")
        if not publish_date:
            time_el = soup.select_one("time[datetime]")
            if time_el:
                publish_date = time_el.get("datetime", "")

        # Category - prefer JSON-LD articleSection
        category = json_ld.get("category", "")
        if not category:
            cat_selectors = [
                "a[href*='/singapore/food/']",
                "a[href*='/singapore/travel/']",
                "a[href*='/singapore/lifestyle/']",
                "a[href*='/malaysia/food/']",
                ".category a",
                ".cat-links a",
                "a[rel='category tag']",
            ]
            for selector in cat_selectors:
                cat_el = soup.select_one(selector)
                if cat_el:
                    category = self.clean_text(cat_el.get_text())
                    if category:
                        break

        # Tags - prefer JSON-LD keywords
        tags = json_ld.get("keywords", [])
        if not tags:
            for tag_el in soup.select(".tags a, .tag-links a, .entry-tags a, a[rel='tag']"):
                tag = self.clean_text(tag_el.get_text())
                if tag and tag not in tags:
                    tags.append(tag)

        # Images
        images = []
        # Featured image
        featured = soup.select_one(
            ".featured-image img, .post-thumbnail img, .hero img, "
            ".entry-thumbnail img"
        )
        if featured:
            src = featured.get("src") or featured.get("data-src") or featured.get("data-lazy-src")
            if src and not src.endswith(".svg"):
                images.append(self.absolute_url(src))

        # Content images
        for img in soup.select(
            ".elementor-widget-theme-post-content img, "
            ".entry-content img, .post-content img, article img"
        ):
            src = img.get("src") or img.get("data-src") or img.get("data-lazy-src")
            if src and not src.endswith(".svg"):
                full_src = self.absolute_url(src)
                if full_src not in images:
                    images.append(full_src)

        # Detect city from title/URL
        detected_country, detected_city = self.detect_location_from_title(title, url)

        return Article(
            url=url,
            title=title,
            content=content,
            author=author or "Seth Lui",
            publish_date=publish_date,
            category=category,
            tags=tags,
            images=images[:10],
            language="en",
            country=detected_country or self.country,
            city=detected_city or self.city,
        )
