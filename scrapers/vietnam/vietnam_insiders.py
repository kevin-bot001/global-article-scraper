# -*- coding: utf-8 -*-
"""
Vietnam Insiders scraper (Sitemap mode)
https://vietnaminsiders.com/
Vietnamese news media covering Michelin, restaurants, food, travel and lifestyle
"""
import json
from typing import List, Optional, Generator
from xml.etree import ElementTree as ET

from base_scraper import BaseScraper, Article
from config import SITE_CONFIGS


class VietnamInsidersScraper(BaseScraper):
    """
    Vietnam Insiders scraper

    Jetpack sitemap (sitemap index -> sitemap-1.xml ~ sitemap-23.xml)
    JSON-LD: BlogPosting / Article format

    Features:
    - Vietnamese news media with food/restaurant coverage
    - Michelin reviews, street food guides, restaurant news
    - English content (some Vietnamese articles)
    - URL filtering needed: general news site, only scrape food-related articles
    """

    CONFIG_KEY = "vietnam_insiders"

    def __init__(self, use_proxy: bool = False):
        config = SITE_CONFIGS.get(self.CONFIG_KEY, {})

        super().__init__(
            name=config.get("name", "Vietnam Insiders"),
            base_url=config.get("base_url", "https://vietnaminsiders.com"),
            delay=config.get("delay", 0.5),
            use_proxy=use_proxy,
            country=config.get("country", "Vietnam"),
            city=config.get("city", ""),
        )

    def get_article_list_urls(self) -> Generator[str, None, None]:
        """Return sitemap marker"""
        yield "sitemap://"

    def parse_article_list(self, html: str, list_url: str) -> List[str]:
        """Not used in sitemap mode"""
        return []

    def fetch_urls_from_sitemap(self) -> List[tuple]:
        """
        Fetch article URLs from Jetpack sitemap index.

        Jetpack structure:
        - /sitemap.xml -> sitemap index pointing to /sitemap-index-1.xml
        - /sitemap-index-1.xml -> sub-sitemaps /sitemap-1.xml ~ /sitemap-23.xml
        - Each sub-sitemap contains article URLs with lastmod
        """
        all_urls = []
        ns = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}

        # Step 1: Fetch sitemap index to get sub-sitemap list
        index_url = f"{self.base_url}/sitemap-index-1.xml"
        response = self.fetch(index_url)
        if not response:
            self.logger.error(f"Failed to fetch sitemap index: {index_url}")
            return all_urls

        sub_sitemap_urls = []
        try:
            root = ET.fromstring(response.text)
            for sitemap_el in root.findall(".//ns:sitemap", ns):
                loc = sitemap_el.find("ns:loc", ns)
                if loc is not None and loc.text:
                    url = loc.text.strip()
                    # Only include content sitemaps, skip image/video sitemaps
                    if "image-sitemap" not in url and "video-sitemap" not in url:
                        sub_sitemap_urls.append(url)
        except ET.ParseError as e:
            self.logger.error(f"Failed to parse sitemap index: {index_url} - {e}")
            return all_urls

        self.logger.info(f"Found {len(sub_sitemap_urls)} sub-sitemaps in index")

        # Step 2: Fetch each sub-sitemap and collect article URLs
        for sub_url in sub_sitemap_urls:
            response = self.fetch(sub_url)
            if not response:
                self.logger.warning(f"Failed to fetch sub-sitemap: {sub_url}")
                continue

            try:
                # Check if this is another sitemap index (nested) or actual URLs
                root = ET.fromstring(response.text)

                # Check for nested sitemap index
                nested_sitemaps = root.findall(".//ns:sitemap", ns)
                if nested_sitemaps:
                    # This is another index level - fetch each nested sitemap
                    for nested_el in nested_sitemaps:
                        nested_loc = nested_el.find("ns:loc", ns)
                        if nested_loc is not None and nested_loc.text:
                            nested_url = nested_loc.text.strip()
                            if "image-sitemap" in nested_url or "video-sitemap" in nested_url:
                                continue
                            nested_resp = self.fetch(nested_url)
                            if nested_resp:
                                try:
                                    nested_root = ET.fromstring(nested_resp.text)
                                    self._extract_urls_from_sitemap(nested_root, ns, all_urls)
                                except ET.ParseError as e:
                                    self.logger.warning(f"Failed to parse nested sitemap: {nested_url} - {e}")
                else:
                    # This contains actual URLs
                    self._extract_urls_from_sitemap(root, ns, all_urls)

            except ET.ParseError as e:
                self.logger.warning(f"Failed to parse sub-sitemap: {sub_url} - {e}")

        self.logger.info(f"Total {len(all_urls)} articles from sitemap")
        return all_urls

    def _extract_urls_from_sitemap(self, root, ns: dict, url_list: list):
        """Extract article URLs from a parsed sitemap XML root element"""
        for url_el in root.findall(".//ns:url", ns):
            loc = url_el.find("ns:loc", ns)
            lastmod = url_el.find("ns:lastmod", ns)

            if loc is not None and loc.text:
                url = loc.text.strip()
                if self.is_valid_article_url(url):
                    mod_date = lastmod.text.strip() if lastmod is not None and lastmod.text else ""
                    url_list.append((url, mod_date))

    def is_valid_article_url(self, url: str) -> bool:
        """
        Filter valid food/restaurant article URLs.

        Vietnam Insiders is a general news site - we only want food-related content.
        URL pattern: https://vietnaminsiders.com/slug/
        """
        if not url or "vietnaminsiders.com" not in url:
            return False

        # Exclude non-article pages
        exclude_patterns = [
            "/category/", "/tag/", "/author/", "/page/",
            "/about", "/contact", "/privacy", "/terms",
            "/wp-admin/", "/wp-content/", "/wp-includes/",
            "wp-json", "feed", "xmlrpc",
            "/advertise", "/disclaimer", "/cookie",
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

        # Food/restaurant related keywords in URL slug
        # Use word-boundary matching on slug segments (split by -)
        # to avoid false positives like "great" matching "eat"
        import re
        slug = path.lower()
        # Split slug into words for exact word matching
        slug_words = set(re.split(r'[-/]', slug))

        # Exact word match keywords (matched against individual slug segments)
        exact_keywords = {
            "food", "restaurant", "dining", "eat", "eating", "cuisine", "dish",
            "michelin", "chef", "cook", "cooking", "recipe", "menu", "cafe",
            "bar", "drink", "beer", "wine", "coffee", "tea",
            "pho", "bun", "noodle", "noodles", "rice", "soup",
            "seafood", "bbq", "grill", "buffet",
            "bakery", "dessert", "sweet", "cake", "bread",
            "vegan", "vegetarian", "halal",
            "brunch", "breakfast", "lunch", "dinner",
            "bowl", "sushi", "pizza", "burger",
            "cocktail", "rooftop", "nightlife",
            "gastronomy", "culinary", "flavor",
            "hawker",
        }

        if slug_words & exact_keywords:
            return True

        # Substring match for compound/hyphenated keywords
        compound_keywords = [
            "banh-mi", "street-food", "fine-dining",
            "food-market", "night-market", "wet-market",
        ]
        return any(kw in slug for kw in compound_keywords)

    def _parse_json_ld(self, soup) -> dict:
        """Extract structured data from JSON-LD (Jetpack format)"""
        result = {}

        for script in soup.select('script[type="application/ld+json"]'):
            try:
                data = json.loads(script.string or "")
                items = data if isinstance(data, list) else [data]

                for item in items:
                    item_type = item.get("@type", "")

                    # @graph format (Yoast SEO style)
                    if "@graph" in item:
                        for graph_item in item["@graph"]:
                            gt = graph_item.get("@type", "")
                            if gt in ("Article", "NewsArticle", "BlogPosting"):
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
                            if gt == "Person":
                                result["author"] = graph_item.get("name", "")

                    # Direct Article/BlogPosting format (Jetpack)
                    elif item_type in ("Article", "NewsArticle", "BlogPosting"):
                        if item.get("datePublished"):
                            result["datePublished"] = item["datePublished"]
                        if item.get("headline"):
                            result["headline"] = item["headline"]
                        # Author can be nested object or string
                        author_data = item.get("author")
                        if isinstance(author_data, dict):
                            result["author"] = author_data.get("name", "")
                        elif isinstance(author_data, str):
                            result["author"] = author_data

            except (json.JSONDecodeError, TypeError, KeyError):
                continue

        return result

    def extract_content(self, html: str) -> str:
        """Extract article body content"""
        soup = self.parse_html(html)

        # Vietnam Insiders uses .post-entry for article content (Flavor theme)
        content_selectors = [
            ".post-entry",
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
                    ".penci-post-share", ".penci-post-tags",
                    ".penci-related-post",
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

        # Title: JSON-LD > h1 > og:title
        title = json_ld.get("headline", "")
        if not title:
            title_el = soup.select_one("h1.post-title, h1.penci-post-title, h1.single-post-title, h1")
            if title_el:
                title = self.clean_text(title_el.get_text())

        if not title:
            og_title = soup.select_one("meta[property='og:title']")
            if og_title:
                title = og_title.get("content", "")

        if not title:
            return None

        # Content
        content = self.extract_content(html)

        # Author: JSON-LD > byline link > meta
        author = json_ld.get("author", "")
        if not author:
            author_el = soup.select_one("a[href*='/author/'], .author-name a, a[rel='author']")
            if author_el:
                author = self.clean_text(author_el.get_text())
        if not author:
            meta_author = soup.select_one("meta[name='author']")
            if meta_author:
                author = meta_author.get("content", "")

        # Publish date: JSON-LD > time[datetime] > meta article:published_time
        publish_date = json_ld.get("datePublished", "")
        if not publish_date:
            time_el = soup.select_one("time[datetime]")
            if time_el:
                publish_date = time_el.get("datetime", "")
        if not publish_date:
            meta_date = soup.select_one("meta[property='article:published_time']")
            if meta_date:
                publish_date = meta_date.get("content", "")

        # Category
        category = json_ld.get("category", "")
        if not category:
            cat_el = soup.select_one(".entry-category a, a[rel='category tag'], .post-category a")
            if cat_el:
                category = self.clean_text(cat_el.get_text())

        # Tags
        tags = json_ld.get("keywords", [])
        if not tags:
            for tag_el in soup.select(".post-tags a, .tag-links a, a[rel='tag']"):
                tag = self.clean_text(tag_el.get_text())
                if tag and tag not in tags and tag.lower() not in ("tags", "tag"):
                    tags.append(tag)

        # Images - site uses lazy loading, prefer data-src/data-lazy-src over src (which is SVG placeholder)
        images = []

        # OG image is the most reliable (always actual URL, not lazy placeholder)
        og_img = soup.select_one("meta[property='og:image']")
        if og_img:
            og_src = og_img.get("content", "")
            if og_src and "data:image" not in og_src:
                images.append(og_src)

        # Featured image - check data-src first (lazy loading)
        if not images:
            featured = soup.select_one(
                ".post-image img, .penci-image-holder, .featured-image img, article img"
            )
            if featured:
                src = featured.get("data-lazy-src") or featured.get("data-src") or featured.get("src")
                if src and "data:image" not in src:
                    images.append(self.absolute_url(src))

        # Content images - also handle lazy loading
        for img in soup.select(".post-entry img, .entry-content img"):
            src = img.get("data-lazy-src") or img.get("data-src") or img.get("src")
            if src and not src.endswith(".svg") and "data:image" not in src:
                full_src = self.absolute_url(src)
                if full_src not in images:
                    images.append(full_src)

        return Article(
            url=url,
            title=title,
            content=content,
            author=author or "Vietnam Insiders",
            publish_date=publish_date,
            category=category,
            tags=tags,
            images=images[:10],
            language="en",
            country="Vietnam",
            city="",
        )
