# -*- coding: utf-8 -*-
"""
Michelin Guide Scraper (Sitemap Mode)
https://guide.michelin.com

Global restaurant guide - editorial articles, dining recommendations, chef interviews.

Sitemap Index: /sitemap.xml -> /sitemap/article/{region}.xml (48 regions)
JSON-LD: Direct @type Article format (not @graph)
Content: div.js-poool__content > div.detail-page__content sections
URL Pattern: /{region}/en/article/{category}/{slug}
"""
import json
import re
from typing import List, Optional, Generator, Tuple
from urllib.parse import urlparse
from xml.etree import ElementTree

from base_scraper import BaseScraper, Article
from config import SITE_CONFIGS

# Region code -> (country, city) mapping for Michelin Guide URLs
REGION_MAP = {
    "sg": ("Singapore", "Singapore"),
    "hk": ("China", "Hong Kong"),
    "mo": ("China", "Macau"),
    "tw": ("Taiwan", "Taipei"),
    "th": ("Thailand", "Bangkok"),
    "my": ("Malaysia", "Kuala Lumpur"),
    "kr": ("Korea", "Seoul"),
    "jp": ("Japan", "Tokyo"),
    "vn": ("Vietnam", ""),
    "ph": ("Philippines", ""),
    "id": ("Indonesia", ""),
    "ae-az": ("UAE", "Abu Dhabi"),
    "ae-du": ("UAE", "Dubai"),
    "qa": ("Qatar", "Doha"),
    "us": ("United States", ""),
    "gb": ("United Kingdom", "London"),
    "fr": ("France", "Paris"),
    "it": ("Italy", ""),
    "es": ("Spain", ""),
    "de": ("Germany", ""),
    "nl": ("Netherlands", ""),
    "be": ("Belgium", ""),
    "ch": ("Switzerland", ""),
    "at": ("Austria", ""),
    "pt": ("Portugal", ""),
    "dk": ("Denmark", "Copenhagen"),
    "se": ("Sweden", "Stockholm"),
    "no": ("Norway", "Oslo"),
    "fi": ("Finland", "Helsinki"),
    "gr": ("Greece", ""),
    "tr": ("Turkey", "Istanbul"),
    "hr": ("Croatia", ""),
    "cz": ("Czech Republic", "Prague"),
    "hu": ("Hungary", "Budapest"),
    "pl": ("Poland", ""),
    "ie": ("Ireland", "Dublin"),
    "si": ("Slovenia", "Ljubljana"),
    "rs": ("Serbia", "Belgrade"),
    "ee": ("Estonia", "Tallinn"),
    "lv": ("Latvia", "Riga"),
    "lt": ("Lithuania", "Vilnius"),
    "lu": ("Luxembourg", "Luxembourg"),
    "mt": ("Malta", ""),
    "is": ("Iceland", "Reykjavik"),
    "br": ("Brazil", ""),
    "mx": ("Mexico", ""),
    "ar": ("Argentina", "Buenos Aires"),
    "ca": ("Canada", ""),
    "global": ("", ""),
}


