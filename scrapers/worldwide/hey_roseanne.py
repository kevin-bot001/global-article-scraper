# -*- coding: utf-8 -*-
"""
Hey Roseanne Scraper (Sitemap Mode)
https://heyroseanne.com

Korean culture and travel blog focused on K-drama filming locations,
Seoul travel guides, and Korean food recommendations.
WordPress + Rank Math SEO.

Sitemap Index: /sitemap_index.xml (Rank Math)
- post-sitemap.xml (~159 articles)

Content Structure:
- No JSON-LD, uses HTML microdata (itemprop)
- OG meta tags: og:title, og:description, og:image, article:section
- Content in div.entry-content
- Author in span.author.vcard
- Date in time[datetime][itemprop="datePublished"]
- Category in meta[property="article:section"] (e.g., "South Korea")

URL Pattern: /{slug}/ (flat structure)
"""
import re
from typing import List, Optional, Generator, Tuple
from xml.etree import ElementTree

from base_scraper import BaseScraper, Article
from config import SITE_CONFIGS


class HeyRoseanneScraper(BaseScraper):
    """
    Hey Roseanne Scraper (Sitemap Mode)

    WordPress + Rank Math, no JSON-LD.
    Korea-focused travel blog (~159 articles).

    URL Pattern: /{slug}/
    """

    CONFIG_KEY = "hey_roseanne"

    def __init__(self, use_proxy: bool = False):
        config = SITE_CONFIGS.get(self.CONFIG_KEY, {})
        super().__init__(
            name=config.get("name", "Hey Roseanne"),
            base_url=config.get("base_url", "https://heyroseanne.com"),
            delay=config.get("delay", 0.8),
            use_proxy=use_proxy,
            country=config.get("country", "South Korea"),
            city=config.get("city", ""),
        )
        self._article_urls_cache = None

    def get_article_list_urls(self) -> Generator[str, None, None]:
        yield "sitemap://hey_roseanne"

    def parse_article_list(self, html: str, list_url: str) -> List[str]:
        return []

    def fetch_urls_from_sitemap(self) -> List[Tuple[str, str]]:
        """Fetch article URLs from Rank Math sitemaps."""
        if self._article_urls_cache is not None:
            return self._article_urls_cache

        url_with_dates = []
        ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

        index_url = f"{self.base_url}/sitemap_index.xml"
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
        if not url or "heyroseanne.com" not in url:
            return False

        url_lower = url.lower().rstrip("/")

        # Exclude blog listing, homepage
        if url_lower in ("https://heyroseanne.com", "https://heyroseanne.com/blog"):
            return False

        exclude_patterns = [
            "/wp-admin/", "/wp-content/", "/wp-includes/",
            "/tag/", "/category/", "/author/", "/page/",
            "/search/", "/feed/", "/attachment/",
            "/about", "/contact", "/privacy", "/terms",
            "/disclosure", "/work-with",
            ".jpg", ".png", ".pdf",
        ]
        if any(p in url_lower for p in exclude_patterns):
            return False

        return True

    def extract_content(self, html: str) -> str:
        soup = self.parse_html(html)

        content_el = soup.select_one("div.entry-content")
        if not content_el:
            content_el = soup.select_one("article")

        if not content_el:
            return ""

        for tag in content_el.find_all([
            "script", "style", "nav", "aside", "iframe",
            "button", "form", "noscript", "footer", "svg",
        ]):
            tag.decompose()

        for css_sel in [
            "[class*='share']", "[class*='social']",
            "[class*='newsletter']", "[class*='related']",
            "[class*='author-bio']", "[class*='sidebar']",
        ]:
            for el in content_el.select(css_sel):
                el.decompose()

        content = content_el.decode_contents()
        content = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)
        content = content.strip()

        return content if len(content) > 200 else ""

    def parse_article(self, html: str, url: str) -> Optional[Article]:
        soup = self.parse_html(html)

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

        content = self.extract_content(html)

        # Author
        author = ""
        author_el = soup.select_one("span.author.vcard a")
        if author_el:
            author = self.clean_text(author_el.get_text())

        # Publish date
        publish_date = ""
        time_el = soup.select_one("time[itemprop='datePublished']")
        if not time_el:
            time_el = soup.select_one("time[datetime]")
        if time_el:
            publish_date = time_el.get("datetime", "")

        # Category
        category = ""
        section_meta = soup.select_one("meta[property='article:section']")
        if section_meta:
            category = section_meta.get("content", "")

        # Images
        images = []
        og_image = soup.select_one("meta[property='og:image']")
        if og_image:
            img_url = og_image.get("content", "")
            if img_url:
                images.append(img_url)

        # City inference from title/URL for Korean cities
        city = self._infer_city(url, title)

        return Article(
            url=url,
            title=title,
            content=content,
            author=author or "Roseanne Ducut",
            publish_date=publish_date,
            category=category,
            tags=[],
            images=images[:10],
            language="en",
            country="South Korea",
            city=city,
        )

    def _infer_city(self, url: str, title: str) -> str:
        text = f"{url} {title}".lower()

        city_keywords = {
            "seoul": "Seoul",
            "busan": "Busan",
            "suwon": "Suwon",
            "jeju": "Jeju",
            "incheon": "Incheon",
            "gyeongju": "Gyeongju",
            "daegu": "Daegu",
            "jeonju": "Jeonju",
            "gangnam": "Seoul",
            "hongdae": "Seoul",
            "myeongdong": "Seoul",
            "itaewon": "Seoul",
        }

        for keyword, city_name in city_keywords.items():
            if keyword in text:
                return city_name

        return ""
