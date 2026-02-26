# -*- coding: utf-8 -*-
"""
HungryGoWhere Scraper (Sitemap Mode)
https://hungrygowhere.com

Singapore's leading food discovery platform covering restaurant reviews,
food news, and dining guides.

WordPress + Yoast SEO
Sitemap Index: /sitemap_index.xml
Article Sitemaps: /post-sitemap.xml, /post-sitemap2.xml

URL Patterns:
- /food-news/{slug}/      - Food news & openings
- /what-to-eat/{slug}/    - Best-of lists & guides
- /critics-reviews/{slug}/ - Restaurant reviews

Content container: #articleContent
JSON-LD: Author only (no datePublished in JSON-LD)
Date source: dataLayer article_published_date + page text
"""
import json
import re
from typing import List, Optional, Generator, Tuple
from xml.etree import ElementTree

from base_scraper import BaseScraper, Article
from config import SITE_CONFIGS


class HungryGoWhereScraper(BaseScraper):
    """
    HungryGoWhere Scraper (Sitemap Mode)

    WordPress + Yoast SEO
    - post-sitemap.xml + post-sitemap2.xml (~3320 articles)
    - Content in #articleContent
    - JSON-LD has author info only
    - Categories: food-news, what-to-eat, critics-reviews

    URL Pattern: /{category}/{slug}/
    """

    CONFIG_KEY = "hungrygowhere"

    def __init__(self, use_proxy: bool = False):
        config = SITE_CONFIGS.get(self.CONFIG_KEY, {})
        super().__init__(
            name=config.get("name", "HungryGoWhere"),
            base_url=config.get("base_url", "https://hungrygowhere.com"),
            delay=config.get("delay", 0.5),
            use_proxy=use_proxy,
            country=config.get("country", "Singapore"),
            city=config.get("city", "Singapore"),
        )
        self._article_urls_cache = None

    def get_article_list_urls(self) -> Generator[str, None, None]:
        """Generate list page URLs - use special marker for sitemap mode"""
        yield "sitemap://hungrygowhere"

    def parse_article_list(self, html: str, list_url: str) -> List[str]:
        """Parse article list page - not used in sitemap mode"""
        return []

    def fetch_urls_from_sitemap(self) -> List[Tuple[str, str]]:
        """
        Fetch article URLs from Yoast post-sitemaps

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

        # Fallback to known pattern
        if not sitemap_urls:
            sitemap_urls = [
                f"{self.base_url}/post-sitemap.xml",
                f"{self.base_url}/post-sitemap2.xml",
            ]

        self.logger.info(f"Found {len(sitemap_urls)} post-sitemaps")

        # Fetch each sitemap
        for sitemap_url in sitemap_urls:
            response = self.fetch(sitemap_url)
            if not response:
                continue

            try:
                root = ElementTree.fromstring(response.content)
                count = 0
                for url_el in root.findall(".//sm:url", ns):
                    loc = url_el.find("sm:loc", ns)
                    lastmod = url_el.find("sm:lastmod", ns)

                    if loc is not None and loc.text:
                        url = loc.text.strip()
                        if self.is_valid_article_url(url):
                            mod_date = lastmod.text.strip() if lastmod is not None and lastmod.text else ""
                            url_with_dates.append((url, mod_date))
                            count += 1

                self.logger.info(f"Sitemap {sitemap_url}: {count} articles")

            except ElementTree.ParseError as e:
                self.logger.error(f"Failed to parse sitemap: {sitemap_url} - {e}")

        # Sort by lastmod descending
        url_with_dates.sort(key=lambda x: x[1] if x[1] else "", reverse=True)
        self._article_urls_cache = url_with_dates

        self.logger.info(f"Total articles from sitemap: {len(url_with_dates)}")
        return url_with_dates

    def is_valid_article_url(self, url: str) -> bool:
        """Check if URL is a valid article URL"""
        if not url or "hungrygowhere.com" not in url:
            return False

        url_lower = url.lower()

        # Must start with a valid content category
        valid_prefixes = [
            "/food-news/",
            "/what-to-eat/",
            "/critics-reviews/",
        ]
        path = url_lower.replace("https://hungrygowhere.com", "").replace("http://hungrygowhere.com", "")
        if not any(path.startswith(p) for p in valid_prefixes):
            return False

        # Exclude category index pages (just the prefix with no slug)
        stripped = path.rstrip("/")
        if stripped in ("/food-news", "/what-to-eat", "/critics-reviews"):
            return False

        # Exclude pagination pages
        if "/page/" in url_lower:
            return False

        # Exclude non-article paths
        exclude_patterns = [
            "/wp-admin/", "/wp-content/", "/wp-includes/",
            "/tag/", "/category/", "/author/",
            "/search/", "/feed/",
            ".jpg", ".png", ".pdf",
        ]
        if any(p in url_lower for p in exclude_patterns):
            return False

        return True

    def extract_content(self, html: str) -> str:
        """
        Extract main content from HTML

        HungryGoWhere uses #articleContent as main content container
        """
        soup = self.parse_html(html)

        content_selectors = [
            "#articleContent",
            ".entry-content",
            "article .content",
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

                # Remove social/ad/widget elements
                for css_sel in [
                    ".sharedaddy", ".jp-relatedposts", ".related-posts",
                    ".social-share", ".post-share", ".share-buttons",
                    ".newsletter", ".optin", ".ad", ".ads",
                    ".trending-items", ".custom-widgets",
                    ".restaurant-details", ".author-box",
                ]:
                    for el in content_el.select(css_sel):
                        el.decompose()

                content = content_el.decode_contents()
                content = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)
                content = re.sub(r'\n{3,}', '\n\n', content)
                content = content.strip()
                if len(content) > 200:
                    return content

        return ""

    def parse_article(self, html: str, url: str) -> Optional[Article]:
        """Parse article detail page"""
        soup = self.parse_html(html)

        # Parse JSON-LD (HungryGoWhere only has author in JSON-LD)
        author = ""
        for script in soup.select('script[type="application/ld+json"]'):
            try:
                data = json.loads(script.string or "")
                if isinstance(data, dict) and "author" in data:
                    author_data = data["author"]
                    if isinstance(author_data, dict):
                        author = author_data.get("name", "")
                    elif isinstance(author_data, str):
                        author = author_data
                    if author:
                        break
            except (json.JSONDecodeError, TypeError):
                continue

        # Title
        title = ""
        h1 = soup.select_one("h1")
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

        # Publish date - extract from visible text
        # HungryGoWhere shows date like "February 17, 2023" in article header
        publish_date = ""
        # Try meta tag first
        date_meta = soup.select_one("meta[property='article:published_time']")
        if date_meta:
            publish_date = date_meta.get("content", "")

        # Try dataLayer (article_published_date)
        if not publish_date:
            for script in soup.find_all("script"):
                if script.string and "article_published_date" in (script.string or ""):
                    match = re.search(r'article_published_date["\s:]+["\']([^"\']+)["\']', script.string)
                    if match:
                        publish_date = match.group(1)
                        break

        # Try time element
        if not publish_date:
            time_el = soup.select_one("time[datetime]")
            if time_el:
                publish_date = time_el.get("datetime", "")

        # Category - infer from URL path
        category = ""
        if "/food-news/" in url:
            category = "Food News"
        elif "/what-to-eat/" in url:
            category = "What To Eat"
        elif "/critics-reviews/" in url:
            category = "Critics' Reviews"

        # Tags
        tags = []
        for tag_el in soup.select(".tag-links a, .entry-tags a, a[rel='tag']"):
            tag = self.clean_text(tag_el.get_text())
            if tag and tag not in tags:
                tags.append(tag)

        # Images
        images = []
        # Featured image
        featured = soup.select_one(".post-thumbnail img, .featured-image img, .entry-thumbnail img")
        if featured:
            src = featured.get("src") or featured.get("data-src")
            if src:
                images.append(self.absolute_url(src))

        # og:image
        og_image = soup.select_one("meta[property='og:image']")
        if og_image:
            img_url = og_image.get("content", "")
            if img_url and img_url not in images:
                images.append(img_url)

        # Content images
        for img in soup.select("#articleContent img, .entry-content img"):
            src = img.get("src") or img.get("data-src") or img.get("data-lazy-src")
            if src and not src.endswith(".svg"):
                full_src = self.absolute_url(src)
                if full_src not in images:
                    images.append(full_src)

        return Article(
            url=url,
            title=title,
            content=content,
            author=author or "HungryGoWhere",
            publish_date=publish_date,
            category=category,
            tags=tags,
            images=images[:10],
            language="en",
            country=self.country,
            city=self.city,
        )
