# -*- coding: utf-8 -*-
"""
${site_name} Scraper (Google News Sitemap Mode)
${base_url}
News portal with Google News sitemap format
"""
import json
from typing import List, Optional, Generator
from xml.etree import ElementTree as ET

from base_scraper import BaseScraper, Article
from config import SITE_CONFIGS


class ${class_name}(BaseScraper):
    """
    ${site_name} Scraper

    Google News Sitemap format with <news:news> namespace

    Features:
    - Google News sitemap format
    - Publication date from <news:publication_date>
    - ${feature_1}
    """

    CONFIG_KEY = "${config_key}"

    def __init__(self, use_proxy: bool = False):
        config = SITE_CONFIGS.get(self.CONFIG_KEY, {})

        super().__init__(
            name=config.get("name", "${site_name}"),
            base_url=config.get("base_url", "${base_url}"),
            delay=config.get("delay", 0.5),
            use_proxy=use_proxy,
            country=config.get("country", "${country}"),
            default_city=config.get("default_city", "${default_city}"),
        )

    def get_article_list_urls(self) -> Generator[str, None, None]:
        yield "sitemap://"

    def parse_article_list(self, html: str, list_url: str) -> List[str]:
        return []

    def fetch_urls_from_sitemap(self) -> List[tuple]:
        """Fetch article URLs from Google News sitemap"""
        sitemap_url = f"{self.base_url}/${sitemap_url}"

        all_urls = []
        ns = {
            "ns": "http://www.sitemaps.org/schemas/sitemap/0.9",
            "news": "http://www.google.com/schemas/sitemap-news/0.9",
        }

        response = self.fetch(sitemap_url)
        if not response:
            return all_urls

        try:
            root = ET.fromstring(response.text)
            for url_el in root.findall(".//ns:url", ns):
                loc = url_el.find("ns:loc", ns)

                if loc is not None and loc.text:
                    url = loc.text.strip()
                    if not self.is_valid_article_url(url):
                        continue

                    # Get publication date from news:news
                    pub_date = ""
                    news_el = url_el.find("news:news", ns)
                    if news_el is not None:
                        pub_date_el = news_el.find("news:publication_date", ns)
                        if pub_date_el is not None and pub_date_el.text:
                            pub_date = pub_date_el.text.strip()

                    # Fallback to lastmod
                    if not pub_date:
                        lastmod = url_el.find("ns:lastmod", ns)
                        if lastmod is not None and lastmod.text:
                            pub_date = lastmod.text.strip()

                    all_urls.append((url, pub_date))

        except ET.ParseError as e:
            self.logger.error(f"Failed to parse sitemap: {sitemap_url} - {e}")

        self.logger.info(f"Found {len(all_urls)} articles from sitemap")
        return all_urls

    def is_valid_article_url(self, url: str) -> bool:
        if not url or "${domain}" not in url:
            return False

        exclude_patterns = [
            "/category/", "/tag/", "/author/", "/page/",
            "/about", "/contact", "/privacy",
        ]
        url_lower = url.lower()
        if any(p in url_lower for p in exclude_patterns):
            return False

        return True

    def extract_content(self, html: str) -> str:
        soup = self.parse_html(html)

        for selector in [${content_selectors}]:
            content_el = soup.select_one(selector)
            if content_el:
                for tag in content_el.find_all(["script", "style", "nav", "aside", "iframe"]):
                    tag.decompose()
                for css_sel in [".share", ".social", ".ad", ".related"]:
                    for el in content_el.select(css_sel):
                        el.decompose()
                content = content_el.decode_contents()
                if len(content) > 200:
                    return content
        return ""

    def parse_article(self, html: str, url: str) -> Optional[Article]:
        soup = self.parse_html(html)

        # Title
        title = ""
        title_el = soup.select_one("${title_selector}")
        if title_el:
            title = self.clean_text(title_el.get_text())

        if not title:
            og_title = soup.select_one("meta[property='og:title']")
            if og_title:
                title = og_title.get("content", "")

        if not title:
            return None

        content = self.extract_content(html)

        # Author
        author = ""
        author_el = soup.select_one("${author_selector}")
        if author_el:
            author = self.clean_text(author_el.get_text())

        # Publish date (may already have from sitemap, but try page too)
        publish_date = ""
        date_el = soup.select_one("${date_selector}")
        if date_el:
            publish_date = date_el.get("datetime") or self.clean_text(date_el.get_text())

        # Category
        category = ""
        cat_el = soup.select_one(".cat-links a, .article-category")
        if cat_el:
            category = self.clean_text(cat_el.get_text())

        # Tags
        tags = []
        for tag_el in soup.select(".tag-links a, a[rel='tag']"):
            tag = self.clean_text(tag_el.get_text())
            if tag and tag not in tags:
                tags.append(tag)

        # Images
        images = []
        featured = soup.select_one(".post-thumbnail img, .featured-image img, .article-image img")
        if featured:
            src = featured.get("src") or featured.get("data-src")
            if src:
                images.append(self.absolute_url(src))

        for img in soup.select(".entry-content img, .article-content img"):
            src = img.get("src") or img.get("data-src")
            if src and not src.endswith(".svg"):
                full_src = self.absolute_url(src)
                if full_src not in images:
                    images.append(full_src)

        return Article(
            url=url,
            title=title,
            content=content,
            author=author or "${default_author}",
            publish_date=publish_date,
            category=category,
            tags=tags,
            images=images[:10],
            language="${language}",
            country=self.country,
            city=self.default_city,
        )
