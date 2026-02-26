# -*- coding: utf-8 -*-
"""
Guide to the Philippines Scraper (Sitemap Mode)
https://guidetothephilippines.ph

Philippine travel and tourism platform with detailed travel guides, dining, activities,
and destination articles. Next.js SSR app with JSON-LD structured data.

Sitemap Index: /sitemap.xml (12 sitemaps: sitemap0.xml - sitemap11.xml)
Key Sitemaps:
- sitemap0.xml  (~84 articles - high priority guides)
- sitemap1.xml  (~148 articles)
- sitemap2.xml  (~158 articles)
- sitemap3.xml  (~75 articles)
- sitemap4-11   (non-article pages: tours, hotels, etc.)

Content Structure:
- JSON-LD Article type (headline, datePublished, dateModified, author)
- Content in <article> tag with articleWidgetHTML divs
- SSR-rendered <p> tags with full content
- Sitemap has lastmod and image:image with geo_location

URL Pattern: /articles/{category}/{slug}
Categories: ultimate-guides, what-to-experience, food-and-dining,
            islands-and-beaches, history-culture, adventure-and-outdoors, etc.
"""
import json
import re
from typing import List, Optional, Generator, Tuple
from xml.etree import ElementTree

from base_scraper import BaseScraper, Article
from config import SITE_CONFIGS


