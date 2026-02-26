# -*- coding: utf-8 -*-
"""
Manual Jakarta 爬虫
https://manual.co.id/
雅加达本地生活方式杂志，专注 food & drinks, nightlife, fashion, arts

使用 Sitemap 获取文章列表，比AJAX更高效可靠
Sitemap: https://manual.co.id/article-sitemap.xml, article-sitemap2.xml
"""
from typing import List, Optional, Generator, Tuple
from xml.etree import ElementTree

from base_scraper import BaseScraper, Article, normalize_date
from config import SITE_CONFIGS


class ManualJakartaScraper(BaseScraper):
    """
    Manual Jakarta 爬虫

    使用 Sitemap 获取文章列表（约1689篇文章）
    支持按lastmod日期倒序爬取

    URL模式:
    - Sitemap: /article-sitemap.xml, /article-sitemap2.xml
    - 详情页: /article/[article-slug]/

    注意：Manual Jakarta的文章URL不包含分类信息，分类需要从详情页获取
    """

    # 可用的分类（从详情页获取）
    AVAILABLE_CATEGORIES = [
        "food-drink", "nightlife", "fashion", "culture", "guides", "street"
    ]

    # 配置 key
    CONFIG_KEY = "manual_jakarta"

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
            name=config.get("name", "Manual Jakarta"),
            base_url=config.get("base_url", "https://manual.co.id"),
            delay=config.get("delay", 1.0),
            use_proxy=use_proxy,
            country=config.get("country", "Indonesia"),
            city=config.get("city", "Jakarta"),
        )
        self.categories = categories  # None表示全部
        self.sitemap_files = ["article-sitemap.xml", "article-sitemap2.xml"]
        self._article_urls_cache = None

    def fetch_urls_from_sitemap(self) -> List[Tuple[str, str]]:
        """
        从 Sitemap 获取所有文章URL，按lastmod倒序排列

        Returns:
            [(url, lastmod), ...] 按lastmod倒序排列
        """
        if self._article_urls_cache is not None:
            return self._article_urls_cache

        url_with_dates = []

        for sitemap_file in self.sitemap_files:
            sitemap_url = f"{self.base_url}/{sitemap_file}"
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

                self.logger.info(f"Sitemap {sitemap_file}: 获取 {count} 篇文章")

            except Exception as e:
                self.logger.error(f"获取 Sitemap {sitemap_file} 失败: {e}")

        # 按lastmod倒序排列（最新的在前）
        url_with_dates.sort(key=lambda x: x[1] if x[1] else "", reverse=True)

        self.logger.info(f"从 Sitemap 共获取 {len(url_with_dates)} 篇文章URL (按lastmod倒序)")
        self._article_urls_cache = url_with_dates
        return url_with_dates

    def get_article_list_urls(self) -> Generator[str, None, None]:
        """生成列表页URL - 使用特殊标记"""
        yield "sitemap://manual-jakarta"

    def is_valid_article_url(self, url: str) -> bool:
        """检查是否为有效的文章URL"""
        if not url:
            return False
        # Manual Jakarta 的文章URL格式: /article/xxx/
        return "/article/" in url and url.startswith(self.base_url)

    def parse_article_list(self, html: str, list_url: str) -> List[str]:
        """解析文章列表页"""
        soup = self.parse_html(html)
        article_urls = []

        # Manual Jakarta 的文章链接在各种位置
        selectors = [
            "a[href*='/article/']",  # 直接匹配文章链接
            ".post-item a[href]",
            ".article-card a[href]",
            "article a[href]",
            "h2 a[href]",
            "h3 a[href]",
        ]

        for selector in selectors:
            for link in soup.select(selector):
                href = link.get("href")
                if href:
                    full_url = self.absolute_url(href)
                    if self.is_valid_article_url(full_url) and full_url not in article_urls:
                        article_urls.append(full_url)

        self.logger.debug(f"从 {list_url} 找到 {len(article_urls)} 篇文章")
        return article_urls

    def extract_content(self, html: str) -> str:
        """
        从原始 HTML 提取正文内容

        Manual Jakarta 用 article 标签作为主内容区域
        """
        soup = self.parse_html(html)

        content_selectors = [
            "article",  # Manual Jakarta的主要内容在article标签里
            ".article-content",
            ".entry-content",
            ".post-content",
        ]
        for selector in content_selectors:
            content_el = soup.select_one(selector)
            if content_el:
                # 移除不需要的元素
                for tag in content_el.find_all(
                        ["script", "style", "nav", "aside", "footer", ".share", ".social-share-wrapper"]):
                    tag.decompose()
                # 保留HTML结构而非纯文本
                content = content_el.decode_contents()
                if len(content) > 100:
                    return content
        return ""

    def parse_article(self, html: str, url: str) -> Optional[Article]:
        """解析文章详情页"""
        soup = self.parse_html(html)

        # 标题 - Manual Jakarta 用 h1
        title = ""
        title_el = soup.select_one("h1")
        if title_el:
            title = self.clean_text(title_el.get_text())

        if not title:
            self.logger.warning(f"未找到标题: {url}")
            return None

        # 内容 - 调用 extract_content 方法
        content = self.extract_content(html)

        # 作者 - Manual Jakarta的author在.author类里，但需要排除子元素.meta-date
        author = ""
        author_el = soup.select_one(".author")
        if author_el:
            # 克隆节点，移除日期子元素后获取纯作者文本
            author_clone = author_el.__copy__()
            for date_tag in author_clone.find_all(class_="meta-date"):
                date_tag.decompose()
            author = self.clean_text(author_clone.get_text())
            # 移除 "by " 前缀
            if author.lower().startswith("by "):
                author = author[3:].strip()

        # 发布日期 - Manual Jakarta用.meta-date类，统一转换成ISO格式
        publish_date = ""
        date_el = soup.select_one(".meta-date")
        if date_el:
            raw_date = self.clean_text(date_el.get_text())
            publish_date = normalize_date(raw_date)
        else:
            # 备用选择器
            date_el = soup.select_one("time[datetime], .date, .published")
            if date_el:
                raw_date = date_el.get("datetime") or self.clean_text(date_el.get_text())
                publish_date = normalize_date(raw_date)

        # 分类 - 优先使用AJAX获取时缓存的分类
        category = ""
        if hasattr(self, '_url_categories') and url in self._url_categories:
            category = self._url_categories[url]
        else:
            # 备用：从页面底部的相关文章区提取
            cat_heading = soup.select_one("article + div h3, .related h3")
            if cat_heading:
                category = self.clean_text(cat_heading.get_text())

        # 标签 - Manual Jakarta 没有明显的标签系统，留空
        tags = []

        # 图片
        images = []
        for img in soup.select("article img, .article-content img, .featured-image img"):
            src = img.get("src") or img.get("data-src") or img.get("data-lazy-src")
            if src and not src.endswith(".svg"):
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
            language="en",  # Manual Jakarta 主要是英文
        )
