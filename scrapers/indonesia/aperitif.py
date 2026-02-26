# -*- coding: utf-8 -*-
"""
Aperitif Scraper (Sitemap Mode)
https://aperitif.com

Bali fine dining and culinary travel blog by Apéritif Restaurant.
Covers Ubud restaurants, Bali food news, wine events, culinary guides.
WordPress + Yoast SEO, Gutenberg blocks.

Sitemap Index: /sitemap.xml (Yoast)
- post-sitemap.xml (~128 articles)

Content Structure:
- No JSON-LD @graph (Yoast but stripped)
- OG meta tags: og:title, og:description, og:image
- article:published_time, article:modified_time
- Content in <article> -> div.col-12.col-lg-10 (Gutenberg blocks)
- No visible author element (default to site name)

URL Pattern: /{category}/{slug}/ (categories: blog, news, events)
"""
import re
from typing import List, Optional, Generator, Tuple
from xml.etree import ElementTree

from base_scraper import BaseScraper, Article
from config import SITE_CONFIGS


class AperitifScraper(BaseScraper):
    """
    Aperitif Scraper (Sitemap Mode)

    WordPress + Yoast, no JSON-LD.
    Bali fine dining blog (~128 articles).

    URL Pattern: /{category}/{slug}/
    """

    CONFIG_KEY = "aperitif"

    # Category mapping from URL path
    CATEGORY_MAP = {
        "blog": "Blog",
        "news": "News",
        "events": "Events",
    }

    def __init__(self, use_proxy: bool = False):
        config = SITE_CONFIGS.get(self.CONFIG_KEY, {})
        super().__init__(
            name=config.get("name", "Aperitif"),
            base_url=config.get("base_url", "https://www.aperitif.com"),
            delay=config.get("delay", 0.8),
            use_proxy=use_proxy,
            country=config.get("country", "Indonesia"),
            city=config.get("city", "Bali"),
        )
        self._article_urls_cache = None

    def get_article_list_urls(self) -> Generator[str, None, None]:
        yield "sitemap://aperitif"

    def parse_article_list(self, html: str, list_url: str) -> List[str]:
        return []

    def fetch_urls_from_sitemap(self) -> List[Tuple[str, str]]:
        """Fetch article URLs from Yoast post-sitemap."""
        if self._article_urls_cache is not None:
            return self._article_urls_cache

        url_with_dates = []
        ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

        index_url = f"{self.base_url}/sitemap.xml"
        response = self.fetch(index_url)
        if not response:
            self._article_urls_cache = []
            return []

        post_sitemap_urls = []
        try:
            root = ElementTree.fromstring(response.content)
            for sitemap_el in root.findall(".//sm:sitemap", ns):
                loc = sitemap_el.find("sm:loc", ns)
                if loc is not None and loc.text and "post-sitemap" in loc.text:
                    post_sitemap_urls.append(loc.text.strip())
        except ElementTree.ParseError as e:
            self.logger.error(f"Failed to parse sitemap index: {e}")
            self._article_urls_cache = []
            return []

        self.logger.info(f"Found {len(post_sitemap_urls)} post-sitemaps")

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
                            if mod_date and "T" in mod_date:
                                mod_date = mod_date.split("T")[0]
                            url_with_dates.append((url, mod_date))
                            count += 1

                sitemap_name = sitemap_url.split("/")[-1]
                self.logger.info(f"Sitemap {sitemap_name}: {count} articles")

            except ElementTree.ParseError as e:
                self.logger.error(f"Failed to parse sitemap: {sitemap_url} - {e}")

        url_with_dates.sort(key=lambda x: x[1] if x[1] else "", reverse=True)
        self._article_urls_cache = url_with_dates
        self.logger.info(f"Total articles from sitemaps: {len(url_with_dates)}")
        return url_with_dates

    def is_valid_article_url(self, url: str) -> bool:
        if not url or "aperitif.com" not in url:
            return False

        url_lower = url.lower().rstrip("/")

        # Must be under blog/, news/, or events/
        valid_prefixes = ["/blog/", "/news/", "/events/"]
        if not any(p in url_lower for p in valid_prefixes):
            return False

        exclude_patterns = [
            "/wp-admin/", "/wp-content/", "/wp-includes/",
            "/tag/", "/category/", "/author/", "/page/",
            "/search/", "/feed/", "/attachment/",
            ".jpg", ".png", ".pdf",
        ]
        if any(p in url_lower for p in exclude_patterns):
            return False

        return True

    def extract_content(self, html: str) -> str:
        soup = self.parse_html(html)

        # Content in <article> tag
        content_el = soup.select_one("article")
        if not content_el:
            return ""

        # Remove non-content elements
        for tag in content_el.find_all([
            "script", "style", "nav", "aside", "iframe",
            "button", "form", "noscript", "footer", "svg",
        ]):
            tag.decompose()

        for css_sel in [
            "[class*='addthis']", "[class*='share']", "[class*='social']",
            "[class*='newsletter']", "[class*='related']",
            "[class*='sidebar']", "[class*='aftoc']",
            "[class*='at-above-post']", "[class*='at-below-post']",
        ]:
            for el in content_el.select(css_sel):
                el.decompose()

        content = content_el.decode_contents()
        content = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)
        content = content.strip()

        return content if len(content) > 200 else ""

    def parse_article(self, html: str, url: str) -> Optional[Article]:
        soup = self.parse_html(html)

        # Title from H1 or OG
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

        content = self.extract_content(html)

        # Publish date from meta article:published_time
        publish_date = ""
        pub_meta = soup.select_one("meta[property='article:published_time']")
        if pub_meta:
            publish_date = pub_meta.get("content", "")

        # Category from URL path
        category = ""
        for prefix, cat_name in self.CATEGORY_MAP.items():
            if f"/{prefix}/" in url:
                category = cat_name
                break

        # Images from OG
        images = []
        og_image = soup.select_one("meta[property='og:image']")
        if og_image:
            img_url = og_image.get("content", "")
            if img_url:
                images.append(img_url)

        # City inference - most articles are about Ubud/Bali
        city = self._infer_city(url, title)

        return Article(
            url=url,
            title=title,
            content=content,
            author="Aperitif",  # No visible author on articles
            publish_date=publish_date,
            category=category,
            tags=[],
            images=images[:10],
            language="en",
            country="Indonesia",
            city=city,
        )

    def _infer_city(self, url: str, title: str) -> str:
        text = f"{url} {title}".lower()

        city_keywords = {
            "ubud": "Bali",
            "seminyak": "Bali",
            "canggu": "Bali",
            "sanur": "Bali",
            "nusa dua": "Bali",
            "kuta": "Bali",
            "jimbaran": "Bali",
            "uluwatu": "Bali",
            "bali": "Bali",
            "jakarta": "Jakarta",
        }

        for keyword, city_name in city_keywords.items():
            if keyword in text:
                return city_name

        # Default to Bali since it's an Ubud-based restaurant
        return "Bali"
