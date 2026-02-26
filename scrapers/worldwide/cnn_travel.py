# -*- coding: utf-8 -*-
"""
CNN Travel Scraper (Category Page Mode)
https://www.cnn.com/travel

CNN Travel covers food, destinations, hotels, airlines and travel news worldwide.

Features:
- 5 section pages (travel home, food-and-drink, destinations, stay, news)
- JSON-LD NewsArticle metadata (headline, author, datePublished, articleBody)
- Content in div.article__content with paragraph-elevate classes
- curl_cffi bypasses CNN protection
- URL patterns: /YYYY/MM/DD/travel/slug or /travel/slug

Usage:
    scraper = CnnTravelScraper()
    articles = scraper.scrape_all(limit=10)
"""
import json
import re
from typing import List, Optional, Generator
from concurrent.futures import ThreadPoolExecutor, as_completed

from base_scraper import BaseScraper, Article, normalize_date
from config import SITE_CONFIGS, CONCURRENCY_CONFIG


class CnnTravelScraper(BaseScraper):
    """
    CNN Travel Scraper

    Fetches articles from CNN Travel section pages.
    Uses JSON-LD NewsArticle for metadata extraction.
    """

    CONFIG_KEY = "cnn_travel"

    # CNN Travel sections to scrape
    SECTIONS = [
        "",                # /travel main page
        "/food-and-drink", # food & drink articles
        "/destinations",   # destination guides
        "/stay",           # hotel/accommodation articles
        "/news",           # travel news
    ]

    def __init__(self, use_proxy: bool = False):
        config = SITE_CONFIGS.get(self.CONFIG_KEY, {})

        super().__init__(
            name=config.get("name", "CNN Travel"),
            base_url=config.get("base_url", "https://www.cnn.com"),
            delay=config.get("delay", 1.0),
            use_proxy=use_proxy,
            country=config.get("country", ""),
            city=config.get("city", ""),
        )

    def get_article_list_urls(self) -> Generator[str, None, None]:
        """Signal category mode (not used in scrape_all)"""
        yield "category://"

    def parse_article_list(self, html: str, list_url: str) -> List[str]:
        """Not used in category mode"""
        return []

    def fetch_urls_from_sitemap(self) -> List[tuple]:
        """Not using sitemap mode"""
        return []

    def _fetch_section_urls(self, section: str) -> List[str]:
        """
        Fetch article URLs from a CNN Travel section page.

        Args:
            section: Section path suffix (e.g., "/food-and-drink", "" for main)

        Returns:
            List of article URLs
        """
        url = f"{self.base_url}/travel{section}"
        response = self.fetch(url)
        if not response:
            return []

        soup = self.parse_html(response.text)
        urls = []

        for link in soup.find_all("a", href=True):
            href = link["href"]

            # Only collect /travel/ article links
            if "/travel/" not in href:
                continue

            # Skip section index pages and non-article patterns
            if href.rstrip("/") in ("/travel", "/travel/food-and-drink",
                                     "/travel/destinations", "/travel/stay",
                                     "/travel/news", "/travel/videos"):
                continue

            # Build absolute URL
            if not href.startswith("http"):
                full_url = f"https://www.cnn.com{href}"
            else:
                # Normalize edition.cnn.com to www.cnn.com
                full_url = href.replace("https://edition.cnn.com", "https://www.cnn.com")

            if self.is_valid_article_url(full_url) and full_url not in urls:
                urls.append(full_url)

        section_name = section or "home"
        self.logger.debug(f"Section [{section_name}] found {len(urls)} articles")
        return urls

    def scrape_all(self, limit: int = 0, since: str = None, exclude_urls: set = None) -> List[Article]:
        """
        Scrape articles from all CNN Travel section pages.

        Args:
            limit: Max articles to scrape, 0 for unlimited
            since: Only articles after this date (YYYY-MM-DD)
            exclude_urls: URLs to skip (already scraped)

        Returns:
            List of Article objects
        """
        self.logger.info(f"Starting {self.name} (category page mode)...")
        if since:
            self.logger.info(f"Date filter enabled: since={since}")

        exclude_urls = exclude_urls or set()
        all_urls = set()

        # Collect URLs from all sections
        for section in self.SECTIONS:
            section_name = section or "home"
            self.logger.info(f"Fetching section [{section_name}]...")
            section_urls = self._fetch_section_urls(section)

            # Filter out excluded URLs
            new_urls = [url for url in section_urls
                        if url not in exclude_urls and url not in all_urls]
            all_urls.update(new_urls)

            self.logger.info(
                f"Section [{section_name}]: {len(new_urls)} new articles (total: {len(all_urls)})"
            )

        self.logger.info(f"Total unique articles found: {len(all_urls)}")

        if not all_urls:
            return []

        # Apply limit
        urls_to_scrape = list(all_urls)
        if limit and len(urls_to_scrape) > limit:
            fetch_limit = limit * 2 if since else limit
            urls_to_scrape = urls_to_scrape[:fetch_limit]

        # Concurrent scraping
        max_workers = CONCURRENCY_CONFIG.get("max_workers", 5)
        all_articles = []
        skipped_by_date = 0

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_url = {
                executor.submit(self.scrape_article, url): url
                for url in urls_to_scrape
            }

            for future in as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    article = future.result()
                    if article:
                        # Date filter
                        if since and article.publish_date:
                            pub_date = normalize_date(article.publish_date)
                            if pub_date and pub_date < since:
                                skipped_by_date += 1
                                self.logger.debug(
                                    f"Date filter skipped: {article.title} ({pub_date})"
                                )
                                continue

                        all_articles.append(article)

                        if limit and len(all_articles) >= limit:
                            self.logger.info(f"Reached limit of {limit} articles")
                            break

                except Exception as e:
                    self.logger.error(f"Failed to scrape {url}: {e}")

        # Log summary
        log_lines = [
            f"Scraping completed: {self.name}",
            f"  Total requests: {self.stats['total_requests']}",
            f"  Successful: {self.stats['successful_requests']}",
            f"  Failed: {self.stats['failed_requests']}",
            f"  Articles: {len(all_articles)}",
        ]
        if since and skipped_by_date > 0:
            log_lines.append(f"  Skipped by date: {skipped_by_date}")
        self.logger.info("\n".join(log_lines))

        return all_articles

    def is_valid_article_url(self, url: str) -> bool:
        """Check if URL is a valid CNN Travel article"""
        if not url:
            return False

        url_lower = url.lower()

        # Must contain /travel/
        if "/travel/" not in url_lower:
            return False

        # Exclude section index pages
        section_pages = [
            "/travel/food-and-drink", "/travel/destinations",
            "/travel/stay", "/travel/news", "/travel/videos",
        ]
        path = url_lower.split("cnn.com")[-1].rstrip("/")
        if path in section_pages or path == "/travel":
            return False

        # Exclude non-article patterns
        exclude_patterns = [
            "/video/", "/gallery/", "/live-news/",
            "/tag/", "/category/", "/author/", "/page/",
            ".jpg", ".png", ".pdf", ".css", ".js",
            "/search", "/login", "/register",
        ]
        if any(p in url_lower for p in exclude_patterns):
            return False

        return True

    def _parse_json_ld(self, soup) -> dict:
        """Extract data from JSON-LD NewsArticle schema"""
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string)
                # CNN uses a list of JSON-LD objects
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and item.get("@type") == "NewsArticle":
                            return item
                elif isinstance(data, dict) and data.get("@type") == "NewsArticle":
                    return data
            except (json.JSONDecodeError, TypeError):
                continue
        return {}

    def extract_content(self, html: str) -> str:
        """Extract article body from .article__content"""
        soup = self.parse_html(html)

        content_div = soup.select_one(".article__content")
        if content_div:
            # Remove unwanted elements
            for tag in content_div.find_all([
                "script", "style", "nav", "aside", "iframe",
                "noscript", "button", "form", "footer"
            ]):
                tag.decompose()

            # Remove editor notes (newsletter signup prompts)
            for el in content_div.select(".editor-note-elevate"):
                el.decompose()

            # Remove ad slots and social elements
            for css_sel in [".ad", ".advertisement", ".social", ".share",
                            ".newsletter", ".related", ".outbrain"]:
                for el in content_div.select(css_sel):
                    el.decompose()

            content = content_div.decode_contents()
            if len(content) > 200:
                return content

        # Fallback: article tag
        article = soup.find("article")
        if article:
            for tag in article.find_all(["script", "style", "nav", "aside"]):
                tag.decompose()
            return article.decode_contents()

        return ""

    def parse_article(self, html: str, url: str) -> Optional[Article]:
        """Parse CNN Travel article page"""
        soup = self.parse_html(html)

        # Extract JSON-LD metadata
        json_ld = self._parse_json_ld(soup)

        # Title - from JSON-LD or fallback to HTML
        title = json_ld.get("headline", "")
        if not title:
            h1 = soup.find("h1")
            if h1:
                title = self.clean_text(h1.get_text())
        if not title:
            og_title = soup.select_one("meta[property='og:title']")
            if og_title:
                title = og_title.get("content", "").replace(" | CNN", "")
        if not title:
            return None

        # Clean title - remove " | CNN" suffix
        title = re.sub(r'\s*\|\s*CNN.*$', '', title).strip()

        # Content
        content = self.extract_content(html)

        # Author - from JSON-LD
        author = ""
        if json_ld.get("author"):
            authors = json_ld["author"]
            if isinstance(authors, list) and authors:
                author = authors[0].get("name", "")
            elif isinstance(authors, dict):
                author = authors.get("name", "")
        if not author:
            author_meta = soup.select_one("meta[name='author']")
            if author_meta:
                author = author_meta.get("content", "")

        # Publish date - from JSON-LD or meta
        publish_date = json_ld.get("datePublished", "")
        if not publish_date:
            date_meta = soup.select_one("meta[property='article:published_time']")
            if date_meta:
                publish_date = date_meta.get("content", "")

        # Category - from articleSection
        category = ""
        article_section = json_ld.get("articleSection", [])
        if isinstance(article_section, list) and article_section:
            category = article_section[0]
        elif isinstance(article_section, str):
            category = article_section

        # Tags - from meta keywords or article:tag
        tags = []
        for meta in soup.find_all("meta", attrs={"property": "article:tag"}):
            tag_val = meta.get("content", "").strip()
            if tag_val and tag_val not in tags:
                tags.append(tag_val)

        # Images - from JSON-LD or og:image
        images = []
        if json_ld.get("image"):
            img_data = json_ld["image"]
            if isinstance(img_data, list):
                for img in img_data:
                    if isinstance(img, dict):
                        img_url = img.get("contentUrl") or img.get("url")
                        if img_url:
                            images.append(img_url)
                    elif isinstance(img, str):
                        images.append(img)
            elif isinstance(img_data, dict):
                img_url = img_data.get("contentUrl") or img_data.get("url")
                if img_url:
                    images.append(img_url)

        og_image = soup.select_one("meta[property='og:image']")
        if og_image:
            img_url = og_image.get("content")
            if img_url and img_url not in images:
                images.append(img_url)

        return Article(
            url=url,
            title=title,
            content=content,
            author=author or "CNN Travel",
            publish_date=publish_date,
            category=category,
            tags=tags,
            images=images[:10],
            language="en",
            country="",   # International site, detect from content
            city="",
        )
