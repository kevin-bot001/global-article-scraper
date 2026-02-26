# -*- coding: utf-8 -*-
"""
TripCanvas Indonesia 爬虫 (Playwright)
https://indonesia.tripcanvas.co/
印尼旅游指南网站，有反爬机制需要 Playwright
"""
import json
from typing import List, Optional, Generator, Dict

from base_scraper import PlaywrightScraper, Article, normalize_date
from config import SITE_CONFIGS


class TripCanvasScraper(PlaywrightScraper):
    """
    TripCanvas Indonesia 爬虫

    需要 Playwright 因为有反爬机制和大量 JavaScript 渲染

    URL模式:
    - 列表页: /, /jakarta/, /bali/
    - 详情页: /[city]/[article-slug]/ 或 /[article-slug]/

    特性:
    - 从列表页 JSON-LD 提取文章日期，支持 --since 前置过滤
    """

    CONFIG_KEY = "tripcanvas"

    def __init__(self, use_proxy: bool = False, headless: bool = True):
        config = SITE_CONFIGS.get(self.CONFIG_KEY, {})

        super().__init__(
            name=config.get("name", "TripCanvas Indonesia"),
            base_url=config.get("base_url", "https://indonesia.tripcanvas.co"),
            delay=config.get("delay", 0.5),
            use_proxy=use_proxy,
            headless=headless,
            country=config.get("country", "Indonesia"),
            city=config.get("city", ""),
        )
        # 从 config 读取 categories 作为城市列表
        self.cities = config.get("categories", ["jakarta"])
        # URL 到发布日期的映射（从列表页 JSON-LD 提取）
        self._url_dates: Dict[str, str] = {}

    def get_article_list_urls(self) -> Generator[str, None, None]:
        """生成列表页URL"""
        # 首页
        # yield self.base_url

        # 城市页面
        for city in self.cities:
            yield f"{self.base_url}/{city}/"

    def is_valid_article_url(self, url: str) -> bool:
        """检查是否为有效的文章URL"""
        if not url or "indonesia.tripcanvas.co" not in url:
            return False

        # 排除列表页、搜索等
        exclude_patterns = [
            "/search", "/author/", "/tag/", "/category/",
            "/page/", "/contact", "/about", "/privacy",
            "/advertise", "/terms", "/write-article", "/careers",
        ]
        url_lower = url.lower()
        if any(pattern in url_lower for pattern in exclude_patterns):
            return False

        # TripCanvas 文章URL通常是 /[city]/[slug]/ 或 /[slug]/
        from urllib.parse import urlparse
        parsed = urlparse(url)
        path = parsed.path.strip("/")

        if not path:
            return False

        parts = path.split("/")

        # 单级路径都是城市/区域主页，不是文章
        # 如 /java/, /bali/, /lombok/, /jakarta/ 等
        if len(parts) == 1:
            return False

        # 文章URL必须有2级以上路径，如 /java/things-to-do-in-xxx/
        # 排除分类列表页 - 这些URL模式是分类而非文章
        category_slugs = [
            "hotels-villas-bali", "hotels-villas", "restaurants-cafes-bars",
            "restaurants-cafes-bars-bali", "attractions-activities",
            "attractions-activities-bali", "travel-guide-tips",
            "travel-guide-tips-bali", "itineraries", "area-guides",
            "hotel-experience-reviews", "hotel-reviews-experience",
            "best-of-indonesia", "responsible-travel", "health-wellness",
        ]
        if len(parts) >= 2:
            slug = parts[-1]
            if slug in category_slugs:
                return False

        # 至少2级路径才可能是文章
        return len(parts) >= 2

    def parse_article_list(self, html: str, list_url: str) -> List[str]:
        """
        解析文章列表页

        从 JSON-LD 结构化数据中提取文章 URL 和发布日期，
        缓存日期用于 --since 前置过滤
        """
        soup = self.parse_html(html)
        article_urls = []

        # 1. 从 JSON-LD 提取文章 URL 和日期（CollectionPage -> hasPart）
        for script in soup.select('script[type="application/ld+json"]'):
            try:
                data = json.loads(script.string or "")
                items = data if isinstance(data, list) else [data]

                for item in items:
                    if item.get("@type") == "CollectionPage" and item.get("hasPart"):
                        for part in item["hasPart"]:
                            if part.get("@type") == "Article" and part.get("url"):
                                url = part["url"]
                                date_published = part.get("datePublished", "")
                                if self.is_valid_article_url(url):
                                    if url not in article_urls:
                                        article_urls.append(url)
                                    # 缓存日期（ISO 格式如 2021-01-18T14:58:37+00:00）
                                    if date_published:
                                        normalized = normalize_date(date_published)
                                        if normalized:
                                            self._url_dates[url] = normalized
            except (json.JSONDecodeError, TypeError, KeyError):
                continue

        if article_urls:
            self.logger.info(f"从 JSON-LD 提取到 {len(article_urls)} 篇文章（含日期）")

        # 2. 从 HTML 链接补充提取（JSON-LD 可能不完整）
        selectors = [
            "a[href*='indonesia.tripcanvas.co/']",
            ".post-card a[href]",
            ".article-card a[href]",
            "article a[href]",
            "h2 a[href]",
            "h3 a[href]",
            ".card a[href]",
            ".entry-title a[href]",
        ]

        html_count = 0
        for selector in selectors:
            for link in soup.select(selector):
                href = link.get("href")
                if href:
                    # 处理相对URL
                    if href.startswith("/"):
                        full_url = f"https://indonesia.tripcanvas.co{href}"
                    elif not href.startswith("http"):
                        full_url = f"https://indonesia.tripcanvas.co/{href}"
                    else:
                        full_url = href

                    if self.is_valid_article_url(full_url) and full_url not in article_urls:
                        article_urls.append(full_url)
                        html_count += 1

        if html_count > 0:
            self.logger.info(f"从 HTML 补充提取 {html_count} 篇文章（无预知日期）")

        return article_urls

    def get_url_date(self, url: str) -> Optional[str]:
        """获取 URL 对应的发布日期（从列表页 JSON-LD 缓存）"""
        return self._url_dates.get(url)

    def extract_content(self, html: str) -> str:
        """
        从原始 HTML 提取正文内容

        TripCanvas 用 .postcontent.content 作为主内容区域
        """
        soup = self.parse_html(html)

        content_selectors = [
            ".postcontent.content",  # TripCanvas主内容
            ".postcontent",
            ".content",
            ".entry-content",
            ".post-content",
            ".article-content",
            "article .content",
            "main article",
        ]
        for selector in content_selectors:
            content_el = soup.select_one(selector)
            if content_el:
                # 移除不需要的标签元素
                for tag in content_el.find_all([
                    "script", "style", "nav", "aside", "iframe", "noscript"
                ]):
                    tag.decompose()
                # 移除不需要的 class 元素
                for css_selector in [
                    ".share-container", ".share", ".ad", ".advertisement",
                    ".related", ".related-posts", ".newsletter", ".optin",
                    ".social-share", ".author-box", ".author-single",
                    ".brick-thumb-link", ".tableofcontent"
                ]:
                    for el in content_el.select(css_selector):
                        el.decompose()
                content = content_el.decode_contents()
                if len(content) > 100:
                    return content
        return ""

    def parse_article(self, html: str, url: str) -> Optional[Article]:
        """解析文章详情页"""
        soup = self.parse_html(html)

        # 标题
        title = ""
        title_selectors = [
            "h1.entry-title",
            "h1.post-title",
            "h1",
            ".article-title",
            ".headline",
        ]
        for selector in title_selectors:
            title_el = soup.select_one(selector)
            if title_el:
                title = self.clean_text(title_el.get_text())
                if title:
                    break

        if not title:
            return None

        # 内容 - 调用 extract_content 方法
        content = self.extract_content(html)

        # 作者 - TripCanvas用链接到/author/页面
        author = ""
        author_selectors = [
            "a[href*='/author/']",  # TripCanvas作者链接
            ".author-name",
            ".byline a",
            ".author a",
            ".entry-author",
        ]
        for selector in author_selectors:
            author_el = soup.select_one(selector)
            if author_el:
                author = self.clean_text(author_el.get_text())
                if author:
                    break

        # 发布日期
        publish_date = ""
        date_selectors = [
            "time[datetime]",
            ".entry-date",
            ".post-date",
            ".published",
            "meta[property='article:published_time']",
        ]
        for selector in date_selectors:
            date_el = soup.select_one(selector)
            if date_el:
                publish_date = date_el.get("datetime") or date_el.get("content") or self.clean_text(date_el.get_text())
                if publish_date:
                    break

        # 分类 - 从URL或页面提取
        category = ""
        from urllib.parse import urlparse
        parsed = urlparse(url)
        path = parsed.path.strip("/")
        parts = path.split("/")

        # 如果第一部分是城市名，用作分类
        if parts and parts[0] in self.cities:
            category = parts[0].title()
        else:
            # 尝试从页面提取
            cat_selectors = [".category a", ".cat-links a", ".entry-category"]
            for selector in cat_selectors:
                cat_el = soup.select_one(selector)
                if cat_el:
                    category = self.clean_text(cat_el.get_text())
                    break

        # 标签
        tags = []
        tag_selectors = [".tag-links a", ".tags a", ".entry-tags a"]
        for selector in tag_selectors:
            for tag_el in soup.select(selector):
                tag = self.clean_text(tag_el.get_text())
                if tag and tag not in tags:
                    tags.append(tag)

        # 图片
        images = []
        # 特色图
        featured = soup.select_one(".featured-image img, .post-thumbnail img, .hero img")
        if featured:
            src = featured.get("src") or featured.get("data-src")
            if src:
                images.append(self.absolute_url(src))

        # 内容中的图片
        for img in soup.select(".postcontent img, .content img, .entry-content img, .post-content img, article img"):
            src = img.get("src") or img.get("data-src") or img.get("data-lazy-src")
            if src and not src.endswith(".svg"):
                full_src = self.absolute_url(src)
                if full_src not in images:
                    images.append(full_src)

        return Article(
            url=url,
            title=title,
            country=self.country,
            content=content,
            author=author,
            publish_date=publish_date,
            category=category,
            tags=tags,
            images=images[:10],
            language="en",  # TripCanvas 主要是英文
        )
