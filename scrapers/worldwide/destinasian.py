# -*- coding: utf-8 -*-
"""
DestinAsian Scraper (Sitemap Mode)
https://destinasian.com

Premium Asian travel magazine covering destinations, dining, hotels, and culture
across Asia-Pacific. Based on WordPress + Yoast SEO.

Sitemap Index: /sitemap.xml
Key Sitemaps:
- editorial-sitemap.xml  (281 articles - long-form travel features)
- post-sitemap.xml       (368 entries - POI with city-type-name pattern)
- update-sitemap.xml     (111 articles - news & updates)
- advertorial-sitemap.xml, honors-circle-sitemap.xml, etc.

Content Structure:
- No JSON-LD - uses GraphQL/Apollo state management
- Author and date in Apollo state (__APOLLO_STATE__)
- Content in WordPress <p> tags with .wp-caption figures
- POI entries have address, transit, website data

URL Patterns:
- /editorial/{slug}/                 - Long-form features
- /{city}-{type}-{name}/           - POI entries (tokyo-dining-two-rooms)
- /update/{slug}/                   - News updates
"""
import json
import re
from typing import List, Optional, Generator, Tuple
from xml.etree import ElementTree

from base_scraper import BaseScraper, Article
from config import SITE_CONFIGS


class DestinAsianScraper(BaseScraper):
    """
    DestinAsian Scraper (Sitemap Mode)

    WordPress + Yoast SEO, multiple sitemap types.
    Uses Apollo/GraphQL state for metadata.
    Covers editorial features, POI entries, and news updates.

    URL Pattern: /editorial/{slug}/ or /{city}-{type}-{name}/
    """

    CONFIG_KEY = "destinasian"

    # Sitemaps to crawl (from sitemap index)
    TARGET_SITEMAPS = [
        "editorial-sitemap.xml",
        "post-sitemap.xml",
        "update-sitemap.xml",
        "advertorial-sitemap.xml",
        "honors-circle-sitemap.xml",
    ]

    def __init__(self, use_proxy: bool = False):
        config = SITE_CONFIGS.get(self.CONFIG_KEY, {})
        super().__init__(
            name=config.get("name", "DestinAsian"),
            base_url=config.get("base_url", "https://destinasian.com"),
            delay=config.get("delay", 0.8),
            use_proxy=use_proxy,
            country=config.get("country", ""),
            city=config.get("city", ""),
        )
        self._article_urls_cache = None

    def get_article_list_urls(self) -> Generator[str, None, None]:
        """Generate list page URLs - use special marker for sitemap mode"""
        yield "sitemap://destinasian"

    def parse_article_list(self, html: str, list_url: str) -> List[str]:
        """Parse article list page - not used in sitemap mode"""
        return []

    def fetch_urls_from_sitemap(self) -> List[Tuple[str, str]]:
        """
        Fetch article URLs from multiple Yoast sitemaps

        Returns:
            [(url, lastmod), ...] sorted by lastmod descending
        """
        if self._article_urls_cache is not None:
            return self._article_urls_cache

        url_with_dates = []
        ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

        # DestinAsian uses query-param style sitemap URLs:
        # /sitemap.xml?sitemap=editorial-sitemap.xml
        for sitemap_name in self.TARGET_SITEMAPS:
            sitemap_url = f"{self.base_url}/sitemap.xml?sitemap={sitemap_name}"
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
                        # Normalize http to https
                        if url.startswith("http://"):
                            url = url.replace("http://", "https://", 1)
                        if self.is_valid_article_url(url):
                            mod_date = lastmod.text.strip() if lastmod is not None and lastmod.text else ""
                            url_with_dates.append((url, mod_date))
                            count += 1

                self.logger.info(f"Sitemap {sitemap_name}: {count} articles")

            except ElementTree.ParseError as e:
                self.logger.error(f"Failed to parse sitemap: {sitemap_name} - {e}")

        # Sort by lastmod descending
        url_with_dates.sort(key=lambda x: x[1] if x[1] else "", reverse=True)
        self._article_urls_cache = url_with_dates

        self.logger.info(f"Total articles from sitemaps: {len(url_with_dates)}")
        return url_with_dates

    def is_valid_article_url(self, url: str) -> bool:
        """Check if URL is a valid article URL"""
        if not url or "destinasian.com" not in url:
            return False

        url_lower = url.lower()

        # Exclude non-article paths
        exclude_patterns = [
            "/wp-admin/", "/wp-content/", "/wp-includes/",
            "/tag/", "/category/", "/author/", "/page/",
            "/search/", "/feed/", "/attachment/",
            "/about", "/contact", "/privacy", "/terms",
            "/advertise", "/subscribe", "/newsletter",
            "/contributors/", "/contributor/",
            ".jpg", ".png", ".pdf", ".css", ".js",
        ]
        if any(p in url_lower for p in exclude_patterns):
            return False

        # Exclude homepage
        path = url_lower.replace("https://destinasian.com", "").replace("http://destinasian.com", "").strip("/")
        if not path:
            return False

        # Exclude pure category/taxonomy pages (single segment like /indonesia/)
        # But allow POI entries like /tokyo-dining-two-rooms/
        segments = [s for s in path.split("/") if s]
        if len(segments) == 1:
            # Single segment: could be category page or POI entry
            # POI entries have pattern: city-type-name (with hyphens)
            slug = segments[0]
            # Category pages are typically short single words
            category_pages = [
                "editorial", "update", "advertorial", "luxe-list",
                "readers-choice-award", "luxury-travel", "honors-circle",
                "travel-guides", "indonesia", "singapore", "thailand",
                "japan", "malaysia", "vietnam", "philippines", "taiwan",
                "hong-kong", "india", "china", "korea", "cambodia",
                "sri-lanka", "myanmar", "laos", "australia", "maldives",
            ]
            if slug in category_pages:
                return False

        return True

    def _extract_next_data(self, soup) -> dict:
        """
        Extract all data from __NEXT_DATA__ script tag.

        DestinAsian is a Next.js app with Apollo state.
        All article data lives in __NEXT_DATA__ → props.pageProps.__APOLLO_STATE__

        Returns dict with: title, content, date, author, categories, images
        """
        result = {}

        next_data_script = soup.find("script", id="__NEXT_DATA__")
        if not next_data_script or not next_data_script.string:
            return result

        try:
            data = json.loads(next_data_script.string)
        except (json.JSONDecodeError, TypeError):
            return result

        apollo_state = (
            data.get("props", {})
            .get("pageProps", {})
            .get("__APOLLO_STATE__", {})
        )
        if not apollo_state:
            return result

        # Find the main content entry (Editorial, Post, Update, etc.)
        content_types = ("Editorial:", "Post:", "Update:", "Advertorial:", "HonorsCircle:")
        for key, val in apollo_state.items():
            if not any(key.startswith(ct) for ct in content_types):
                continue
            if not isinstance(val, dict):
                continue

            # Title
            if val.get("title"):
                result["title"] = val["title"]

            # Content (HTML)
            if val.get("content"):
                result["content"] = val["content"]

            # Date
            if val.get("date"):
                result["date"] = val["date"]

            # Author
            author_data = val.get("author")
            if isinstance(author_data, dict):
                node = author_data.get("node", {})
                if isinstance(node, dict) and node.get("name"):
                    result["author"] = node["name"]

            # Categories
            cats_data = val.get("categories")
            if isinstance(cats_data, dict):
                edges = cats_data.get("edges", [])
                cat_names = []
                for edge in edges:
                    if isinstance(edge, dict):
                        node = edge.get("node", {})
                        if isinstance(node, dict) and node.get("name"):
                            name = node["name"]
                            if name not in cat_names:
                                cat_names.append(name)
                if cat_names:
                    result["categories"] = cat_names

            # Featured image
            feat_img = val.get("featuredImage")
            if isinstance(feat_img, dict):
                node = feat_img.get("node", {})
                if isinstance(node, dict) and node.get("sourceUrl"):
                    result["featured_image"] = node["sourceUrl"]

            # Found our main entry, stop
            break

        return result

    def extract_content(self, html: str) -> str:
        """
        Extract main content from HTML.

        DestinAsian is a Next.js/React app - the rendered HTML has no <p> tags.
        Content lives in __NEXT_DATA__ Apollo state as raw HTML string.
        """
        soup = self.parse_html(html)

        # Primary: extract from __NEXT_DATA__
        next_data = self._extract_next_data(soup)
        raw_content = next_data.get("content", "")
        if raw_content and len(raw_content) > 200:
            return raw_content

        # Fallback: try rendered DOM (unlikely to work for Next.js SSR)
        content_selectors = [
            ".entry-content",
            ".post-content",
            "article",
        ]
        for selector in content_selectors:
            content_el = soup.select_one(selector)
            if content_el:
                for tag in content_el.find_all([
                    "script", "style", "nav", "aside", "iframe",
                    "button", "form", "noscript", "footer"
                ]):
                    tag.decompose()

                content = content_el.decode_contents()
                content = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)
                content = content.strip()
                if len(content) > 200:
                    return content

        return ""

    def _infer_category_from_url(self, url: str) -> str:
        """Infer category from URL path pattern"""
        url_lower = url.lower()

        if "/editorial/" in url_lower:
            return "Editorial"
        if "/update/" in url_lower:
            return "Update"
        if "/advertorial/" in url_lower:
            return "Advertorial"
        if "/luxury-travel/" in url_lower:
            return "Luxury Travel"
        if "/honors-circle/" in url_lower:
            return "Honors Circle"
        if "/readers-choice-award/" in url_lower:
            return "Readers' Choice"

        # POI entries: {city}-dining-{name}, {city}-hotels-{name}, etc.
        path = url_lower.replace("https://destinasian.com/", "").replace("http://destinasian.com/", "").strip("/")
        if "-dining-" in path or "-restaurants-" in path:
            return "Dining"
        if "-hotels-" in path or "-resorts-" in path:
            return "Hotels"
        if "-nightlife-" in path or "-bars-" in path:
            return "Nightlife"
        if "-attractions-" in path or "-museums-" in path:
            return "Attractions"
        if "-shopping-" in path or "-shops-" in path:
            return "Shopping"
        if "-spas-" in path:
            return "Spas"

        return ""

    def parse_article(self, html: str, url: str) -> Optional[Article]:
        """Parse article detail page using __NEXT_DATA__ Apollo state"""
        soup = self.parse_html(html)

        # Primary data source: __NEXT_DATA__
        next_data = self._extract_next_data(soup)

        # Title - prefer __NEXT_DATA__, fallback to DOM
        title = next_data.get("title", "")
        if not title:
            h1 = soup.select_one("h1")
            if h1:
                title = self.clean_text(h1.get_text())
        if not title:
            og_title = soup.select_one("meta[property='og:title']")
            if og_title:
                title = og_title.get("content", "")
                if title and " | " in title:
                    title = title.split(" | ")[0].strip()

        if not title:
            return None

        # Content - from __NEXT_DATA__
        content = next_data.get("content", "")
        if not content:
            content = self.extract_content(html)

        # Author
        author = next_data.get("author", "")

        # Publish date
        publish_date = next_data.get("date", "")

        # Categories - deduplicated from __NEXT_DATA__
        categories = next_data.get("categories", [])

        # Pick the most specific category
        category = ""
        if categories:
            broad_categories = {
                "indonesia", "singapore", "thailand", "japan", "malaysia",
                "vietnam", "philippines", "taiwan", "hong kong", "india",
                "china", "korea", "cambodia", "australia", "outside asia",
                "maldives", "myanmar", "laos", "sri lanka", "mongolia",
            }
            for cat in categories:
                if cat.lower() not in broad_categories:
                    category = cat
                    break
            if not category and categories:
                category = categories[0]

        if not category:
            category = self._infer_category_from_url(url)

        # Tags - remaining categories (deduplicated)
        seen = set()
        tags = []
        for c in categories:
            if c != category and c not in seen:
                tags.append(c)
                seen.add(c)

        # Images
        images = []
        # Featured image from __NEXT_DATA__
        feat_img = next_data.get("featured_image", "")
        if feat_img:
            images.append(feat_img)

        # og:image as fallback
        og_image = soup.select_one("meta[property='og:image']")
        if og_image:
            img_url = og_image.get("content", "")
            if img_url and img_url not in images:
                images.append(img_url)

        return Article(
            url=url,
            title=title,
            content=content,
            author=author or "DestinAsian",
            publish_date=publish_date,
            category=category,
            tags=tags,
            images=images[:10],
            language="en",
            country="",  # Global site, auto-detect from content
            city="",
        )
