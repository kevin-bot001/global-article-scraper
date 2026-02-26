# -*- coding: utf-8 -*-
"""
IDN Times 爬虫
https://www.idntimes.com/

印尼大型综合媒体平台，支持多城市子域名

Features:
- Sitemap Index 格式，每个站点有 sitemap-web.xml / sitemap-news.xml
- JSON-LD NewsArticle 元数据
- 主站 + 城市子站（bali, jateng, ntb 等）
- 印尼语内容

Usage:
    scraper = IDNTimesScraper(city="main")   # 主站 www.idntimes.com
    scraper = IDNTimesScraper(city="bali")   # Bali子站 bali.idntimes.com
"""
import json
from typing import List, Optional, Tuple, Generator
from xml.etree import ElementTree

from base_scraper import BaseScraper, Article
from config import SITE_CONFIGS


class IDNTimesScraper(BaseScraper):
    """
    IDN Times 爬虫（支持多城市子域名）

    URL 模式:
    - 主站: www.idntimes.com/{category}/{subcategory}/{slug}
    - 子站: {city}.idntimes.com/{city}/{category}/{slug}

    Sitemap 结构:
    - 主站: www.idntimes.com/sitemap.xml -> /{category}/sitemap-web.xml
    - 子站: {city}.idntimes.com/{city}/sitemap.xml -> /{city}/{category}/sitemap-web.xml
    """

    CONFIG_KEY = "idntimes"

    # Available categories (both main site and subsites)
    CATEGORIES = [
        "food", "travel", "life", "news", "sport",
        "health", "business", "tech", "science",
    ]

    def __init__(self, use_proxy: bool = False, city: str = None):
        """
        Initialize scraper

        Args:
            use_proxy: Whether to use proxy
            city: City/site to scrape:
                  - "main" or None: Main site (www.idntimes.com)
                  - "bali", "jateng", etc.: City subsite
        """
        config = SITE_CONFIGS.get(self.CONFIG_KEY, {})
        cities_config = config.get("cities", {})

        # Default to main site
        self.city_key = city or "main"

        # Build base URL and get city info
        if self.city_key == "main":
            self.site_base_url = "https://www.idntimes.com"
            self.sitemap_prefix = ""
            display_city = config.get("city", "Jakarta")
            country = config.get("country", "Indonesia")
        else:
            if self.city_key not in cities_config:
                available = ["main"] + list(cities_config.keys())
                raise ValueError(f"Unsupported city: {self.city_key}, available: {available}")
            city_info = cities_config[self.city_key]
            self.site_base_url = f"https://{self.city_key}.idntimes.com"
            self.sitemap_prefix = f"/{self.city_key}"
            display_city = city_info.get("city", self.city_key)
            country = city_info.get("country", "Indonesia")

        super().__init__(
            name=f"IDN Times ({display_city})",
            base_url=self.site_base_url,
            delay=config.get("delay", 0.5),
            use_proxy=use_proxy,
            country=country,
            city=display_city,
        )

        # Filter categories from config
        self.categories = config.get("categories", []) or self.CATEGORIES
        # Subcategory filter (e.g., dining-guide under food)
        self.subcategories = config.get("subcategories", [])
        self._article_urls_cache = None

    def _fetch_sitemap_index(self) -> List[str]:
        """Fetch sitemap index and return list of sub-sitemap URLs"""
        sitemap_url = f"{self.site_base_url}{self.sitemap_prefix}/sitemap.xml"
        self.logger.info(f"Fetching sitemap index: {sitemap_url}")

        try:
            resp = self.fetch(sitemap_url)
            if not resp:
                return []

            root = ElementTree.fromstring(resp.content)
            ns = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}

            sub_sitemaps = []
            for sitemap in root.findall('.//sm:sitemap', ns):
                loc = sitemap.find('sm:loc', ns)
                if loc is not None and loc.text:
                    url = loc.text.strip()
                    # Only include sitemap-web.xml (skip news/image sitemaps)
                    if 'sitemap-web.xml' in url:
                        # Filter by category if configured
                        if self.categories:
                            for cat in self.categories:
                                if f"/{cat}/" in url:
                                    sub_sitemaps.append(url)
                                    break
                        else:
                            sub_sitemaps.append(url)

            self.logger.info(f"Found {len(sub_sitemaps)} sub-sitemaps")
            return sub_sitemaps

        except Exception as e:
            self.logger.error(f"Failed to fetch sitemap index: {e}")
            return []

    def fetch_urls_from_sitemap(self) -> List[Tuple[str, str]]:
        """
        Fetch article URLs from all sub-sitemaps

        Returns:
            [(url, lastmod), ...] sorted by lastmod descending
        """
        if self._article_urls_cache is not None:
            return self._article_urls_cache

        url_with_dates = []
        sub_sitemaps = self._fetch_sitemap_index()

        for sitemap_url in sub_sitemaps:
            try:
                resp = self.fetch(sitemap_url)
                if not resp:
                    continue

                root = ElementTree.fromstring(resp.content)
                ns = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}

                count = 0
                for url_elem in root.findall('.//sm:url', ns):
                    loc = url_elem.find('sm:loc', ns)
                    lastmod = url_elem.find('sm:lastmod', ns)

                    if loc is not None and loc.text:
                        url = loc.text.strip()
                        mod_date = lastmod.text.strip() if lastmod is not None and lastmod.text else ""

                        if self.is_valid_article_url(url):
                            url_with_dates.append((url, mod_date))
                            count += 1

                self.logger.debug(f"Sitemap {sitemap_url}: found {count} articles")

            except Exception as e:
                self.logger.error(f"Failed to fetch sitemap {sitemap_url}: {e}")

        # Sort by lastmod descending
        url_with_dates.sort(key=lambda x: x[1] if x[1] else "", reverse=True)

        self.logger.info(f"Total {len(url_with_dates)} articles from sitemaps (sorted by date)")
        self._article_urls_cache = url_with_dates
        return url_with_dates

    def get_article_list_urls(self) -> Generator[str, None, None]:
        """Signal sitemap mode - actual URL fetching done in fetch_urls_from_sitemap"""
        yield f"sitemap://idntimes-{self.city_key}"

    def parse_article_list(self, html: str, list_url: str) -> List[str]:
        """Not used in sitemap mode"""
        return []

    def is_valid_article_url(self, url: str) -> bool:
        """Check if URL is a valid article page"""
        if not url:
            return False

        # Must be from this site
        if self.site_base_url not in url:
            return False

        # Exclude non-article patterns
        exclude_patterns = [
            "/tag/", "/author/", "/search", "/sitemap",
            "/page/", "/category/", "/about", "/contact",
            ".jpg", ".png", ".pdf", ".xml",
        ]
        url_lower = url.lower()
        if any(p in url_lower for p in exclude_patterns):
            return False

        # URL must have at least 3 path segments (domain/category/subcategory/slug)
        path = url.replace(self.site_base_url, "").strip("/")
        parts = [p for p in path.split("/") if p]

        # For subsite: /{city}/{category}/{subcategory}/{slug} = 4 parts
        # For main: /{category}/{subcategory}/{slug} = 3 parts
        if len(parts) < 3:
            return False

        # Subcategory filter (e.g., only dining-guide)
        # URL structure for both main and subsite: /{category}/{subcategory}/{slug}
        if self.subcategories:
            subcategory = parts[1] if len(parts) > 1 else ""
            if subcategory not in self.subcategories:
                return False

        return True

    def _parse_json_ld(self, soup) -> dict:
        """Extract data from JSON-LD NewsArticle schema"""
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string)
                if isinstance(data, dict) and data.get("@type") == "NewsArticle":
                    return data
            except (json.JSONDecodeError, TypeError):
                continue
        return {}

    def extract_content(self, html: str) -> str:
        """Extract article body content"""
        soup = self.parse_html(html)

        # IDN Times content selectors
        content_selectors = [
            "article .content-block",
            ".article-content",
            ".entry-content",
            "article",
        ]

        for selector in content_selectors:
            content_el = soup.select_one(selector)
            if content_el:
                # Remove unwanted elements
                for tag in content_el.find_all(["script", "style", "nav", "aside", "iframe"]):
                    tag.decompose()
                for css_sel in [".share", ".social", ".ad", ".related", ".newsletter", ".tags"]:
                    for el in content_el.select(css_sel):
                        el.decompose()

                content = content_el.decode_contents()
                if len(content) > 200:
                    return content

        return ""

    def parse_article(self, html: str, url: str) -> Optional[Article]:
        """Parse article page and extract metadata"""
        soup = self.parse_html(html)

        # Try JSON-LD first (most reliable)
        json_ld = self._parse_json_ld(soup)

        # Title
        title = json_ld.get("headline") or ""
        if not title:
            h1 = soup.find("h1")
            if h1:
                title = self.clean_text(h1.get_text())
        if not title:
            return None

        # Content
        content = self.extract_content(html)

        # Author from JSON-LD
        author = ""
        if json_ld.get("author"):
            authors = json_ld["author"]
            if isinstance(authors, list) and authors:
                author = authors[0].get("name", "")
            elif isinstance(authors, dict):
                author = authors.get("name", "")

        # Publish date from JSON-LD
        publish_date = json_ld.get("datePublished") or ""

        # Category from URL
        category = ""
        path = url.replace(self.site_base_url, "").strip("/")
        parts = path.split("/")
        if self.city != "main" and len(parts) >= 2:
            # Subsite: /{city}/{category}/...
            category = parts[1].replace("-", " ").title()
        elif len(parts) >= 1:
            # Main: /{category}/...
            category = parts[0].replace("-", " ").title()

        # Images
        images = []
        if json_ld.get("image"):
            img_data = json_ld["image"]
            if isinstance(img_data, dict):
                img_url = img_data.get("url")
                if img_url:
                    images.append(img_url)
            elif isinstance(img_data, str):
                images.append(img_data)

        # OG image fallback
        og_image = soup.select_one("meta[property='og:image']")
        if og_image:
            img_url = og_image.get("content")
            if img_url and img_url not in images:
                images.append(img_url)

        # Keywords as tags
        tags = []
        if json_ld.get("keywords"):
            keywords = json_ld["keywords"]
            if isinstance(keywords, str):
                tags = [k.strip() for k in keywords.split(",") if k.strip()]
            elif isinstance(keywords, list):
                tags = keywords

        return Article(
            url=url,
            title=title,
            content=content,
            author=author or "IDN Times",
            publish_date=publish_date,
            category=category,
            tags=tags[:10],
            images=images[:10],
            language="id",  # Indonesian
            country="Indonesia",
            city=self.city.title() if self.city != "main" else "",
        )
