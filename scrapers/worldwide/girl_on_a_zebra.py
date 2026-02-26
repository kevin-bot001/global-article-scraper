# -*- coding: utf-8 -*-
"""
Girl on a Zebra Scraper (Sitemap Mode)
https://girlonazebra.com

Travel and food blog covering Asia-Pacific, Latin America, and Europe.
WordPress + Rank Math SEO, Gutenberg block editor.

Sitemap Index: /sitemap_index.xml (Rank Math)
- post-sitemap1.xml (201 articles)
- post-sitemap2.xml (200 articles)
- post-sitemap3.xml (2 articles)
Total: ~403 articles

Content Structure:
- No JSON-LD, uses HTML microdata (itemprop)
- OG meta tags provide title, description, image, section
- Content in div.entry-content.single-content
- Author in span.author.vcard
- Date in time[itemprop="datePublished"]
- Category in meta[property="article:section"]

URL Pattern: /{slug}/ (flat structure)
"""
import re
from typing import List, Optional, Generator, Tuple
from xml.etree import ElementTree

from base_scraper import BaseScraper, Article
from config import SITE_CONFIGS


class GirlOnAZebraScraper(BaseScraper):
    """
    Girl on a Zebra Scraper (Sitemap Mode)

    WordPress + Rank Math, no JSON-LD.
    OG tags + HTML microdata for metadata.
    ~403 articles about travel and food.

    URL Pattern: /{slug}/
    """

    CONFIG_KEY = "girl_on_a_zebra"

    def __init__(self, use_proxy: bool = False):
        config = SITE_CONFIGS.get(self.CONFIG_KEY, {})
        super().__init__(
            name=config.get("name", "Girl on a Zebra"),
            base_url=config.get("base_url", "https://girlonazebra.com"),
            delay=config.get("delay", 0.8),
            use_proxy=use_proxy,
            country=config.get("country", ""),
            city=config.get("city", ""),
        )
        self._article_urls_cache = None

    def get_article_list_urls(self) -> Generator[str, None, None]:
        yield "sitemap://girl_on_a_zebra"

    def parse_article_list(self, html: str, list_url: str) -> List[str]:
        return []

    def fetch_urls_from_sitemap(self) -> List[Tuple[str, str]]:
        """
        Fetch article URLs from Rank Math sitemaps.

        Parses sitemap_index.xml to find all post-sitemap*.xml files.
        """
        if self._article_urls_cache is not None:
            return self._article_urls_cache

        url_with_dates = []
        ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

        # Fetch sitemap index
        index_url = f"{self.base_url}/sitemap_index.xml"
        response = self.fetch(index_url)
        if not response:
            self._article_urls_cache = []
            return []

        # Find post-sitemaps
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
        if not url or "girlonazebra.com" not in url:
            return False

        url_lower = url.lower().rstrip("/")

        # Exclude the blog listing page
        if url_lower.endswith("/blog"):
            return False

        # Exclude homepage
        if url_lower == "https://girlonazebra.com":
            return False

        # Exclude non-article paths
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

        # Primary: div.entry-content.single-content
        content_el = soup.select_one("div.entry-content.single-content")
        if not content_el:
            content_el = soup.select_one(".entry-content")
        if not content_el:
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
            "[class*='share']", "[class*='social']",
            "[class*='newsletter']", "[class*='related']",
            "[class*='author-bio']", "[class*='sidebar']",
            "[class*='ad-']", "[class*='advertisement']",
        ]:
            for el in content_el.select(css_sel):
                el.decompose()

        content = content_el.decode_contents()
        content = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)
        content = content.strip()

        if len(content) > 200:
            return content

        return ""

    def parse_article(self, html: str, url: str) -> Optional[Article]:
        soup = self.parse_html(html)

        # Title
        title = ""
        h1 = soup.select_one("h1.entry-title")
        if h1:
            title = self.clean_text(h1.get_text())
        if not title:
            og_title = soup.select_one("meta[property='og:title']")
            if og_title:
                title = og_title.get("content", "")
                # Remove site name suffix
                if " - Girl on a Zebra" in title:
                    title = title.split(" - Girl on a Zebra")[0].strip()

        if not title:
            return None

        # Content
        content = self.extract_content(html)

        # Author - from span.author.vcard
        author = ""
        author_el = soup.select_one("span.author.vcard a.fn")
        if author_el:
            author = self.clean_text(author_el.get_text())

        # Publish date - from time[itemprop="datePublished"]
        publish_date = ""
        time_el = soup.select_one("time[itemprop='datePublished']")
        if time_el:
            publish_date = time_el.get("datetime", "")

        # Category - from meta[property="article:section"]
        category = ""
        section_meta = soup.select_one("meta[property='article:section']")
        if section_meta:
            category = section_meta.get("content", "")
        if not category:
            # Fallback: from entry-taxonomies
            tax_el = soup.select_one(".entry-taxonomies a[rel='tag']")
            if tax_el:
                category = self.clean_text(tax_el.get_text())

        # Tags
        tags = []
        for tag_el in soup.select(".entry-taxonomies a[rel='tag']"):
            tag = self.clean_text(tag_el.get_text())
            if tag and tag != category and tag not in tags:
                tags.append(tag)

        # Images
        images = []
        og_image = soup.select_one("meta[property='og:image']")
        if og_image:
            img_url = og_image.get("content", "")
            if img_url:
                images.append(img_url)

        return Article(
            url=url,
            title=title,
            content=content,
            author=author or "Girl on a Zebra",
            publish_date=publish_date,
            category=category,
            tags=tags,
            images=images[:10],
            language="en",
            country="",  # Global blog, auto-detect
            city="",
        )
