# -*- coding: utf-8 -*-
"""
Detik Food Scraper (Sitemap Mode)
https://food.detik.com

Major Indonesian food portal by Detik.com.
Covers restaurant reviews, food news, culinary events across Indonesia.
Custom CMS with JSON-LD NewsArticle.

Sitemap Index: /sitemap.xml (custom, CDATA wrapped)
Relevant sitemaps (POI content only):
- tempat-makan/sitemap_web.xml (~100 articles, restaurant reviews)
- kabar-kuliner/sitemap_web.xml (~100 articles, food news)
Excluded: resep/ (recipes), makanan-anak/ (kids), sehat/ (health), foto/ (photos)

Content Structure:
- JSON-LD NewsArticle: headline, datePublished, author, image
- Content in div.detail__body (direct children: p, h2, h3, table)
- div.noncontent must be removed (ads/promos)

URL Pattern: /{subcategory}/d-{id}/{slug}
Subcategories: resto-dan-kafe, rumah-makan, warung-makan, info-kuliner, berita-boga
"""
import re
import json
from typing import List, Optional, Generator, Tuple
from xml.etree import ElementTree

from base_scraper import BaseScraper, Article
from config import SITE_CONFIGS


class DetikFoodScraper(BaseScraper):
    """
    Detik Food Scraper (Sitemap Mode)

    Indonesia's major food portal.
    Custom CMS + JSON-LD NewsArticle.
    ~200 articles (restaurant reviews + food news).
    CDATA-wrapped sitemap URLs.

    URL Pattern: /{subcategory}/d-{id}/{slug}
    """

    CONFIG_KEY = "detik_food"

    # Only these sitemap categories contain POI content
    POI_SITEMAPS = [
        "tempat-makan/sitemap_web.xml",
        "kabar-kuliner/sitemap_web.xml",
    ]

    # Category mapping from URL subcategory
    CATEGORY_MAP = {
        "resto-dan-kafe": "Restaurant & Cafe",
        "rumah-makan": "Restaurant",
        "warung-makan": "Warung",
        "pengalaman-bersantap": "Dining Experience",
        "online-food": "Online Food",
        "info-kuliner": "Culinary News",
        "berita-boga": "Food News",
    }

    def __init__(self, use_proxy: bool = False):
        config = SITE_CONFIGS.get(self.CONFIG_KEY, {})
        super().__init__(
            name=config.get("name", "Detik Food"),
            base_url=config.get("base_url", "https://food.detik.com"),
            delay=config.get("delay", 0.5),
            use_proxy=use_proxy,
            country=config.get("country", "Indonesia"),
            city=config.get("city", ""),
        )
        self._article_urls_cache = None

    def get_article_list_urls(self) -> Generator[str, None, None]:
        yield "sitemap://detik_food"

    def parse_article_list(self, html: str, list_url: str) -> List[str]:
        return []

    def fetch_urls_from_sitemap(self) -> List[Tuple[str, str]]:
        """Fetch article URLs from CDATA-wrapped sitemaps."""
        if self._article_urls_cache is not None:
            return self._article_urls_cache

        url_with_dates = []

        for sitemap_path in self.POI_SITEMAPS:
            sitemap_url = f"{self.base_url}/{sitemap_path}"
            response = self.fetch(sitemap_url)
            if not response:
                continue

            content = response.text
            # Extract URLs from CDATA blocks
            cdata_urls = re.findall(r'<!\[CDATA\[(https?://[^\]]+)\]\]>', content)

            count = 0
            for url in cdata_urls:
                url = url.strip()
                if self.is_valid_article_url(url):
                    url_with_dates.append((url, ""))
                    count += 1

            sitemap_name = sitemap_path.split("/")[0]
            self.logger.info(f"Sitemap {sitemap_name}: {count} articles")

        self._article_urls_cache = url_with_dates
        self.logger.info(f"Total articles from sitemaps: {len(url_with_dates)}")
        return url_with_dates

    def is_valid_article_url(self, url: str) -> bool:
        if not url or "food.detik.com" not in url:
            return False

        url_lower = url.lower()

        # Must have article ID pattern /d-{digits}/
        if not re.search(r'/d-\d+/', url_lower):
            return False

        # Exclude recipe and non-POI sections
        exclude_patterns = [
            "/resep/", "/makanan-anak/", "/sehat/",
            "/foto/", "/video/", "/indeks/",
            "/tag/", "/main/",
        ]
        if any(p in url_lower for p in exclude_patterns):
            return False

        return True

    def extract_content(self, html: str) -> str:
        soup = self.parse_html(html)

        content_el = soup.select_one("div.detail__body")
        if not content_el:
            return ""

        # Remove non-content elements
        for tag in content_el.find_all([
            "script", "style", "nav", "aside", "iframe",
            "button", "form", "noscript", "footer", "svg",
        ]):
            tag.decompose()

        # Remove ad/promo blocks
        for el in content_el.select("div.noncontent"):
            el.decompose()

        for css_sel in [
            "[class*='share']", "[class*='social']",
            "[class*='newsletter']", "[class*='related']",
            "[class*='sidebar']", "[class*='banner']",
            "[class*='ads']", "[class*='promo']",
        ]:
            for el in content_el.select(css_sel):
                el.decompose()

        content = content_el.decode_contents()
        content = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)
        content = content.strip()

        return content if len(content) > 200 else ""

    def parse_article(self, html: str, url: str) -> Optional[Article]:
        soup = self.parse_html(html)

        # Try JSON-LD first
        title = ""
        author = ""
        publish_date = ""
        images = []

        for script in soup.select("script[type='application/ld+json']"):
            try:
                data = json.loads(script.string)
                if isinstance(data, dict) and data.get("@type") == "NewsArticle":
                    title = data.get("headline", "")
                    publish_date = data.get("datePublished", "")

                    author_data = data.get("author", "")
                    if isinstance(author_data, dict):
                        author = author_data.get("name", "")
                    elif isinstance(author_data, list) and author_data:
                        author = author_data[0].get("name", "") if isinstance(author_data[0], dict) else str(author_data[0])

                    img_data = data.get("image", "")
                    if isinstance(img_data, dict):
                        img_url = img_data.get("url", "")
                        if img_url:
                            images.append(img_url)
                    elif isinstance(img_data, str) and img_data:
                        images.append(img_data)
                    elif isinstance(img_data, list):
                        for img in img_data[:5]:
                            if isinstance(img, dict):
                                img_url = img.get("url", "")
                                if img_url:
                                    images.append(img_url)
                            elif isinstance(img, str) and img:
                                images.append(img)
                    break
            except (json.JSONDecodeError, TypeError):
                continue

        # Fallback title from H1 or OG
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

        content = self.extract_content(html)

        # Fallback date from OG
        if not publish_date:
            pub_meta = soup.select_one("meta[property='article:published_time']")
            if pub_meta:
                publish_date = pub_meta.get("content", "")

        # Fallback image from OG
        if not images:
            og_image = soup.select_one("meta[property='og:image']")
            if og_image:
                img_url = og_image.get("content", "")
                if img_url:
                    images.append(img_url)

        # Category from URL subcategory
        category = self._extract_category(url)

        # City inference from title/content
        city = self._infer_city(url, title)

        return Article(
            url=url,
            title=title,
            content=content,
            author=author or "Detik Food",
            publish_date=publish_date,
            category=category,
            tags=[],
            images=images[:10],
            language="id",
            country="Indonesia",
            city=city,
        )

    def _extract_category(self, url: str) -> str:
        """Extract category from URL subcategory path."""
        for sub_path, cat_name in self.CATEGORY_MAP.items():
            if f"/{sub_path}/" in url:
                return cat_name
        return "Food"

    def _infer_city(self, url: str, title: str) -> str:
        """Infer city from URL and title."""
        text = f"{url} {title}".lower()

        city_keywords = {
            "jakarta": "Jakarta",
            "bandung": "Bandung",
            "surabaya": "Surabaya",
            "yogyakarta": "Yogyakarta",
            "jogja": "Yogyakarta",
            "semarang": "Semarang",
            "malang": "Malang",
            "bali": "Bali",
            "ubud": "Bali",
            "denpasar": "Bali",
            "medan": "Medan",
            "solo": "Solo",
            "bogor": "Bogor",
            "depok": "Depok",
            "tangerang": "Tangerang",
            "bekasi": "Bekasi",
        }

        for keyword, city_name in city_keywords.items():
            if keyword in text:
                return city_name

        return ""
