# -*- coding: utf-8 -*-
"""
Travel+Leisure Asia Scraper (Multi-Region Sitemap Mode)
https://www.travelandleisureasia.com

Premium travel and lifestyle magazine covering destinations, dining, hotels,
and culture across Asia-Pacific. WordPress + Yoast SEO, multiple regional sites.

Regional Sites:
- /sea/  - Southeast Asia (default, ~5,100 articles)
- /sg/   - Singapore (~4,300 articles)
- /hk/   - Hong Kong (~4,200 articles)
- /th/   - Thailand (~4,200 articles)
- /my/   - Malaysia (~4,300 articles)

Sitemap: /{region}/sitemap_index.xml → post-sitemap.xml, post-sitemap2.xml, ...
JSON-LD: NewsArticle type (headline, datePublished, dateModified, author)
Content: <article> tag with <p>, <h2>, <h3> elements

URL Pattern: /{region}/{category}/{subcategory}/{slug}/
Categories: destinations, hotels, news, trips, dining, travel-tips, people, awards

Usage:
  python main.py -s travel_leisure_asia:sea    # Southeast Asia
  python main.py -s travel_leisure_asia:sg     # Singapore
  python main.py -s travel_leisure_asia:hk     # Hong Kong
  python main.py -s travel_leisure_asia:th     # Thailand
  python main.py -s travel_leisure_asia:my     # Malaysia
"""
import json
import re
from typing import List, Optional, Generator, Tuple
from xml.etree import ElementTree

from base_scraper import BaseScraper, Article
from config import SITE_CONFIGS


