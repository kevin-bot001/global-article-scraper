# -*- coding: utf-8 -*-
"""
Lonely Planet Scraper (Pagination Mode)
https://www.lonelyplanet.com/articles

Global travel guide website covering destinations, food, adventure and culture worldwide.

Features:
- Pagination mode: /articles/page/{N}?slug={continent}
- Continent filter via ?slug= param (asia, europe, etc.)
- Default: asia (~4 pages). Without filter: 225+ pages
- JSON-LD NewsArticle metadata (headline, datePublished, author, image)
- Content in div.content-block
- curl_cffi bypasses CloudFront protection
- No sitemap available (returns 404)
- robots.txt allows /articles/page/ but disallows /articles/category/

Usage:
    scraper = LonelyPlanetScraper()                      # Default: asia
    scraper = LonelyPlanetScraper(continent="europe")    # Europe
    scraper = LonelyPlanetScraper(continent=None)        # All continents
"""
import json
from typing import List, Optional, Generator
from concurrent.futures import ThreadPoolExecutor, as_completed

from base_scraper import BaseScraper, Article, normalize_date
from config import SITE_CONFIGS, CONCURRENCY_CONFIG


class LonelyPlanetScraper(BaseScraper):
    """
    Lonely Planet Scraper

    Fetches articles from /articles/page/{N} pagination pages.
    Supports continent filter via ?slug= parameter.
    Uses JSON-LD NewsArticle for metadata extraction.
    """

    CONFIG_KEY = "lonely_planet"

    # Available continent slugs
    CONTINENTS = [
        "europe", "asia", "north-america", "south-america",
        "pacific", "africa", "middle-east", "caribbean",
        "central-america", "antarctica",
    ]

    def __init__(self, use_proxy: bool = False, continent: str = None):
        config = SITE_CONFIGS.get(self.CONFIG_KEY, {})

        # Continent filter: explicit param > config > default "asia"
        if continent is not None:
            self.continent = continent
        else:
            self.continent = config.get("continent", "asia")

        # Build display name with continent
        base_name = config.get("name", "Lonely Planet")
        display_name = f"{base_name} ({self.continent.title()})" if self.continent else base_name

        super().__init__(
            name=display_name,
            base_url=config.get("base_url", "https://www.lonelyplanet.com"),
            delay=config.get("delay", 1.0),
            use_proxy=use_proxy,
            country=config.get("country", ""),
            city=config.get("city", ""),
        )

        self.max_pages = config.get("max_pages", 225)

    def get_article_list_urls(self) -> Generator[str, None, None]:
        """Signal pagination mode (not used in scrape_all)"""
        yield "pagination://"

    def parse_article_list(self, html: str, list_url: str) -> List[str]:
        """Not used in pagination mode"""
        return []

    def fetch_urls_from_sitemap(self) -> List[tuple]:
        """Not using sitemap mode"""
        return []

    def _fetch_page_urls(self, page_num: int) -> List[str]:
        """
        Fetch article URLs from a single pagination page.

        Args:
            page_num: Page number (1-based)

        Returns:
            List of unique article URLs found on the page
        """
        if page_num == 1:
            url = f"{self.base_url}/articles"
        else:
            url = f"{self.base_url}/articles/page/{page_num}"

        # Append continent filter if set
        if self.continent:
            url += f"?slug={self.continent}"

        response = self.fetch(url)
        if not response:
            return []

        soup = self.parse_html(response.text)
        urls = []

        for link in soup.find_all("a", href=True):
            href = link["href"]

            if "/articles/" not in href:
                continue

            full_url = self.absolute_url(href)

            if self.is_valid_article_url(full_url) and full_url not in urls:
                urls.append(full_url)

        self.logger.debug(f"Page {page_num} found {len(urls)} articles")
        return urls

    def scrape_all(self, limit: int = 0, since: str = None, exclude_urls: set = None) -> List[Article]:
        """
        Scrape articles from pagination pages.

        Iterates through /articles/page/{N} pages to collect article URLs,
        then scrapes each article page concurrently.

        Args:
            limit: Max articles to scrape, 0 for unlimited
            since: Only articles after this date (YYYY-MM-DD)
            exclude_urls: URLs to skip (already scraped)

        Returns:
            List of Article objects
        """
        self.logger.info(f"Starting {self.name} (pagination mode)...")
        if since:
            self.logger.info(f"Date filter enabled: since={since}")

        exclude_urls = exclude_urls or set()
        all_urls = set()

        # Collect URLs from pagination pages
        for page_num in range(1, self.max_pages + 1):
            self.logger.info(f"Fetching page {page_num}/{self.max_pages}...")
            page_urls = self._fetch_page_urls(page_num)

            if not page_urls:
                self.logger.info(f"Page {page_num} returned 0 articles, stopping pagination")
                break

            # Filter out excluded URLs
            new_urls = [url for url in page_urls if url not in exclude_urls and url not in all_urls]
            all_urls.update(new_urls)

            self.logger.info(f"Page {page_num}: {len(new_urls)} new articles (total: {len(all_urls)})")

            # Early stop if we have enough URLs (with buffer for date filtering)
            if limit:
                target = limit * 3 if since else limit
                if len(all_urls) >= target:
                    self.logger.info(f"Collected enough URLs ({len(all_urls)}), stopping pagination")
                    break

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
        """Check if URL is a valid Lonely Planet article page"""
        if not url:
            return False

        url_lower = url.lower()

        # Must be from main domain
        if "support.lonelyplanet.com" in url_lower or "shop.lonelyplanet.com" in url_lower:
            return False

        # Must contain /articles/ path
        if "/articles/" not in url_lower:
            return False

        # Exclude non-article patterns
        exclude_patterns = [
            "/articles/page/",        # Pagination pages
            "/articles/category/",    # Category index pages
            "/destinations/",
            "/search", "/author/",
            ".jpg", ".png", ".pdf", ".css", ".js",
            "/hc/", "/help/",
        ]
        if any(p in url_lower for p in exclude_patterns):
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
        """Extract article body from content-block div"""
        soup = self.parse_html(html)

        # Primary selector: div.content-block
        content_div = soup.find("div", class_=lambda c: c and "content-block" in c)
        if content_div:
            # Remove unwanted elements
            for tag in content_div.find_all([
                "script", "style", "nav", "aside", "iframe",
                "noscript", "button", "form", "footer"
            ]):
                tag.decompose()

            for css_sel in [".share", ".social", ".ad", ".related",
                            ".newsletter", ".outbrain"]:
                for el in content_div.select(css_sel):
                    el.decompose()

            content = content_div.decode_contents()
            if len(content) > 200:
                return content

        # Fallback: main tag
        main = soup.find("main")
        if main:
            for tag in main.find_all(["script", "style", "nav", "aside"]):
                tag.decompose()
            content = main.decode_contents()
            if len(content) > 200:
                return content

        return ""

    def parse_article(self, html: str, url: str) -> Optional[Article]:
        """Parse Lonely Planet article page and extract metadata"""
        soup = self.parse_html(html)

        # JSON-LD is the primary metadata source
        json_ld = self._parse_json_ld(soup)

        # Title
        title = json_ld.get("headline") or json_ld.get("name") or ""
        if not title:
            h1 = soup.find("h1")
            if h1:
                title = self.clean_text(h1.get_text())
        if not title:
            og_title = soup.select_one("meta[property='og:title']")
            if og_title:
                title = og_title.get("content", "")

        if not title:
            return None

        # Skip template/redirect pages (old URLs redirect to LP homepage)
        if title.lower() in ("we know where to go", "lonely planet"):
            self.logger.debug(f"Skipping template page: {title} ({url})")
            return None

        # Content
        content = self.extract_content(html)

        # Author
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

        # Publish date
        publish_date = json_ld.get("datePublished", "")
        if not publish_date:
            date_meta = soup.select_one("meta[property='article:published_time']")
            if date_meta:
                publish_date = date_meta.get("content", "")

        # Category - infer from URL slug pattern
        category = ""
        if "/articles/best-" in url:
            category = "Best Of"
        elif "/articles/how-" in url or "/articles/getting-" in url:
            category = "Travel Tips"
        elif "/articles/top-" in url:
            category = "Best Of"
        elif "/articles/where-" in url:
            category = "Guides"

        # Tags - not available in JSON-LD
        tags = []

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

        og_image = soup.select_one("meta[property='og:image']")
        if og_image:
            img_url = og_image.get("content")
            if img_url and img_url not in images:
                images.append(img_url)

        return Article(
            url=url,
            title=title,
            content=content,
            author=author or "Lonely Planet",
            publish_date=publish_date,
            category=category,
            tags=tags,
            images=images[:10],
            language="en",
            country="",   # Global site, auto-detect from content
            city="",
        )
