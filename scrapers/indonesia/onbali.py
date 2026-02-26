# -*- coding: utf-8 -*-
"""
OnBali Scraper (Sitemap mode)
https://onbali.com/

Bali travel and dining guide, built with Next.js.
Sitemap Index: /sitemap.xml -> /sitemap_1.xml ~ /sitemap_7.xml
JSON-LD @graph format with Article, Organization, FAQPage schemas.
"""
import json
import re
from typing import List, Optional, Generator, Tuple
from urllib.parse import urlparse

from base_scraper import BaseScraper, Article
from config import SITE_CONFIGS


class OnBaliScraper(BaseScraper):
    """
    OnBali Scraper

    Sitemap:
    - Index: /sitemap.xml (standard sitemapindex)
    - Sub-sitemaps: /sitemap_1.xml ~ /sitemap_7.xml

    URL pattern:
    - Articles: /{category}/{slug}/ (e.g. /uluwatu/best-restaurants-in-uluwatu/)
    - Categories: all-bali, uluwatu, seminyak, ubud, canggu, kuta, nusa-dua, sanur, jimbaran, etc.
    - Exclude: /about-us/, category index pages (single segment paths)
    """

    CONFIG_KEY = "onbali"

    def __init__(self, use_proxy: bool = False):
        config = SITE_CONFIGS.get(self.CONFIG_KEY, {})

        super().__init__(
            name=config.get("name", "OnBali"),
            base_url=config.get("base_url", "https://onbali.com"),
            delay=config.get("delay", 0.5),
            use_proxy=use_proxy,
            country=config.get("country", "Indonesia"),
            city=config.get("city", "Bali"),
        )

    def get_article_list_urls(self) -> Generator[str, None, None]:
        """Use sitemap marker for sitemap mode"""
        yield "sitemap://onbali"

    def parse_article_list(self, html: str, list_url: str) -> List[str]:
        """Not used in sitemap mode"""
        return []

    def fetch_urls_from_sitemap(self) -> List[Tuple[str, str]]:
        """Fetch all article URLs from sitemap index"""
        url_with_dates = []
        seen_urls = set()

        # First, fetch the sitemap index to discover sub-sitemaps
        index_url = f"{self.base_url}/sitemap.xml"
        self.logger.info(f"Fetching sitemap index: {index_url}")

        sitemap_files = []
        try:
            resp = self.session.get(index_url, timeout=30)
            if resp.status_code == 200:
                # Extract sub-sitemap URLs from the index
                loc_pattern = re.compile(r'<loc>([^<]+)</loc>')
                for match in loc_pattern.finditer(resp.text):
                    sitemap_url = match.group(1).strip()
                    if sitemap_url.endswith('.xml') and sitemap_url != index_url:
                        sitemap_files.append(sitemap_url)
                self.logger.info(f"Found {len(sitemap_files)} sub-sitemaps")
            else:
                self.logger.warning(f"Failed to fetch sitemap index: {resp.status_code}")
        except Exception as e:
            self.logger.warning(f"Error fetching sitemap index: {e}")

        # Fallback: if index parsing failed, try known patterns
        if not sitemap_files:
            sitemap_files = [f"{self.base_url}/sitemap_{i}.xml" for i in range(1, 8)]

        # Parse each sub-sitemap for article URLs
        url_pattern = re.compile(
            r'<url>\s*<loc>([^<]+)</loc>(?:\s*<lastmod>([^<]+)</lastmod>)?',
            re.DOTALL,
        )

        for sitemap_url in sitemap_files:
            self.logger.info(f"Fetching sitemap: {sitemap_url}")
            try:
                resp = self.session.get(sitemap_url, timeout=30)
                if resp.status_code != 200:
                    self.logger.warning(f"Failed to fetch {sitemap_url}: {resp.status_code}")
                    continue

                for match in url_pattern.finditer(resp.text):
                    url = match.group(1).strip()
                    lastmod = match.group(2).strip() if match.group(2) else ""
                    if self.is_valid_article_url(url) and url not in seen_urls:
                        url_with_dates.append((url, lastmod))
                        seen_urls.add(url)

            except Exception as e:
                self.logger.warning(f"Error fetching {sitemap_url}: {e}")
                continue

        # Sort by lastmod descending (newest first)
        url_with_dates.sort(key=lambda x: x[1] if x[1] else "", reverse=True)
        self.logger.info(f"Found {len(url_with_dates)} article URLs from sitemaps")
        return url_with_dates

    def is_valid_article_url(self, url: str) -> bool:
        """Check if URL is a valid article page"""
        if not url or "onbali.com" not in url:
            return False

        parsed = urlparse(url)
        path = parsed.path.strip("/")

        # Must have a path
        if not path:
            return False

        # Exclude non-article pages
        exclude_patterns = [
            "/about-us",
            "/contact",
            "/privacy-policy",
            "/terms",
            "/disclaimer",
            "/sitemap",
            "/search",
            "/tag/",
            "/category/",
            "/author/",
            "/page/",
            "/wp-admin/",
            "/wp-content/",
            "/api/",
        ]
        url_lower = url.lower()
        if any(p in url_lower for p in exclude_patterns):
            return False

        # Must have at least 2 path segments: /{category}/{slug}/
        # Single segment pages are category index pages (e.g. /uluwatu/, /all-bali/)
        segments = [s for s in path.split("/") if s]
        if len(segments) < 2:
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
                    # Direct Article type
                    if item.get("@type") in ["Article", "BlogPosting", "NewsArticle"]:
                        if item.get("datePublished"):
                            result["datePublished"] = item["datePublished"]
                        if item.get("dateModified"):
                            result["dateModified"] = item["dateModified"]
                        if item.get("headline"):
                            result["headline"] = item["headline"]
                        if item.get("author"):
                            author = item["author"]
                            if isinstance(author, dict):
                                result["author"] = author.get("name", "")
                            elif isinstance(author, list) and author:
                                result["author"] = author[0].get("name", "") if isinstance(author[0], dict) else str(author[0])
                            elif isinstance(author, str):
                                result["author"] = author

                    # @graph format (common in Yoast/Rank Math and custom implementations)
                    if "@graph" in item:
                        for graph_item in item["@graph"]:
                            item_type = graph_item.get("@type", "")
                            # Handle both string and list types
                            if isinstance(item_type, list):
                                types = item_type
                            else:
                                types = [item_type]

                            if any(t in ["Article", "BlogPosting", "NewsArticle", "WebPage"] for t in types):
                                if graph_item.get("datePublished"):
                                    result["datePublished"] = graph_item["datePublished"]
                                if graph_item.get("dateModified"):
                                    result["dateModified"] = graph_item["dateModified"]
                                if graph_item.get("headline"):
                                    result["headline"] = graph_item["headline"]
                                if graph_item.get("author"):
                                    author = graph_item["author"]
                                    if isinstance(author, dict):
                                        result["author"] = author.get("name", "")
                                    elif isinstance(author, list) and author:
                                        result["author"] = author[0].get("name", "") if isinstance(author[0], dict) else str(author[0])

                            if any(t == "Person" for t in types) and graph_item.get("name"):
                                if "author" not in result:
                                    result["author"] = graph_item["name"]

            except (json.JSONDecodeError, TypeError, KeyError):
                continue

        return result

    def extract_content(self, html: str) -> str:
        """Extract article body content from HTML"""
        soup = self.parse_html(html)

        # OnBali uses Next.js with CSS modules - class names contain hashes
        # Primary: div.layout_post__* (main post container)
        # Fallback: standard selectors
        content_selectors = [
            "div[class*='layout_post']",
            "div[class*='post__']",
            "article",
            "main",
            ".entry-content",
            ".post-content",
        ]

        for selector in content_selectors:
            content_el = soup.select_one(selector)
            if content_el:
                # Remove unwanted elements
                for tag in content_el.find_all([
                    "script", "style", "nav", "aside", "iframe",
                    "noscript", "button", "form", "footer",
                ]):
                    tag.decompose()

                # Remove common non-content sections
                for css_sel in [
                    "[class*='AuthorCard']",
                    "[class*='Breadcrumbs']",
                    "[class*='RelatedArticles']",
                    "[class*='Newsletter']",
                    "[class*='ShareButton']",
                    "[class*='TableOfContents']",
                    "[class*='FAQ']",
                    ".share", ".social", ".ad", ".advertisement",
                    ".related", ".newsletter", ".comments",
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

        # Extract JSON-LD structured data
        json_ld = self._parse_json_ld(soup)

        # Title - prefer og:title, then JSON-LD headline, then h1
        title = ""
        og_title = soup.select_one("meta[property='og:title']")
        if og_title:
            title = og_title.get("content", "")
            # Remove site name suffix if present
            for suffix in [" | OnBali", " - OnBali", " | ONBALI", " - ONBALI"]:
                if title.endswith(suffix):
                    title = title[: -len(suffix)]

        if not title:
            title = json_ld.get("headline", "")

        if not title:
            # Next.js CSS module class: PageTitle_title__*
            title_selectors = [
                "h1[class*='PageTitle']",
                "h1[class*='title']",
                "h1",
            ]
            for selector in title_selectors:
                title_el = soup.select_one(selector)
                if title_el:
                    title = self.clean_text(title_el.get_text())
                    if title:
                        break

        if not title:
            return None

        # Content
        content = self.extract_content(html)

        # Author - prefer JSON-LD
        author = json_ld.get("author", "")
        if not author:
            # Try author link in page
            author_selectors = [
                "a[class*='authorName']",
                "[class*='AuthorLink'] a",
                "a[href*='/about-us/']",
            ]
            for selector in author_selectors:
                author_el = soup.select_one(selector)
                if author_el:
                    author = self.clean_text(author_el.get_text())
                    if author:
                        break

        # Publish date - prefer JSON-LD
        publish_date = json_ld.get("datePublished", "")
        if not publish_date:
            publish_date = json_ld.get("dateModified", "")

        if not publish_date:
            # Try meta tags
            for meta_name in ["article:published_time", "article:modified_time"]:
                date_meta = soup.select_one(f"meta[property='{meta_name}']")
                if date_meta:
                    publish_date = date_meta.get("content", "")
                    if publish_date:
                        break

        # Category - extract from URL path (first segment)
        category = ""
        parsed = urlparse(url)
        path_segments = [s for s in parsed.path.strip("/").split("/") if s]
        if path_segments:
            # Convert slug to readable form: "all-bali" -> "All Bali"
            category = path_segments[0].replace("-", " ").title()

        # Images - prefer og:image
        images = []
        og_image = soup.select_one("meta[property='og:image']")
        if og_image:
            src = og_image.get("content", "")
            if src:
                images.append(src)

        # Get more images from article content
        for img in soup.select("img[src*='/assets/posts/'], article img, main img"):
            src = img.get("src") or img.get("data-src")
            if src and not src.endswith(".svg") and "data:image" not in src:
                full_src = self.absolute_url(src)
                if full_src not in images:
                    images.append(full_src)

        return Article(
            url=url,
            title=title,
            content=content,
            author=author or "OnBali",
            publish_date=publish_date,
            category=category,
            tags=[],
            images=images[:10],
            language="en",
            country="Indonesia",
            city="Bali",
        )