class TravelLeisureAsiaScraper(BaseScraper):
    """
    Travel+Leisure Asia Scraper (Multi-Region Sitemap Mode)

    WordPress + Yoast SEO with JSON-LD NewsArticle data.
    Parameterized by region: sea, sg, hk, th, my.
    ~22,000 total articles across all regions.

    URL Pattern: /{region}/{category}/{subcategory}/{slug}/
    """

    CONFIG_KEY = "travel_leisure_asia"

    # Region -> (country, city) mapping
    REGION_MAP = {
        "sea": ("", ""),              # Southeast Asia - auto-detect
        "sg": ("Singapore", "Singapore"),
        "hk": ("Hong Kong", "Hong Kong"),
        "th": ("Thailand", "Bangkok"),
        "my": ("Malaysia", "Kuala Lumpur"),
    }

    # Category slug -> display name
    CATEGORY_MAP = {
        "destinations": "Destinations",
        "hotels": "Hotels",
        "news": "News",
        "trips": "Trips",
        "dining": "Dining",
        "travel-tips": "Travel Tips",
        "people": "People",
        "awards": "Awards",
        "weddings-and-honeymoons": "Weddings",
    }

    def __init__(self, region: str = None, use_proxy: bool = False):
        config = SITE_CONFIGS.get(self.CONFIG_KEY, {})
        cities_config = config.get("cities", {})

        self.region = region or "sea"
        if self.region not in self.REGION_MAP:
            self.region = "sea"

        # Get country/city from region mapping
        region_country, region_city = self.REGION_MAP.get(self.region, ("", ""))

        # Override from cities config if available
        if self.region in cities_config:
            city_config = cities_config[self.region]
            if isinstance(city_config, dict):
                region_country = city_config.get("country", region_country)
                region_city = city_config.get("city", region_city)
            elif isinstance(city_config, str):
                region_country = city_config

        super().__init__(
            name=config.get("name", f"Travel+Leisure Asia ({self.region.upper()})"),
            base_url=config.get("base_url", "https://www.travelandleisureasia.com"),
            delay=config.get("delay", 0.5),
            use_proxy=use_proxy,
            country=region_country,
            city=region_city,
        )
        self._article_urls_cache = None

    def get_article_list_urls(self) -> Generator[str, None, None]:
        """Generate list page URLs - use special marker for sitemap mode"""
        yield f"sitemap://travel_leisure_asia:{self.region}"

    def parse_article_list(self, html: str, list_url: str) -> List[str]:
        """Parse article list page - not used in sitemap mode"""
        return []

    def fetch_urls_from_sitemap(self) -> List[Tuple[str, str]]:
        """
        Fetch article URLs from Yoast sitemaps for the current region.

        Reads sitemap_index.xml, finds all post-sitemap*.xml,
        then parses each for article URLs.

        Returns:
            [(url, lastmod), ...] sorted by lastmod descending
        """
        if self._article_urls_cache is not None:
            return self._article_urls_cache

        url_with_dates = []
        ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

        # Fetch sitemap index to get all post-sitemap URLs
        index_url = f"{self.base_url}/{self.region}/sitemap_index.xml"
        response = self.fetch(index_url)
        if not response:
            self.logger.error(f"Failed to fetch sitemap index: {index_url}")
            self._article_urls_cache = []
            return []

        # Parse sitemap index to find post-sitemaps
        post_sitemap_urls = []
        try:
            root = ElementTree.fromstring(response.content)
            for sitemap_el in root.findall(".//sm:sitemap", ns):
                loc = sitemap_el.find("sm:loc", ns)
                if loc is not None and loc.text:
                    url = loc.text.strip()
                    # Only process post-sitemaps (not page, category, etc.)
                    if "post-sitemap" in url:
                        post_sitemap_urls.append(url)
        except ElementTree.ParseError as e:
            self.logger.error(f"Failed to parse sitemap index: {e}")
            self._article_urls_cache = []
            return []

        self.logger.info(f"Found {len(post_sitemap_urls)} post-sitemaps for region {self.region}")

        # Parse each post-sitemap
        for sitemap_url in post_sitemap_urls:
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
                            # Normalize ISO datetime to date-only
                            if mod_date and "T" in mod_date:
                                mod_date = mod_date.split("T")[0]
                            url_with_dates.append((url, mod_date))
                            count += 1

                sitemap_name = sitemap_url.split("/")[-1]
                self.logger.info(f"Sitemap {sitemap_name}: {count} articles")

            except ElementTree.ParseError as e:
                self.logger.error(f"Failed to parse sitemap: {sitemap_url} - {e}")

        # Sort by lastmod descending
        url_with_dates.sort(key=lambda x: x[1] if x[1] else "", reverse=True)
        self._article_urls_cache = url_with_dates

        self.logger.info(f"Total articles from sitemaps ({self.region}): {len(url_with_dates)}")
        return url_with_dates

    def is_valid_article_url(self, url: str) -> bool:
        """Check if URL is a valid article URL"""
        if not url or "travelandleisureasia.com" not in url:
            return False

        url_lower = url.lower()

        # Must be from our region
        region_prefix = f"/{self.region}/"
        if region_prefix not in url_lower:
            return False

        # Exclude non-article paths
        exclude_patterns = [
            "/wp-admin/", "/wp-content/", "/wp-includes/",
            "/tag/", "/category/", "/author/", "/page/",
            "/search/", "/feed/", "/attachment/",
            "/about", "/contact", "/privacy", "/terms",
            "/advertise", "/subscribe", "/newsletter",
            ".jpg", ".png", ".pdf", ".css", ".js",
        ]
        if any(p in url_lower for p in exclude_patterns):
            return False

        # Must have at least category and slug after region
        # /{region}/{category}/{slug}/ or /{region}/{category}/{subcategory}/{slug}/
        path = url_lower.split(f"/{self.region}/", 1)[-1].strip("/")
        segments = [s for s in path.split("/") if s]
        if len(segments) < 2:
            return False

        return True

    def _extract_json_ld(self, soup) -> dict:
        """Extract NewsArticle data from JSON-LD"""
        result = {}

        for script in soup.find_all("script", type="application/ld+json"):
            if not script.string:
                continue
            try:
                data = json.loads(script.string)
            except (json.JSONDecodeError, TypeError):
                continue

            if not isinstance(data, dict):
                continue

            article_data = None

            # Direct NewsArticle/Article
            if data.get("@type") in ("NewsArticle", "Article", "BlogPosting"):
                article_data = data

            # Yoast @graph pattern
            elif isinstance(data.get("@graph"), list):
                for item in data["@graph"]:
                    if isinstance(item, dict) and item.get("@type") in ("NewsArticle", "Article", "BlogPosting"):
                        article_data = item
                        break

            if not article_data:
                continue

            if article_data.get("headline"):
                result["title"] = article_data["headline"]

            if article_data.get("datePublished"):
                result["date"] = article_data["datePublished"]

            if article_data.get("dateModified"):
                result["date_modified"] = article_data["dateModified"]

            author = article_data.get("author", {})
            if isinstance(author, dict) and author.get("name"):
                result["author"] = author["name"]
            elif isinstance(author, list):
                names = [a.get("name", "") for a in author if isinstance(a, dict)]
                result["author"] = ", ".join(n for n in names if n)

            break

        return result

    def _category_from_url(self, url: str) -> str:
        """Extract category from URL path"""
        # /{region}/{category}/...
        path = url.split(f"/{self.region}/", 1)[-1] if f"/{self.region}/" in url else ""
        segments = [s for s in path.strip("/").split("/") if s]
        if segments:
            slug = segments[0]
            return self.CATEGORY_MAP.get(slug, slug.replace("-", " ").title())
        return ""

    def extract_content(self, html: str) -> str:
        """
        Extract main content from <article> tag.

        T+L Asia uses standard WordPress structure with content
        directly in <article> tag using <p>, <h2>, <h3> elements.
        """
        soup = self.parse_html(html)

        article = soup.find("article")
        if not article:
            return ""

        # Remove non-content elements
        for tag in article.find_all([
            "script", "style", "nav", "aside", "iframe",
            "button", "form", "noscript", "footer", "svg",
        ]):
            tag.decompose()

        # Remove ad/social/newsletter/related widgets
        for css_sel in [
            "[class*='share']", "[class*='social']",
            "[class*='newsletter']", "[class*='related']",
            "[class*='advertisement']", "[class*='sidebar']",
            "[class*='author-bio']", "[class*='author-card']",
            "[id*='taboola']", "[id*='outbrain']",
        ]:
            for el in article.select(css_sel):
                el.decompose()

        content = article.decode_contents()
        content = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)
        content = content.strip()

        if len(content) > 200:
            return content

        return ""

    def parse_article(self, html: str, url: str) -> Optional[Article]:
        """Parse article detail page using JSON-LD and DOM selectors"""
        soup = self.parse_html(html)

        # JSON-LD data
        json_ld = self._extract_json_ld(soup)

        # Title
        title = json_ld.get("title", "")
        if not title:
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

        # Author
        author = json_ld.get("author", "")

        # Publish date
        publish_date = json_ld.get("date", "")

        # Category from URL
        category = self._category_from_url(url)

        # Tags
        tags = []
        for tag_el in soup.select("a[rel='tag']"):
            tag = self.clean_text(tag_el.get_text())
            if tag and tag not in tags:
                tags.append(tag)

        # Images
        images = []
        og_image = soup.select_one("meta[property='og:image']")
        if og_image:
            img_url = og_image.get("content", "")
            if img_url:
                images.append(img_url)

        # Country/city - use region default, can be overridden by auto-detect
        country = self.country
        city = self.city

        return Article(
            url=url,
            title=title,
            content=content,
            author=author or "Travel+Leisure Asia",
            publish_date=publish_date,
            category=category,
            tags=tags,
            images=images[:10],
            language="en",
            country=country,
            city=city,
        )
