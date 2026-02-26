# -*- coding: utf-8 -*-
"""
Daniel Food Diary Scraper (Sitemap Mode)
https://danielfooddiary.com
Singapore Food & Restaurant Reviews

All in One SEO Pro
Sitemap Index: /sitemap.xml
Article Sitemaps: /post-sitemap.xml ~ /post-sitemap8.xml
"""
import json
import re
from typing import List, Optional, Generator, Tuple
from xml.etree import ElementTree

from base_scraper import BaseScraper, Article
from config import SITE_CONFIGS


class DanielFoodDiaryScraper(BaseScraper):
    """
    Daniel Food Diary Scraper (Sitemap Mode)

    All in One SEO Pro sitemap structure
    - JSON-LD @graph structured data
    - Multiple post-sitemaps (post-sitemap.xml ~ post-sitemap8.xml)
    - Content in article > main

    URL Pattern: /YYYY/MM/DD/[slug]/
    """

    CONFIG_KEY = "daniel_food_diary"

    def __init__(self, use_proxy: bool = False):
        config = SITE_CONFIGS.get(self.CONFIG_KEY, {})
        super().__init__(
            name=config.get("name", "Daniel Food Diary"),
            base_url=config.get("base_url", "https://danielfooddiary.com"),
            delay=config.get("delay", 0.5),
            use_proxy=use_proxy,
            country=config.get("country", "Singapore"),
            city=config.get("city", "Singapore"),
        )
        self._article_urls_cache = None
        self.max_sitemaps = config.get("max_sitemaps", 8)
        self.default_city = self.city

    def get_article_list_urls(self) -> Generator[str, None, None]:
        """Generate list page URLs - use special marker for sitemap mode"""
        yield "sitemap://daniel_food_diary"

    def parse_article_list(self, html: str, list_url: str) -> List[str]:
        """Parse article list page - not used in sitemap mode"""
        return []

    def fetch_urls_from_sitemap(self) -> List[Tuple[str, str]]:
        """
        Fetch article URLs from multiple post-sitemaps

        Returns:
            [(url, lastmod), ...] sorted by lastmod descending
        """
        if self._article_urls_cache is not None:
            return self._article_urls_cache

        url_with_dates = []
        ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

        # Try sitemap index first
        index_url = f"{self.base_url}/sitemap.xml"
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

        # Fallback to default pattern if index failed
        if not sitemap_urls:
            sitemap_urls = [f"{self.base_url}/post-sitemap.xml"]
            for i in range(2, self.max_sitemaps + 1):
                sitemap_urls.append(f"{self.base_url}/post-sitemap{i}.xml")

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
        if not url or "danielfooddiary.com" not in url:
            return False

        # Exclude non-article pages
        exclude_patterns = [
            "/wp-admin/", "/wp-content/", "/wp-includes/",
            "/tag/", "/category/", "/author/", "/page/",
            "/search/", "/attachment/", "/feed/",
            "/aboutthediary", "/advertising", "/instagram",
            "/contact", "/privacy", "/terms",
            "/sitemap", "/xmlrpc",
        ]
        url_lower = url.lower()
        if any(p in url_lower for p in exclude_patterns):
            return False

        # URL should match pattern: /YYYY/MM/DD/slug/
        # e.g., https://danielfooddiary.com/2026/02/05/gwanghwamunmijin/
        path = url.replace(self.base_url, "").strip("/")
        if not path:
            return False

        # Check for date pattern in URL
        date_pattern = r"^\d{4}/\d{2}/\d{2}/"
        if re.match(date_pattern, path):
            return True

        return False

    def _parse_json_ld(self, soup) -> dict:
        """
        Parse JSON-LD structured data (All in One SEO / Yoast style)

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
                        elif isinstance(author, list) and len(author) > 0:
                            result["author"] = author[0].get("name", "") if isinstance(author[0], dict) else str(author[0])
                        elif isinstance(author, str):
                            result["author"] = author

                    # @graph format (common in SEO plugins)
                    if "@graph" in item:
                        for graph_item in item["@graph"]:
                            if graph_item.get("@type") in ["Article", "BlogPosting", "NewsArticle"]:
                                if graph_item.get("datePublished"):
                                    result["datePublished"] = graph_item["datePublished"]
                                if graph_item.get("dateModified"):
                                    result["dateModified"] = graph_item["dateModified"]
                                if graph_item.get("headline"):
                                    result["headline"] = graph_item["headline"]
                            if graph_item.get("@type") == "Person" and graph_item.get("name"):
                                result["author"] = graph_item["name"]

            except (json.JSONDecodeError, TypeError, KeyError):
                continue

        return result

    def extract_content(self, html: str) -> str:
        """
        Extract main content from HTML

        Daniel Food Diary uses article > main structure
        """
        soup = self.parse_html(html)

        content_selectors = [
            "article main",
            "article .entry-content",
            ".entry-content",
            "article .post-content",
            "article",
        ]

        for selector in content_selectors:
            content_el = soup.select_one(selector)
            if content_el:
                # Remove unwanted elements
                for tag in content_el.find_all([
                    "script", "style", "nav", "aside", "iframe",
                    "button", "form", "noscript", "header", "footer"
                ]):
                    tag.decompose()

                # Remove social/share/related elements
                for css_sel in [
                    ".share", ".social", ".related",
                    ".author-box", ".author-info", ".author-bio",
                    ".comments", ".comment-respond",
                    ".post-navigation", ".navigation",
                    "[class*='share']", "[class*='social']",
                    ".wp-block-embed", ".instagram-media",
                ]:
                    for el in content_el.select(css_sel):
                        el.decompose()

                content = content_el.decode_contents()
                # Remove HTML comments
                content = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)
                # Clean up excessive whitespace
                content = re.sub(r'\n{3,}', '\n\n', content)
                content = content.strip()
                if len(content) > 200:
                    return content

        return ""

    def parse_article(self, html: str, url: str) -> Optional[Article]:
        """Parse article detail page"""
        soup = self.parse_html(html)

        # Parse JSON-LD structured data
        json_ld = self._parse_json_ld(soup)

        # Title - prefer JSON-LD, then HTML
        title = json_ld.get("headline", "")
        if not title:
            title_selectors = [
                "article h1",
                "h1.entry-title",
                "h1.post-title",
                ".entry-header h1",
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
                title = og_title.get("content", "").split("|")[0].strip()

        if not title:
            return None

        # Content
        content = self.extract_content(html)

        # Author - prefer JSON-LD
        author = json_ld.get("author", "")
        if not author:
            author_selectors = [
                ".author-name a",
                ".author a",
                ".entry-author a",
                "a[rel='author']",
                ".byline a",
                "a[href*='/author/']",
            ]
            for selector in author_selectors:
                author_el = soup.select_one(selector)
                if author_el:
                    author = self.clean_text(author_el.get_text())
                    if author and author.lower() not in ["admin", "author"]:
                        break

        # Publish date - prefer JSON-LD
        publish_date = json_ld.get("datePublished", "")
        if not publish_date:
            date_selectors = [
                "time[datetime]",
                ".entry-date",
                ".post-date",
                "meta[property='article:published_time']",
            ]
            for selector in date_selectors:
                date_el = soup.select_one(selector)
                if date_el:
                    publish_date = date_el.get("datetime") or date_el.get("content") or self.clean_text(date_el.get_text())
                    if publish_date:
                        break

        # Extract date from URL if not found (URL pattern: /YYYY/MM/DD/slug/)
        if not publish_date:
            url_match = re.search(r'/(\d{4})/(\d{2})/(\d{2})/', url)
            if url_match:
                publish_date = f"{url_match.group(1)}-{url_match.group(2)}-{url_match.group(3)}"

        # Category
        category = ""
        cat_selectors = [
            ".cat-links a",
            ".entry-categories a",
            "a[rel='category tag']",
            "a[href*='/category/']",
        ]
        for selector in cat_selectors:
            cat_el = soup.select_one(selector)
            if cat_el:
                category = self.clean_text(cat_el.get_text())
                if category:
                    break

        # Tags
        tags = []
        for tag_el in soup.select(".tag-links a, .entry-tags a, a[rel='tag'], a[href*='/tag/']"):
            tag = self.clean_text(tag_el.get_text())
            # Clean up common prefixes
            if tag.startswith("#"):
                tag = tag[1:]
            if tag and tag not in tags and len(tag) < 50:
                tags.append(tag)

        # Images
        images = []
        # og:image as featured
        og_image = soup.select_one("meta[property='og:image']")
        if og_image:
            src = og_image.get("content")
            if src:
                images.append(self.absolute_url(src))

        # Featured image
        featured = soup.select_one(".post-thumbnail img, .entry-thumbnail img, .featured-image img, article header img")
        if featured:
            src = featured.get("src") or featured.get("data-src")
            if src and self.absolute_url(src) not in images:
                images.append(self.absolute_url(src))

        # Content images
        for img in soup.select("article img, .entry-content img"):
            src = img.get("src") or img.get("data-src") or img.get("data-lazy-src")
            if src and not src.endswith(".svg") and "gravatar" not in src:
                full_src = self.absolute_url(src)
                if full_src not in images:
                    images.append(full_src)

        return Article(
            url=url,
            title=title,
            content=content,
            author=author or "Daniel Food Diary",
            publish_date=publish_date,
            category=category,
            tags=tags[:15],
            images=images[:10],
            language="en",
            country=self.country,
            city=self.default_city,
        )
