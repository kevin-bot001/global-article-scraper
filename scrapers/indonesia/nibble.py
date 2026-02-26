# -*- coding: utf-8 -*-
"""
Nibble.id 爬虫 (分类分页模式)
https://www.nibble.id/
印尼美食点评平台，餐厅指南和美食文章
"""
import re
import json
from typing import List, Optional, Generator
from concurrent.futures import ThreadPoolExecutor, as_completed

from base_scraper import BaseScraper, Article, normalize_date
from config import SITE_CONFIGS, CONCURRENCY_CONFIG


class NibbleScraper(BaseScraper):
    """
    Nibble.id 爬虫

    从分类分页获取文章（按时间倒序）
    无 sitemap，使用分类页面分页获取

    特性:
    - 印尼美食点评平台
    - 覆盖多个印尼城市 (Jakarta, Bandung, Surabaya, Bali 等)
    - 内容类型: 餐厅推荐、美食指南、Foodie Trends
    - JSON-LD 格式元数据
    """

    CONFIG_KEY = "nibble"

    # 分类和城市配置
    CATEGORIES = [
        "nibbles-guide",
        "foodie-trends",
        "healthy-foodies",
        "food",
        "reviews",
    ]

    CITIES = [
        "jakarta",
        "bandung",

        "surabaya",
        "bali",
        "bogor",
        "yogyakarta",
        "semarang",
        "malang",
    ]

    # 分页 URL 模板
    CATEGORY_URL_TEMPLATE = "https://www.nibble.id/{category}/?page={page}"

    def __init__(self, use_proxy: bool = False):
        config = SITE_CONFIGS.get(self.CONFIG_KEY, {})

        super().__init__(
            name=config.get("name", "Nibble.id"),
            base_url=config.get("base_url", "https://www.nibble.id"),
            delay=config.get("delay", 0.5),
            use_proxy=use_proxy,
            country=config.get("country", "Indonesia"),
            city=config.get("city", ""),  # 从文章内容识别城市
        )

        # 使用配置中的分类，如果没有则使用默认
        self.categories = config.get("categories") or self.CATEGORIES
        self.max_pages = config.get("max_pages", 15)

    def get_article_list_urls(self) -> Generator[str, None, None]:
        """不使用默认分页模式"""
        yield "category://"

    def parse_article_list(self, html: str, list_url: str) -> List[str]:
        """不使用默认分页模式"""
        return []

    def fetch_urls_from_sitemap(self) -> List[tuple]:
        """不使用 sitemap 模式，返回空让 scrape_all 走自定义逻辑"""
        return []

    def _fetch_page_urls(self, category: str, page: int) -> List[str]:
        """从分类分页获取文章 URL 列表"""
        url = self.CATEGORY_URL_TEMPLATE.format(category=category, page=page)
        response = self.fetch(url)
        if not response:
            return []

        soup = self.parse_html(response.text)
        urls = []

        # 提取文章链接
        for link in soup.select("a[href*='nibble.id']"):
            href = link.get("href", "")
            if href and self.is_valid_article_url(href):
                full_url = self.absolute_url(href)
                if full_url not in urls:
                    urls.append(full_url)

        return urls

    def _get_max_page(self, category: str) -> int:
        """获取分类的最大页数"""
        url = self.CATEGORY_URL_TEMPLATE.format(category=category, page=1)
        response = self.fetch(url)
        if not response:
            return 1

        # 查找分页链接中的最大页码
        soup = self.parse_html(response.text)
        max_page = 1
        for match in re.findall(r'page=(\d+)', response.text):
            page_num = int(match)
            if page_num > max_page:
                max_page = page_num

        return min(max_page, self.max_pages)

    def scrape_all(self, limit: int = 0, since: str = None, exclude_urls: set = None) -> List[Article]:
        """
        从分类分页爬取文章

        Args:
            limit: 限制文章数量，0 表示不限制
            since: 只爬取该日期之后的文章，格式如 "2025-01-01"
            exclude_urls: 要排除的 URL 集合

        Returns:
            文章列表
        """
        self.logger.info(f"开始爬取 {self.name} (分类分页模式)...")
        if since:
            self.logger.info(f"启用时间过滤: since={since} (基于 publish_date)")

        exclude_urls = exclude_urls or set()
        all_articles = []
        all_urls = set()  # 去重

        max_workers = CONCURRENCY_CONFIG.get("max_workers", 5)
        consecutive_old_pages = 0
        max_consecutive_old = 2

        # 遍历每个分类
        for category in self.categories:
            if limit and len(all_articles) >= limit:
                break

            self.logger.info(f"正在爬取分类: {category}")
            max_page = self._get_max_page(category)

            for page in range(1, max_page + 1):
                if limit and len(all_articles) >= limit:
                    break

                self.logger.info(f"  获取 {category} 第 {page}/{max_page} 页...")
                page_urls = self._fetch_page_urls(category, page)

                if not page_urls:
                    self.logger.info(f"  第 {page} 页无文章，跳过")
                    break

                # 去重 + 排除已爬取
                new_urls = [url for url in page_urls if url not in all_urls and url not in exclude_urls]
                all_urls.update(new_urls)

                if not new_urls:
                    self.logger.info(f"  第 {page} 页文章都已爬取过，继续")
                    continue

                self.logger.info(f"  第 {page} 页获取到 {len(new_urls)} 篇新文章")

                # 并发爬取
                page_articles = []
                oldest_date = None

                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    future_to_url = {executor.submit(self.scrape_article, url): url for url in new_urls}
                    for future in as_completed(future_to_url):
                        url = future_to_url[future]
                        try:
                            article = future.result()
                            if article:
                                pub_date = normalize_date(article.publish_date) if article.publish_date else ""

                                # 更新最老日期
                                if pub_date:
                                    if oldest_date is None or pub_date < oldest_date:
                                        oldest_date = pub_date

                                # since 过滤
                                if since and pub_date and pub_date < since:
                                    self.logger.debug(f"since 过滤跳过: {article.title} ({pub_date})")
                                    continue

                                page_articles.append(article)
                        except Exception as e:
                            self.logger.error(f"爬取失败 {url}: {e}")

                all_articles.extend(page_articles)

                # 检查是否达到 limit
                if limit and len(all_articles) >= limit:
                    all_articles = all_articles[:limit]
                    break

                # 提前终止判断
                if since and oldest_date and oldest_date < since:
                    consecutive_old_pages += 1
                    if consecutive_old_pages >= max_consecutive_old:
                        self.logger.info(f"连续 {max_consecutive_old} 页都是老文章，切换下一分类")
                        break
                else:
                    consecutive_old_pages = 0

        self.logger.info(f"爬取完成，共获取 {len(all_articles)} 篇文章")
        return all_articles

    def is_valid_article_url(self, url: str) -> bool:
        """检查是否为有效的文章 URL"""
        if not url or "nibble.id" not in url:
            return False

        # 必须是 www.nibble.id 域名
        if "www.nibble.id" not in url:
            return False

        # 排除非文章页
        exclude_patterns = [
            "/tag/", "/category/", "/author/", "/page/",
            "/search", "/about", "/contact", "/privacy",
            "/terms", "/static/", "/wp-content/",
            # 分类页面
            "/jakarta/", "/bandung/", "/surabaya/", "/bali/",
            "/bogor/", "/yogyakarta/", "/semarang/", "/malang/",
            "/makassar/", "/depok/", "/tangerang/", "/bekasi/",
            "/solo/",
            "/food/", "/foodie-trends/", "/healthy-foodies/",
            "/inside-stories/", "/lifestyle/", "/recipes/",
            "/reviews/", "/tips-tricks/", "/populer/",
            "/nibbles-guide/", "/bars/", "/cafes/",
            "/coffee-shops/", "/desserts/", "/fine-dining/",
            "/street-food/",
        ]
        url_lower = url.lower()

        # 检查是否是分类页面 (以 / 结尾且只有一级路径)
        from urllib.parse import urlparse
        parsed = urlparse(url)
        path = parsed.path.strip("/")

        # 分类页面通常只有一个路径段
        if "/" not in path and path in [
            "jakarta", "bandung", "surabaya", "bali", "bogor",
            "yogyakarta", "semarang", "malang", "makassar",
            "depok", "tangerang", "bekasi", "solo",
            "food", "foodie-trends", "healthy-foodies",
            "inside-stories", "lifestyle", "recipes",
            "reviews", "tips-tricks", "populer",
            "nibbles-guide", "bars", "cafes",
            "coffee-shops", "desserts", "fine-dining",
            "street-food", "about-us", "contact-us",
            "terms-and-conditions",
        ]:
            return False

        return not any(p in url_lower for p in exclude_patterns)

    def _parse_jsonld(self, html: str) -> dict:
        """解析 JSON-LD 数据，处理格式问题"""
        match = re.search(r'<script type="application/ld\+json">\s*(\{.*?\})\s*</script>', html, re.DOTALL)
        if not match:
            return {}

        jsonld_str = match.group(1)
        # 修复常见的 JSON 格式问题
        jsonld_str = re.sub(r'"copyrightYear":\s*,', '"copyrightYear": null,', jsonld_str)

        try:
            return json.loads(jsonld_str)
        except json.JSONDecodeError:
            return {}

    def extract_content(self, html: str) -> str:
        """提取文章正文内容"""
        soup = self.parse_html(html)

        # Nibble 特有选择器
        for selector in [".article-content", ".article-body", ".entry-content", "article"]:
            content_el = soup.select_one(selector)
            if content_el:
                # 移除无用元素
                for tag in content_el.find_all(["script", "style", "nav", "aside", "iframe", "noscript"]):
                    tag.decompose()
                for css_sel in [".share", ".social", ".ad", ".related", ".popular-posts", ".sidebar"]:
                    for el in content_el.select(css_sel):
                        el.decompose()

                content = content_el.decode_contents()
                if len(content) > 200:
                    return content

        return ""

    def parse_article(self, html: str, url: str) -> Optional[Article]:
        """解析文章详情页"""
        soup = self.parse_html(html)

        # 标题
        title = ""
        title_el = soup.select_one("h1")
        if title_el:
            title = self.clean_text(title_el.get_text())

        if not title:
            og_title = soup.select_one("meta[property='og:title']")
            if og_title:
                title = og_title.get("content", "")

        if not title:
            return None

        # 提取内容
        content = self.extract_content(html)

        # 解析 JSON-LD 获取元数据
        jsonld = self._parse_jsonld(html)

        # 发布日期
        publish_date = jsonld.get("datePublished", "")
        if not publish_date:
            # 从 article-meta 提取
            meta_el = soup.select_one(".article-meta")
            if meta_el:
                meta_text = meta_el.get_text()
                # 匹配日期格式如 "February 03, 2026"
                date_match = re.search(r'([A-Z][a-z]+ \d{1,2}, \d{4})', meta_text)
                if date_match:
                    publish_date = date_match.group(1)

        # 作者
        author = ""
        author_data = jsonld.get("author", {})
        if isinstance(author_data, dict):
            author = author_data.get("name", "")
        if not author:
            # 从 article-meta 提取
            meta_el = soup.select_one(".article-meta")
            if meta_el:
                by_match = re.search(r'By\s+([A-Za-z\s]+)', meta_el.get_text())
                if by_match:
                    author = by_match.group(1).strip()

        # 分类 - 从 URL 或面包屑提取
        category = ""
        breadcrumb = soup.select_one(".breadcrumb a:last-child, .category a")
        if breadcrumb:
            category = self.clean_text(breadcrumb.get_text())

        # 标签
        tags = []
        keywords = jsonld.get("keywords", "")
        if keywords:
            if isinstance(keywords, str):
                tags = [k.strip() for k in keywords.split(",") if k.strip()]
            elif isinstance(keywords, list):
                tags = keywords

        # 图片
        images = []
        # 特色图
        og_image = soup.select_one("meta[property='og:image']")
        if og_image:
            src = og_image.get("content")
            if src:
                images.append(src)

        # 内容图片
        content_el = soup.select_one(".article-content")
        if content_el:
            for img in content_el.select("img"):
                src = img.get("src") or img.get("data-src")
                if src and not src.endswith(".svg") and src not in images:
                    images.append(self.absolute_url(src))

        return Article(
            url=url,
            title=title,
            content=content,
            author=author or "Nibble.id",
            publish_date=publish_date,
            category=category or "Food",
            tags=tags[:10],
            images=images[:10],
            language="id",
            country="Indonesia",
            city="",  # 从标题自动识别
        )