class MichelinGuideScraper(BaseScraper):
    """
    Michelin Guide Scraper (Sitemap Mode)

    - Sitemap index with 48 regional article sitemaps
    - JSON-LD @type Article with rich structured data
    - Content in div.js-poool__content > div.detail-page__content sections
    - URL Pattern: /{region}/en/article/{category}/{slug}
    """

    CONFIG_KEY = "michelin_guide"

    def __init__(self, use_proxy: bool = False):
        config = SITE_CONFIGS.get(self.CONFIG_KEY, {})
        super().__init__(
            name=config.get("name", "Michelin Guide"),
            base_url=config.get("base_url", "https://guide.michelin.com"),
            delay=config.get("delay", 1.0),
            use_proxy=use_proxy,
            country=config.get("country", ""),
            city=config.get("city", ""),
        )
        self._article_urls_cache = None

    def get_article_list_urls(self) -> Generator[str, None, None]:
        """Generate list page URLs - use special marker for sitemap mode"""
        yield "sitemap://michelin_guide"

    def parse_article_list(self, html: str, list_url: str) -> List[str]:
        """Parse article list page - not used in sitemap mode"""
        return []

    def fetch_urls_from_sitemap(self) -> List[Tuple[str, str]]:
        """
        Fetch article URLs from all regional article sitemaps.

        Steps:
        1. Fetch sitemap index (/sitemap.xml)
        2. Extract all article sitemap URLs (pattern: /sitemap/article/{region}.xml)
        3. Fetch each article sitemap and collect URLs with lastmod

        Returns:
            [(url, lastmod), ...] sorted by lastmod descending
        """
        if self._article_urls_cache is not None:
            return self._article_urls_cache

        url_with_dates = []
        ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

        # Step 1: Fetch sitemap index
        index_url = f"{self.base_url}/sitemap.xml"
        response = self.fetch(index_url)

        article_sitemap_urls = []
        if response:
            try:
                root = ElementTree.fromstring(response.content)
                for sitemap_el in root.findall(".//sm:sitemap", ns):
                    loc = sitemap_el.find("sm:loc", ns)
                    if loc is not None and loc.text and "/sitemap/article/" in loc.text:
                        article_sitemap_urls.append(loc.text.strip())
            except ElementTree.ParseError as e:
                self.logger.error(f"Failed to parse sitemap index: {e}")

        if not article_sitemap_urls:
            self.logger.warning("No article sitemaps found in sitemap index")
            return []

        self.logger.info(f"Found {len(article_sitemap_urls)} article sitemaps")

        # Step 2: Fetch each article sitemap
        for sitemap_url in article_sitemap_urls:
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

                self.logger.debug(f"  {sitemap_url}: {count} articles")
            except ElementTree.ParseError as e:
                self.logger.error(f"Failed to parse sitemap: {sitemap_url} - {e}")

        # Sort by lastmod descending (newest first)
        url_with_dates.sort(key=lambda x: x[1] if x[1] else "", reverse=True)

        # Deduplicate URLs (same article may appear in multiple regional sitemaps)
        seen = set()
        deduped = []
        for url, lastmod in url_with_dates:
            # Normalize: extract path after the region/lang prefix to identify duplicates
            # e.g., /sg/en/article/foo and /en/article/foo are the same article
            path_match = re.search(r'/article/(.+)$', url)
            article_path = path_match.group(1) if path_match else url
            if article_path not in seen:
                seen.add(article_path)
                deduped.append((url, lastmod))

        self._article_urls_cache = deduped
        self.logger.info(
            f"Found {len(url_with_dates)} total article URLs, "
            f"{len(deduped)} unique after dedup"
        )
        return deduped

    def is_valid_article_url(self, url: str) -> bool:
        """Check if URL is a valid Michelin Guide article URL"""
        if not url or "guide.michelin.com" not in url:
            return False

        # Must contain /article/ in the path
        if "/article/" not in url:
            return False

        # Exclude non-English versions (we want /en/ paths)
        # Some URLs have /{region}/en/article/... and some have /en/article/...
        parsed = urlparse(url)
        path = parsed.path

        # Accept paths like /{region}/en/article/... or /en/article/...
        if "/en/article/" not in path:
            return False

        # Exclude known non-article patterns
        exclude_patterns = [
            "/tag/", "/category/", "/author/", "/page/",
            "/search/", "/login", "/register",
        ]
        url_lower = url.lower()
        if any(p in url_lower for p in exclude_patterns):
            return False

        return True

    def _extract_region_from_url(self, url: str) -> str:
        """
        Extract region code from URL path.

        Examples:
            /sg/en/article/... -> sg
            /en/article/... -> global
            /ae-du/en/article/... -> ae-du
        """
        parsed = urlparse(url)
        path = parsed.path.lstrip("/")
        parts = path.split("/")

        # Check if first part is a region code (not 'en')
        if len(parts) >= 3 and parts[0] != "en" and parts[1] == "en":
            return parts[0]

        return "global"

    def _get_country_city_from_url(self, url: str) -> Tuple[str, str]:
        """Get country and city from URL region code"""
        region = self._extract_region_from_url(url)
        return REGION_MAP.get(region, ("", ""))

    def _parse_json_ld(self, soup) -> dict:
        """
        Parse JSON-LD structured data.

        Michelin Guide uses direct @type: Article format (not @graph).

        Returns:
            Dict with headline, datePublished, author, articleSection, keywords, image
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
                    if data.get("dateCreated"):
                        result["dateCreated"] = data["dateCreated"]
                    if data.get("articleSection"):
                        result["articleSection"] = data["articleSection"]
                    if data.get("keywords"):
                        result["keywords"] = data["keywords"]
                    if data.get("image"):
                        result["image"] = data["image"]
                    if data.get("inLanguage"):
                        result["inLanguage"] = data["inLanguage"]

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
        Extract main content from HTML.

        Michelin Guide uses:
        - div.js-poool__content as the main content wrapper
        - Multiple div.detail-page__content sections inside
        """
        soup = self.parse_html(html)

        # Primary: js-poool__content contains all article content sections
        content_selectors = [
            ".js-poool__content",
            "div.detail-page__content-article",
            "div.detail-page__wrap-content",
        ]

        for selector in content_selectors:
            content_el = soup.select_one(selector)
            if not content_el:
                continue

            # Remove unwanted elements
            for tag in content_el.find_all([
                "script", "style", "nav", "aside", "iframe",
                "button", "form", "noscript"
            ]):
                tag.decompose()

            # Remove social share, author box, newsletter, ads
            for css_sel in [
                ".detail-page__content-share", ".js-share-container",
                ".article__author", ".social-share", ".share-buttons",
                ".newsletter", ".subscribe", ".ad", ".ads",
                ".related-articles", ".section-subscribe",
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

        # Parse JSON-LD structured data (primary source for metadata)
        json_ld = self._parse_json_ld(soup)

        # Title - prefer JSON-LD
        title = json_ld.get("headline", "")
        if not title:
            title_el = soup.select_one("h1")
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

        # Author - prefer JSON-LD
        author = json_ld.get("author", "")
        if not author:
            author_el = soup.select_one(".article__author")
            if author_el:
                # Extract just the author name, skip "Written by" text
                name_el = author_el.select_one("a") or author_el.select_one("span")
                if name_el:
                    author = self.clean_text(name_el.get_text())

        # Publish date - prefer JSON-LD
        publish_date = json_ld.get("datePublished", "")
        if not publish_date:
            publish_date = json_ld.get("dateCreated", "")
        if not publish_date:
            meta_date = soup.select_one("meta[property='article:published_time']")
            if meta_date:
                publish_date = meta_date.get("content", "")

        # Category - from JSON-LD articleSection or URL path
        category = json_ld.get("articleSection", "")
        if not category:
            # Extract from URL: /{region}/en/article/{category}/{slug}
            match = re.search(r'/article/([^/]+)/', url)
            if match:
                category = match.group(1).replace("-", " ").title()

        # Tags - from JSON-LD keywords
        tags = []
        keywords = json_ld.get("keywords", "")
        if keywords:
            if isinstance(keywords, str):
                tags = [t.strip() for t in keywords.split(",") if t.strip()]
            elif isinstance(keywords, list):
                tags = keywords

        # Images
        images = []
        # From JSON-LD
        json_image = json_ld.get("image", "")
        if json_image:
            if isinstance(json_image, str):
                images.append(json_image)
            elif isinstance(json_image, dict):
                img_url = json_image.get("url", "")
                if img_url:
                    images.append(img_url)

        # Main hero image
        main_img = soup.select_one(".detail-page__main-image img")
        if main_img:
            src = main_img.get("src") or main_img.get("data-src")
            if src and src not in images:
                images.append(self.absolute_url(src))

        # Content images
        content_area = soup.select_one(".js-poool__content") or soup.select_one(".detail-page__content-article")
        if content_area:
            for img in content_area.select("img"):
                src = img.get("src") or img.get("data-src")
                if src and not src.endswith(".svg") and "/assets/images/" not in src:
                    full_src = self.absolute_url(src)
                    if full_src not in images:
                        images.append(full_src)

        # Country/City from URL region code
        region_country, region_city = self._get_country_city_from_url(url)

        # Language
        language = json_ld.get("inLanguage", "en")
        if "-" in language:
            language = language.split("-")[0]  # "en-SG" -> "en"

        return Article(
            url=url,
            title=title,
            content=content,
            author=author or "MICHELIN Guide",
            publish_date=publish_date,
            category=category,
            tags=tags,
            images=images[:10],
            language=language,
            country=region_country,
            city=region_city,
        )
