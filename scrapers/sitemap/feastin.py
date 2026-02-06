# -*- coding: utf-8 -*-
"""
Feastin Indonesia 爬虫 (Sitemap 模式)
https://www.feastin.id/
印尼美食和餐饮文化媒体

使用 Sitemap 获取文章列表
Sitemap: https://www.feastin.id/sitemap.xml

文章分类路径:
- /food-news-stories/ - 美食新闻
- /eating-out/ - 外食评论
- /table-talk/ - 对话专访
- /travel/ - 旅游
- /home/ - 主要内容
- /common-table/ - 社区投稿
"""
import re
from typing import List, Optional, Generator, Tuple
from xml.etree import ElementTree

from base_scraper import BaseScraper, Article
from config import SITE_CONFIGS


class FeastinScraper(BaseScraper):
    """
    Feastin Indonesia 爬虫 (Sitemap 模式)

    Squarespace 博客平台
    - 多分类文章路径
    - 印尼语为主的美食内容

    URL模式:
    - Sitemap: /sitemap.xml
    - 文章: /{category}/[article-slug]
    """

    CONFIG_KEY = "feastin"

    def __init__(self, use_proxy: bool = False):
        config = SITE_CONFIGS.get(self.CONFIG_KEY, {})
        super().__init__(
            name=config.get("name", "Feastin Indonesia"),
            base_url=config.get("base_url", "https://www.feastin.id"),
            delay=config.get("delay", 0.5),
            use_proxy=use_proxy,
            country=config.get("country", "Indonesia"),
            city=config.get("city", ""),
        )
        self.sitemap_url = f"{self.base_url}/sitemap.xml"
        self._article_urls_cache = None
        # 分类过滤配置（从页面解析分类并过滤）
        self.categories = config.get("categories", [])

    def fetch_urls_from_sitemap(self) -> List[Tuple[str, str]]:
        """
        从 Sitemap 获取文章URL

        Returns:
            [(url, lastmod), ...] 按 lastmod 倒序排列
        """
        if self._article_urls_cache is not None:
            return self._article_urls_cache

        url_with_dates = []

        try:
            proxies = self._get_proxy()
            resp = self.session.get(self.sitemap_url, timeout=30, proxies=proxies)
            resp.raise_for_status()

            root = ElementTree.fromstring(resp.content)
            ns = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}

            for url_elem in root.findall('.//sm:url', ns):
                loc = url_elem.find('sm:loc', ns)
                lastmod = url_elem.find('sm:lastmod', ns)

                if loc is not None:
                    url = loc.text
                    mod_date = lastmod.text if lastmod is not None else ""

                    if url and self.is_valid_article_url(url):
                        url_with_dates.append((url, mod_date))

            self.logger.info(f"Sitemap: 获取 {len(url_with_dates)} 篇文章")

        except Exception as e:
            self.logger.error(f"获取 Sitemap 失败: {e}")

        url_with_dates.sort(key=lambda x: x[1] if x[1] else "", reverse=True)
        self._article_urls_cache = url_with_dates
        return url_with_dates

    def get_article_list_urls(self) -> Generator[str, None, None]:
        """生成列表页URL - 使用特殊标记"""
        yield "sitemap://feastin"

    # 所有有效的文章路径
    ALL_ARTICLE_PATHS = [
        "food-news-stories",  # 美食新闻
        "eating-out",         # 外食评论
        "table-talk",         # 对话专访
        "travel",             # 旅游
        "home",               # 主要内容
        "common-table",       # 社区投稿
    ]

    def is_valid_article_url(self, url: str) -> bool:
        """检查是否为有效的文章URL，支持按路径分类过滤"""
        if not url or "feastin.id" not in url:
            return False

        # 解析 URL 路径
        path = url.replace(self.base_url, "").strip("/")
        parts = path.split("/")

        if len(parts) < 2:
            return False  # 至少需要 category/slug

        category_path = parts[0]

        # 必须是有效的分类路径
        if category_path not in self.ALL_ARTICLE_PATHS:
            return False

        # 分类路径过滤：如果配置了 categories，只爬取指定分类
        if self.categories:
            # 标准化分类名称（统一转小写，- 替换为空格）
            config_cats = [c.lower().replace("-", " ") for c in self.categories]
            path_normalized = category_path.lower().replace("-", " ")
            if path_normalized not in config_cats:
                return False

        # 排除搜索、账户、分类列表等页面
        exclude_patterns = [
            "/config", "/search", "/account", "/cart",
            "/category/",  # 分类列表页不是文章
            "?", "#",
        ]
        if any(p in url for p in exclude_patterns):
            return False

        return True

    def parse_article_list(self, html: str, list_url: str) -> List[str]:
        """解析文章列表页 - sitemap 模式不使用"""
        return []

    def extract_content(self, html: str) -> str:
        """
        从原始 HTML 提取正文内容

        Feastin 使用 Squarespace 平台，内容在 .blog-item-content 区域
        """
        soup = self.parse_html(html)

        content_selectors = [
            ".blog-item-content",
            ".entry-content",
            ".post-content",
            "article .content",
            ".sqs-block-content",
            "article",
        ]
        for selector in content_selectors:
            content_el = soup.select_one(selector)
            if content_el:
                for tag in content_el.find_all([
                    "script", "style", "nav", "aside", "iframe",
                    "button", "form"
                ]):
                    tag.decompose()
                content = content_el.decode_contents()
                if len(content) > 200:
                    return content
        return ""

    def parse_article(self, html: str, url: str) -> Optional[Article]:
        """解析文章详情页"""
        soup = self.parse_html(html)

        # 标题 - Squarespace 用 h1 或 .blog-title
        title = ""
        title_selectors = [
            "h1.blog-title",
            "article h1",
            ".entry-title",
            "h1",
        ]
        for selector in title_selectors:
            title_el = soup.select_one(selector)
            if title_el:
                title = self.clean_text(title_el.get_text())
                if title:
                    break

        if not title:
            # 从 meta 或 title 标签获取
            og_title = soup.select_one("meta[property='og:title']")
            if og_title:
                title = og_title.get("content", "")

        if not title:
            return None

        # 内容 - 调用 extract_content 方法
        content = self.extract_content(html)

        # 作者 - Squarespace 作者区域
        author = ""
        author_selectors = [
            ".blog-author-name",
            ".author-name",
            "a[href*='/author/']",
            ".byline",
        ]
        for selector in author_selectors:
            author_el = soup.select_one(selector)
            if author_el:
                author = self.clean_text(author_el.get_text())
                if author:
                    break

        # 发布日期 - 优先从 structured data 获取
        publish_date = ""
        # 1. 优先 schema.org 的 datePublished (最准确)
        meta_date = soup.select_one("meta[itemprop='datePublished']")
        if meta_date:
            publish_date = meta_date.get("content", "")
        # 2. 其次 Open Graph 的 article:published_time
        if not publish_date:
            meta_date = soup.select_one("meta[property='article:published_time']")
            if meta_date:
                publish_date = meta_date.get("content", "")
        # 3. time 标签
        if not publish_date:
            time_el = soup.select_one("time[datetime]")
            if time_el:
                publish_date = time_el.get("datetime", "")
        # 4. 最后尝试页面文本
        if not publish_date:
            date_el = soup.select_one(".blog-date, .post-date, .date")
            if date_el:
                publish_date = self.clean_text(date_el.get_text())

        # 分类 - 从 URL 路径提取（已在 is_valid_article_url 中过滤）
        category = ""
        path = url.replace(self.base_url, "").strip("/")
        parts = path.split("/")
        if parts:
            # URL 路径格式化为分类名称（如 food-news-stories -> Food News Stories）
            category = parts[0].replace("-", " ").title()

        # 标签
        tags = []
        for tag_el in soup.select(".blog-tags a, .tags a"):
            tag = self.clean_text(tag_el.get_text())
            if tag and tag not in tags:
                tags.append(tag)

        # 图片 - Squarespace 图片
        images = []
        for img in soup.select("article img, .blog-item-content img, .entry-content img"):
            src = img.get("src") or img.get("data-src")
            if src and not src.endswith(".svg"):
                if "squarespace" in src or "feastin" in src or src.startswith("/"):
                    full_src = self.absolute_url(src)
                    if full_src not in images:
                        images.append(full_src)

        return Article(
            url=url,
            title=title,
            content=content,
            author=author or "Feastin",
            publish_date=publish_date,
            category=category,
            tags=tags,
            images=images[:10],
            language="id",  # 印尼语
        )
