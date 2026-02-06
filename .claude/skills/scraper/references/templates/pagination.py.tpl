# -*- coding: utf-8 -*-
"""
${site_name} Scraper (Pagination Mode)
${base_url}
No sitemap available, uses pagination to discover articles
"""
import json
from typing import List, Optional, Generator

from base_scraper import BaseScraper, Article
from config import SITE_CONFIGS


class ${class_name}(BaseScraper):
    """
    ${site_name} Scraper

    No sitemap available - uses pagination mode
    List URL pattern: ${list_url_pattern}

    Features:
    - Pagination-based article discovery
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

        # Pagination configuration
        self.max_pages = config.get("max_pages", 50)

    def get_article_list_urls(self) -> Generator[str, None, None]:
        """Generate pagination URLs"""
        # First page (often no page number)
        yield f"{self.base_url}/${list_path}/"

        # Subsequent pages
        for page in range(2, self.max_pages + 1):
            # Common patterns:
            # Option 1: /blog/page/2/
            yield f"{self.base_url}/${list_path}/page/{page}/"
            # Option 2: /blog?page=2
            # yield f"{self.base_url}/${list_path}?page={page}"
            # Option 3: /blog/2
            # yield f"{self.base_url}/${list_path}/{page}"

    def parse_article_list(self, html: str, list_url: str) -> List[str]:
        """Extract article URLs from list page"""
        soup = self.parse_html(html)
        urls = []

        # Common article link selectors
        for selector in [
            "article a.entry-title-link",    # Genesis themes
            "h2.entry-title a",              # WordPress
            ".post-title a",                 # Generic blog
            "article h2 a",                  # Semantic HTML
            ".article-card a",               # Card layout
            ".blog-post a.title",            # Blog style
        ]:
            for link in soup.select(selector):
                href = link.get("href")
                if href:
                    full_url = self.absolute_url(href)
                    if self.is_valid_article_url(full_url) and full_url not in urls:
                        urls.append(full_url)

        # If no articles found with specific selectors, try broader search
        if not urls:
            for link in soup.select("a[href]"):
                href = link.get("href")
                if href:
                    full_url = self.absolute_url(href)
                    if self.is_valid_article_url(full_url) and full_url not in urls:
                        urls.append(full_url)

        return urls

    def is_valid_article_url(self, url: str) -> bool:
        """Check if URL is a valid article"""
        if not url or "${domain}" not in url:
            return False

        exclude_patterns = [
            "/category/", "/tag/", "/author/", "/page/",
            "/about", "/contact", "/privacy", "/terms",
            "/wp-admin/", "/wp-content/",
            "wp-json", "feed",
            # Exclude list pages themselves
            "/${list_path}/$",
        ]
        url_lower = url.lower()
        if any(p in url_lower for p in exclude_patterns):
            return False

        # Require article URL pattern
        # Example: must contain /article/ or specific slug pattern
        # if "/${article_path}/" not in url:
        #     return False

        return True

    def has_next_page(self, html: str, current_url: str) -> bool:
        """Check if there's a next page"""
        soup = self.parse_html(html)

        # Check for next page link
        for selector in [
            "a.next", ".pagination .next", "a[rel='next']",
            ".nav-next a", ".older-posts",
        ]:
            next_link = soup.select_one(selector)
            if next_link:
                return True

        # Check if current page has articles
        # If no articles, probably reached the end
        articles = self.parse_article_list(html, current_url)
        return len(articles) > 0

    def _parse_json_ld(self, soup) -> dict:
        """Parse JSON-LD structured data"""
        result = {}
        for script in soup.select('script[type="application/ld+json"]'):
            try:
                data = json.loads(script.string or "")
                items = data if isinstance(data, list) else [data]

                for item in items:
                    if item.get("@type") in ["Article", "BlogPosting"]:
                        if item.get("datePublished"):
                            result["datePublished"] = item["datePublished"]
                        if item.get("headline"):
                            result["headline"] = item["headline"]

                    if "author" in item:
                        author = item["author"]
                        if isinstance(author, dict):
                            result["author"] = author.get("name", "")

                    if "@graph" in item:
                        for graph_item in item["@graph"]:
                            if graph_item.get("@type") in ["Article", "BlogPosting"]:
                                if graph_item.get("datePublished"):
                                    result["datePublished"] = graph_item["datePublished"]
                                if graph_item.get("headline"):
                                    result["headline"] = graph_item["headline"]
                            if graph_item.get("@type") == "Person":
                                result["author"] = graph_item.get("name", "")

            except (json.JSONDecodeError, TypeError, KeyError):
                continue
        return result

    def extract_content(self, html: str) -> str:
        soup = self.parse_html(html)

        for selector in [${content_selectors}]:
            content_el = soup.select_one(selector)
            if content_el:
                for tag in content_el.find_all(["script", "style", "nav", "aside", "iframe"]):
                    tag.decompose()
                for css_sel in [".share", ".social", ".ad", ".related", ".newsletter"]:
                    for el in content_el.select(css_sel):
                        el.decompose()
                content = content_el.decode_contents()
                if len(content) > 200:
                    return content
        return ""

    def parse_article(self, html: str, url: str) -> Optional[Article]:
        soup = self.parse_html(html)
        json_ld = self._parse_json_ld(soup)

        # Title
        title = json_ld.get("headline", "")
        if not title:
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
        author = json_ld.get("author", "")
        if not author:
            author_el = soup.select_one("${author_selector}")
            if author_el:
                author = self.clean_text(author_el.get_text())

        # Date
        publish_date = json_ld.get("datePublished", "")
        if not publish_date:
            date_el = soup.select_one("${date_selector}")
            if date_el:
                publish_date = date_el.get("datetime") or self.clean_text(date_el.get_text())

        # Category
        category = ""
        cat_el = soup.select_one(".cat-links a, a[rel='category tag']")
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
        featured = soup.select_one(".post-thumbnail img, .featured-image img")
        if featured:
            src = featured.get("src") or featured.get("data-src")
            if src:
                images.append(self.absolute_url(src))

        for img in soup.select(".entry-content img, .post-content img"):
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


# ============================================================
# Note: Pagination mode does NOT use fetch_urls_from_sitemap()
# It uses get_article_list_urls() + parse_article_list() instead
# ============================================================
