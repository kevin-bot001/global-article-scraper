# -*- coding: utf-8 -*-
"""
Lonely Planet Scraper (Category Page Mode)
https://www.lonelyplanet.com/articles

Global travel guide website - no working sitemap, use category pages to fetch articles.

Features:
- 13 article categories (adventure, food-and-drink, beaches, etc.)
- Continent filter support (default: asia)
- JSON-LD NewsArticle metadata
- Content in div.content-block
- curl_cffi bypasses 403 Cloudflare protection

Usage:
    scraper = LonelyPlanetScraper(continent="asia")  # Default
    scraper = LonelyPlanetScraper(continent="europe")  # Other continents
    scraper = LonelyPlanetScraper(continent=None)  # All continents (no filter)
"""
import json
from typing import List, Optional, Generator
from concurrent.futures import ThreadPoolExecutor, as_completed

from base_scraper import BaseScraper, Article, normalize_date
from config import SITE_CONFIGS, CONCURRENCY_CONFIG


class LonelyPlanetScraper(BaseScraper):
    """
    Lonely Planet Scraper

    Fetches articles from category pages since sitemap is broken.
    Uses JSON-LD for metadata extraction.
    """

    CONFIG_KEY = "lonely_planet"

    # All available categories
    CATEGORIES = [
        "adventure",
        "adventure-travel",
        "art-and-culture",
        "beaches",
        "budget-travel",
        "family-travel",
        "festivals-and-events",
        "food-and-drink",
        "road-trips",
        "romance",
        "sustainable-travel",
        "travel-advice",
        "wildlife-and-nature",
    ]

    # Available continent filters
    CONTINENTS = [
        "europe", "asia", "north-america", "south-america",
        "pacific", "africa", "middle-east", "caribbean",
        "central-america", "antarctica",
    ]

    def __init__(self, use_proxy: bool = False, continent: str = None):
        config = SITE_CONFIGS.get(self.CONFIG_KEY, {})

        # Continent filter (default to asia)
        self.continent = continent or config.get("continent", "asia")

        super().__init__(
            name=config.get("name", "Lonely Planet") + f" ({self.continent.title()})",
            base_url=config.get("base_url", "https://www.lonelyplanet.com"),
            delay=config.get("delay", 0.5),
            use_proxy=use_proxy,
            country=config.get("country", ""),  # Global site, detect from content
            city=config.get("city", ""),
        )

        # Get categories from config or use all
        self.categories = config.get("categories", []) or self.CATEGORIES

    def get_article_list_urls(self) -> Generator[str, None, None]:
        """Signal category mode (not used in scrape_all)"""
        yield "category://"

    def parse_article_list(self, html: str, list_url: str) -> List[str]:
        """Not used in category mode"""
        return []

    def fetch_urls_from_sitemap(self) -> List[tuple]:
        """Not using sitemap mode"""
        return []

    def _fetch_category_urls(self, category: str) -> List[str]:
        """
        Fetch article URLs from a single category page.
        Only fetches page 1 since pagination doesn't work properly.
        """
        # Add continent filter if set
        url = f"{self.base_url}/articles/category/{category}"
        if self.continent:
            url += f"?slug={self.continent}"

        response = self.fetch(url)
        if not response:
            return []

        soup = self.parse_html(response.text)
        urls = []

        # Find article links - /articles/{slug} pattern
        for link in soup.select("a[href*='/articles/']"):
            href = link.get("href", "")
            if href and self.is_valid_article_url(href):
                full_url = self.absolute_url(href)
                if full_url not in urls:
                    urls.append(full_url)

        self.logger.debug(f"Category [{category}] found {len(urls)} articles")
        return urls

    def scrape_all(self, limit: int = 0, since: str = None, exclude_urls: set = None) -> List[Article]:
        """
        Scrape articles from all category pages.

        Args:
            limit: Max articles to scrape, 0 for unlimited
            since: Only articles after this date (YYYY-MM-DD), based on publish_date
            exclude_urls: URLs to skip (already scraped)

        Returns:
            List of Article objects
        """
        self.logger.info(f"Starting {self.name} (category page mode)...")
        if since:
            self.logger.info(f"Date filter enabled: since={since}")

        exclude_urls = exclude_urls or set()
        all_urls = set()

        # Collect URLs from all categories
        for category in self.categories:
            self.logger.info(f"Fetching category [{category}]...")
            category_urls = self._fetch_category_urls(category)

            # Filter out excluded URLs
            new_urls = [url for url in category_urls if url not in exclude_urls and url not in all_urls]
            all_urls.update(new_urls)

            self.logger.info(f"Category [{category}]: {len(new_urls)} new articles (total: {len(all_urls)})")

        self.logger.info(f"Total unique articles found: {len(all_urls)}")

        if not all_urls:
            return []

        # Apply limit if set
        urls_to_scrape = list(all_urls)
        if limit and len(urls_to_scrape) > limit:
            # Over-fetch to account for date filtering
            fetch_limit = limit * 2 if since else limit
            urls_to_scrape = urls_to_scrape[:fetch_limit]

        # Concurrent scraping
        max_workers = CONCURRENCY_CONFIG.get("max_workers", 5)
        all_articles = []
        skipped_by_date = 0

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_url = {executor.submit(self.scrape_article, url): url for url in urls_to_scrape}

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
                                self.logger.debug(f"Date filter skipped: {article.title} ({pub_date})")
                                continue

                        all_articles.append(article)

                        # Check limit
                        if limit and len(all_articles) >= limit:
                            self.logger.info(f"Reached limit of {limit} articles")
                            break

                except Exception as e:
                    self.logger.error(f"Failed to scrape {url}: {e}")

        # Build log message
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
        """Check if URL is a valid article page"""
        if not url:
            return False

        url_lower = url.lower()

        # Must be from main domain (not support/shop subdomains)
        if "support.lonelyplanet.com" in url_lower or "shop.lonelyplanet.com" in url_lower:
            return False

        # Must contain /articles/ but not /category/
        if "/articles/" not in url_lower:
            return False
        if "/category/" in url_lower:
            return False

        # Exclude non-article patterns
        exclude_patterns = [
            "/destinations/", "/search", "/author/",
            ".jpg", ".png", ".pdf", ".css", ".js",
            "/hc/", "/help/",  # Help center links
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

        # Lonely Planet specific selector
        content_div = soup.find("div", class_=lambda c: c and "content-block" in c)
        if content_div:
            # Remove unwanted elements
            for tag in content_div.find_all(["script", "style", "nav", "aside", "iframe", "noscript"]):
                tag.decompose()
            for css_sel in [".share", ".social", ".ad", ".related", ".newsletter"]:
                for el in content_div.select(css_sel):
                    el.decompose()

            content = content_div.decode_contents()
            if len(content) > 200:
                return content

        # Fallback to article tag
        article = soup.find("article")
        if article:
            for tag in article.find_all(["script", "style", "nav", "aside"]):
                tag.decompose()
            return article.decode_contents()

        return ""

    def parse_article(self, html: str, url: str) -> Optional[Article]:
        """Parse article page and extract metadata"""
        soup = self.parse_html(html)

        # Try JSON-LD first (most reliable)
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

        # Content
        content = self.extract_content(html)

        # Author - from JSON-LD or fallback
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

        # Publish date from JSON-LD
        publish_date = json_ld.get("datePublished") or ""
        if not publish_date:
            date_meta = soup.select_one("meta[property='article:published_time']")
            if date_meta:
                publish_date = date_meta.get("content", "")

        # Category - try to extract from URL or breadcrumb
        category = ""
        # Check if URL has category hint
        if "/articles/best-" in url:
            category = "Best Of"
        elif "/articles/how-" in url or "/articles/getting-" in url:
            category = "Travel Tips"

        # Tags - not readily available, leave empty
        tags = []

        # Images
        images = []
        # From JSON-LD
        if json_ld.get("image"):
            img_data = json_ld["image"]
            if isinstance(img_data, dict):
                img_url = img_data.get("url")
                if img_url:
                    images.append(img_url)
            elif isinstance(img_data, str):
                images.append(img_data)

        # From og:image
        og_image = soup.select_one("meta[property='og:image']")
        if og_image:
            img_url = og_image.get("content")
            if img_url and img_url not in images:
                images.append(img_url)

        # Content images
        if content:
            content_soup = self.parse_html(content)
            for img in content_soup.find_all("img"):
                src = img.get("src") or img.get("data-src")
                if src and not src.endswith(".svg") and src not in images:
                    images.append(self.absolute_url(src))

        # Use continent as country since it's a global site filtered by region
        country = self.continent.title() if self.continent else ""

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
            country=country,  # Use continent filter as region indicator
            city="",
        )
