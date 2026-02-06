# -*- coding: utf-8 -*-
"""
NOW! Jakarta 爬虫
https://www.nowjakarta.co.id/
雅加达国际社区生活方式杂志

使用 Sitemap 获取文章列表，比分页爬取更高效可靠
Sitemap: https://www.nowjakarta.co.id/post-sitemap[1-5].xml
"""
from typing import List, Optional, Generator, Tuple
from xml.etree import ElementTree

from base_scraper import BaseScraper, Article
from config import SITE_CONFIGS


class NowJakartaScraper(BaseScraper):
    """
    NOW! Jakarta 爬虫

    使用 Sitemap 获取文章列表（约4456篇文章）
    支持按lastmod日期倒序爬取

    URL模式:
    - Sitemap: /post-sitemap[1-5].xml
    - 详情页: /[article-slug]/  (扁平URL结构，不含分类)
    """

    # 可用的分类
    AVAILABLE_CATEGORIES = [
        "news", "discover-jakarta", "dining", "features",
        "art-and-culture", "lifestyle", "travel"
    ]

    # 配置 key
    CONFIG_KEY = "now_jakarta"

    def __init__(self, use_proxy: bool = False, categories: List[str] = None):
        """
        初始化爬虫

        Args:
            use_proxy: 是否使用代理
            categories: 要爬取的分类列表，None表示全部
                       注意：分类过滤在爬取详情页后进行
        """
        config = SITE_CONFIGS.get(self.CONFIG_KEY, {})
        super().__init__(
            name=config.get("name", "NOW! Jakarta"),
            base_url=config.get("base_url", "https://www.nowjakarta.co.id"),
            delay=config.get("delay", 0.5),
            use_proxy=use_proxy,
            country=config.get("country", "Indonesia"),
            city=config.get("city", "Jakarta"),
        )
        self.categories = categories  # None表示全部
        self._article_urls_cache = None

    def _detect_sitemap_count(self) -> int:
        """
        动态检测有多少个sitemap文件
        NOW Jakarta每满1000篇文章就新增一个sitemap index

        Returns:
            sitemap文件数量
        """
        # 二分查找最大的sitemap index
        low, high = 1, 100  # 假设最多100个sitemap
        max_found = 0

        while low <= high:
            mid = (low + high) // 2
            sitemap_url = f"{self.base_url}/post-sitemap{mid}.xml"
            try:
                proxies = self._get_proxy()
                resp = self.session.head(sitemap_url, timeout=10, proxies=proxies)
                if resp.status_code == 200:
                    max_found = mid
                    low = mid + 1
                else:
                    high = mid - 1
            except Exception:
                high = mid - 1

        self.logger.info(f"检测到 {max_found} 个sitemap文件")
        return max_found

    def fetch_urls_from_sitemap(self) -> List[Tuple[str, str]]:
        """
        从 Sitemap 获取所有文章URL
        从最大的index开始爬（最新的文章），结果按lastmod倒序排列

        Returns:
            [(url, lastmod), ...] 按lastmod倒序排列
        """
        if self._article_urls_cache is not None:
            return self._article_urls_cache

        url_with_dates = []
        sitemap_count = self._detect_sitemap_count()

        if sitemap_count == 0:
            self.logger.error("未检测到任何sitemap文件")
            return []

        # 从最大的index开始爬（最新的文章在最大的index里）
        for i in range(sitemap_count, 0, -1):
            sitemap_url = f"{self.base_url}/post-sitemap{i}.xml"
            try:
                proxies = self._get_proxy()
                resp = self.session.get(sitemap_url, timeout=30, proxies=proxies)
                resp.raise_for_status()

                root = ElementTree.fromstring(resp.content)
                ns = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}

                count = 0
                for url_elem in root.findall('.//sm:url', ns):
                    loc = url_elem.find('sm:loc', ns)
                    lastmod = url_elem.find('sm:lastmod', ns)

                    if loc is not None:
                        url = loc.text
                        mod_date = lastmod.text if lastmod is not None else ""

                        if url and self.is_valid_article_url(url):
                            url_with_dates.append((url, mod_date))
                            count += 1

                self.logger.info(f"Sitemap {i}: 获取 {count} 篇文章")

            except Exception as e:
                self.logger.error(f"获取 Sitemap {i} 失败: {e}")

        # 按lastmod倒序排列（最新的在前）
        url_with_dates.sort(key=lambda x: x[1] if x[1] else "", reverse=True)

        self.logger.info(f"从 Sitemap 共获取 {len(url_with_dates)} 篇文章URL (按lastmod倒序)")
        self._article_urls_cache = url_with_dates
        return url_with_dates

    def get_article_list_urls(self) -> Generator[str, None, None]:
        """生成列表页URL - 使用特殊标记"""
        yield "sitemap://now-jakarta"

    def is_valid_article_url(self, url: str) -> bool:
        """检查是否为有效的文章URL"""
        if not url or not url.startswith(self.base_url):
            return False

        # 排除分类、标签、分页等URL
        exclude_patterns = [
            "/category/", "/tag/", "/page/", "/author/",
            "/wp-content/", "/wp-admin/", "/feed/",
            "/about", "/contact", "/subscribe", "/advertise",
            "/order-form",  # 订阅表单页
        ]
        url_lower = url.lower()
        if any(pattern in url_lower for pattern in exclude_patterns):
            return False

        # NOW! Jakarta 的文章URL是扁平结构: /article-slug/
        # 检查是否只有一级路径
        from urllib.parse import urlparse
        parsed = urlparse(url)
        path_parts = [p for p in parsed.path.split("/") if p]

        # 文章应该只有一级路径（slug）
        return len(path_parts) == 1

    def parse_article_list(self, html: str, list_url: str) -> List[str]:
        """解析文章列表页"""
        soup = self.parse_html(html)
        article_urls = []

        # NOW! Jakarta 的文章链接
        selectors = [
            "article h2 a[href]",
            "article h3 a[href]",
            ".post-title a[href]",
            ".entry-title a[href]",
            ".article-title a[href]",
        ]

        for selector in selectors:
            for link in soup.select(selector):
                href = link.get("href")
                if href:
                    full_url = self.absolute_url(href)
                    if self.is_valid_article_url(full_url) and full_url not in article_urls:
                        article_urls.append(full_url)

        return article_urls

    def extract_content(self, html: str) -> str:
        """
        从原始 HTML 提取正文内容

        NOW! Jakarta 用 .post-entry / .entry-content 作为主内容区域
        """
        soup = self.parse_html(html)

        content_el = None
        for selector in [".post-entry", ".entry-content", ".post-content"]:
            content_el = soup.select_one(selector)
            if content_el:
                break

        if content_el:
            # 移除不需要的元素
            for selector in [
                "script", "style", "nav", "aside",
                ".share", ".related", ".author-box", ".author-list",
                ".border-bottom",  # 分割线
            ]:
                for tag in content_el.select(selector):
                    tag.decompose()
            return content_el.decode_contents()

        return ""

    def parse_article(self, html: str, url: str) -> Optional[Article]:
        """解析文章详情页"""
        soup = self.parse_html(html)

        # 标题
        title = ""
        title_el = soup.select_one("h1.entry-title, h1.post-title, h1")
        if title_el:
            title = self.clean_text(title_el.get_text())

        if not title:
            return None

        # 作者（在 soup 未被修改时提取）
        author = ""
        author_el = soup.select_one(".author-box .author a, .author a, .byline a, .entry-author")
        if author_el:
            author = self.clean_text(author_el.get_text())

        # 内容 - 调用 extract_content 方法
        content = self.extract_content(html)

        # 发布日期
        publish_date = ""
        date_el = soup.select_one("time[datetime], .entry-date, .published")
        if date_el:
            publish_date = date_el.get("datetime") or self.clean_text(date_el.get_text())

        # 分类
        category = ""
        cat_el = soup.select_one(".category a, .cat-links a, .entry-category a")
        if cat_el:
            category = self.clean_text(cat_el.get_text())

        # 标签
        tags = []
        for tag_el in soup.select(".tag-links a, .tags a, .post-tags a"):
            tag = self.clean_text(tag_el.get_text())
            if tag and tag not in tags:
                tags.append(tag)

        # 图片
        images = []
        # 先找特色图片
        featured = soup.select_one(".post-thumbnail img, .featured-image img")
        if featured:
            src = featured.get("src") or featured.get("data-src")
            if src:
                images.append(self.absolute_url(src))

        # 再找内容中的图片
        for img in soup.select(".entry-content img"):
            src = img.get("src") or img.get("data-src")
            if src and src not in images:
                images.append(self.absolute_url(src))

        return Article(
            url=url,
            title=title,
            content=content,
            author=author,
            publish_date=publish_date,
            category=category,
            tags=tags,
            images=images[:10],
            language="en",
        )