class GuideToPhScraper(BaseScraper):
    """
    Guide to the Philippines Scraper (Sitemap Mode)

    Next.js SSR with JSON-LD Article data.
    ~465 English articles about Philippine travel and dining.

    URL Pattern: /articles/{category}/{slug}
    """

    CONFIG_KEY = "guide_to_ph"

    # Only sitemaps 0-3 contain article URLs
    TARGET_SITEMAPS = [
        "sitemap0.xml",
        "sitemap1.xml",
        "sitemap2.xml",
        "sitemap3.xml",
    ]

    # Category slug -> display name mapping
    CATEGORY_MAP = {
        "ultimate-guides": "Travel Guides",
        "what-to-experience": "Experiences",
        "food-and-dining": "Food & Dining",
        "islands-and-beaches": "Islands & Beaches",
        "history-culture": "History & Culture",
        "adventure-and-outdoors": "Adventure & Outdoors",
        "city-guide": "City Guide",
        "nature": "Nature",
        "nightlife-and-events": "Nightlife & Events",
        "wellness-and-relaxation": "Wellness & Relaxation",
    }

    def __init__(self, use_proxy: bool = False):
        config = SITE_CONFIGS.get(self.CONFIG_KEY, {})
        super().__init__(
            name=config.get("name", "Guide to the Philippines"),
            base_url=config.get("base_url", "https://guidetothephilippines.ph"),
            delay=config.get("delay", 0.8),
            use_proxy=use_proxy,
            country=config.get("country", "Philippines"),
            city=config.get("city", ""),
        )
        self._article_urls_cache = None

    def get_article_list_urls(self) -> Generator[str, None, None]:
        """Generate list page URLs - use special marker for sitemap mode"""
        yield "sitemap://guide_to_ph"

    def parse_article_list(self, html: str, list_url: str) -> List[str]:
        """Parse article list page - not used in sitemap mode"""
        return []

    def fetch_urls_from_sitemap(self) -> List[Tuple[str, str]]:
        """
        Fetch article URLs from multiple sitemaps

        Returns:
            [(url, lastmod), ...] sorted by lastmod descending
        """
        if self._article_urls_cache is not None:
            return self._article_urls_cache

        url_with_dates = []
        ns = {
            "sm": "http://www.sitemaps.org/schemas/sitemap/0.9",
            "image": "http://www.google.com/schemas/sitemap-image/1.1",
        }

        for sitemap_name in self.TARGET_SITEMAPS:
            sitemap_url = f"{self.base_url}/{sitemap_name}"
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
                            # Normalize ISO datetime to date-only for sorting
                            if mod_date and "T" in mod_date:
                                mod_date = mod_date.split("T")[0]
                            url_with_dates.append((url, mod_date))
                            count += 1

                self.logger.info(f"Sitemap {sitemap_name}: {count} articles")

            except ElementTree.ParseError as e:
                self.logger.error(f"Failed to parse sitemap: {sitemap_name} - {e}")

        # Sort by lastmod descending
        url_with_dates.sort(key=lambda x: x[1] if x[1] else "", reverse=True)
        self._article_urls_cache = url_with_dates

        self.logger.info(f"Total articles from sitemaps: {len(url_with_dates)}")
        return url_with_dates

    def is_valid_article_url(self, url: str) -> bool:
        """Check if URL is a valid article URL"""
        if not url or "guidetothephilippines.ph" not in url:
            return False

        url_lower = url.lower()

        # Only English articles (no /zh/ or /ko/ prefix)
        if "/zh/" in url_lower or "/ko/" in url_lower:
            return False

        # Must be an /articles/ path
        if "/articles/" not in url_lower:
            return False

        # Must have category and slug: /articles/{category}/{slug}
        path = url_lower.replace("https://guidetothephilippines.ph", "").strip("/")
        segments = [s for s in path.split("/") if s]
        if len(segments) < 3:
            # /articles/ alone or /articles/{category}/ without slug
            return False

        # Exclude non-article paths
        exclude_patterns = [
            "/search", "/login", "/cart", "/travel-plan/",
            "/messages/", "/voucher/", "/res/",
            ".jpg", ".png", ".pdf",
        ]
        if any(p in url_lower for p in exclude_patterns):
            return False

        return True

    def _extract_json_ld(self, soup) -> dict:
        """Extract Article data from JSON-LD"""
        result = {}

        for script in soup.find_all("script", type="application/ld+json"):
            if not script.string:
                continue
            try:
                data = json.loads(script.string)
            except (json.JSONDecodeError, TypeError):
                continue

            if not isinstance(data, dict):
                continue

            if data.get("@type") not in ("Article", "BlogPosting", "NewsArticle"):
                continue

            if data.get("headline"):
                result["title"] = data["headline"]

            if data.get("datePublished"):
                result["date"] = data["datePublished"]

            if data.get("dateModified"):
                result["date_modified"] = data["dateModified"]

            author = data.get("author", {})
            if isinstance(author, dict) and author.get("name"):
                result["author"] = author["name"]
            elif isinstance(author, list) and author:
                names = [a.get("name", "") for a in author if isinstance(a, dict)]
                result["author"] = ", ".join(n for n in names if n)

            break

        return result

    def _category_from_url(self, url: str) -> str:
        """Extract and prettify category from URL path"""
        # /articles/{category}/{slug}
        match = re.search(r"/articles/([^/]+)/", url)
        if match:
            slug = match.group(1)
            return self.CATEGORY_MAP.get(slug, slug.replace("-", " ").title())
        return ""

    def extract_content(self, html: str) -> str:
        """
        Extract main content from HTML.

        Content is SSR-rendered in <article> tag.
        Widget divs with class containing 'articleWidgetHTML' hold the text blocks.
        """
        soup = self.parse_html(html)

        article = soup.find("article")
        if not article:
            return ""

        # Remove non-content elements
        for tag in article.find_all([
            "script", "style", "nav", "aside", "iframe",
            "button", "form", "noscript", "footer", "svg",
        ]):
            tag.decompose()

        # Remove ad/promo/booking widgets
        for css_sel in [
            "[class*='BookingWidget']",
            "[class*='RelatedTrips']",
            "[class*='commentsAnchor']",
            "[class*='ArticleCtaWidget']",
            "[class*='ShareWidget']",
            "[class*='BreadCrumb']",
        ]:
            for el in article.select(css_sel):
                el.decompose()

        # Find articleWidgetHTML divs (the main content blocks)
        widget_divs = article.find_all("div", class_=re.compile(r"articleWidgetHTML"))
        if widget_divs:
            content_parts = []
            for div in widget_divs:
                html_content = div.decode_contents()
                # Clean up empty tags and excessive whitespace
                html_content = re.sub(r'<!--.*?-->', '', html_content, flags=re.DOTALL)
                html_content = html_content.strip()
                if html_content:
                    content_parts.append(html_content)
            content = "\n".join(content_parts)
            if len(content) > 200:
                return content

        # Fallback: get all content from article tag
        content = article.decode_contents()
        content = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)
        content = content.strip()
        if len(content) > 200:
            return content

        return ""

    def parse_article(self, html: str, url: str) -> Optional[Article]:
        """Parse article detail page using JSON-LD and DOM selectors"""
        soup = self.parse_html(html)

        # JSON-LD data
        json_ld = self._extract_json_ld(soup)

        # Title - prefer JSON-LD, fallback to DOM
        title = json_ld.get("title", "")
        if not title:
            h1 = soup.select_one("h1")
            if h1:
                title = self.clean_text(h1.get_text())
        if not title:
            og_title = soup.select_one("meta[property='og:title']")
            if og_title:
                title = og_title.get("content", "")
                # Remove site name suffix
                for suffix in [" | Guide to the Philippines", " - Guide to the Philippines"]:
                    if title.endswith(suffix):
                        title = title[:-len(suffix)]

        if not title:
            return None

        # Content
        content = self.extract_content(html)

        # Author
        author = json_ld.get("author", "")

        # Publish date
        publish_date = json_ld.get("date", "")

        # Category from URL
        category = self._category_from_url(url)

        # Tags - try to extract from breadcrumb or other sources
        tags = []

        # Images
        images = []
        og_image = soup.select_one("meta[property='og:image']")
        if og_image:
            img_url = og_image.get("content", "")
            if img_url:
                images.append(img_url)

        # Article images
        article_el = soup.find("article")
        if article_el:
            for img in article_el.find_all("img"):
                src = img.get("src") or img.get("data-src")
                if src and not src.endswith(".svg") and "icon" not in src.lower():
                    full_src = self.absolute_url(src)
                    if full_src not in images:
                        images.append(full_src)

        # City - try to infer from URL slug or title
        city = self._infer_city(url, title)

        return Article(
            url=url,
            title=title,
            content=content,
            author=author or "Guide to the Philippines",
            publish_date=publish_date,
            category=category,
            tags=tags,
            images=images[:10],
            language="en",
            country="Philippines",
            city=city,
        )

    def _infer_city(self, url: str, title: str) -> str:
        """Infer city from URL slug or article title"""
        text = f"{url} {title}".lower()

        city_keywords = {
            "manila": "Manila",
            "makati": "Makati",
            "bgc": "BGC",
            "cebu": "Cebu",
            "boracay": "Boracay",
            "palawan": "Palawan",
            "siargao": "Siargao",
            "baguio": "Baguio",
            "davao": "Davao",
            "bohol": "Bohol",
            "iloilo": "Iloilo",
            "tagaytay": "Tagaytay",
            "batangas": "Batangas",
            "zambales": "Zambales",
            "la union": "La Union",
            "subic": "Subic",
            "dumaguete": "Dumaguete",
            "bacolod": "Bacolod",
            "vigan": "Vigan",
            "sagada": "Sagada",
            "coron": "Coron",
            "el nido": "El Nido",
            "puerto princesa": "Puerto Princesa",
            "camiguin": "Camiguin",
        }

        for keyword, city_name in city_keywords.items():
            if keyword in text:
                return city_name

        return ""
