# -*- coding: utf-8 -*-
"""
Flokq Blog 爬虫
https://www.flokq.com/blog
Jakarta 共居(Coliving)生活博客

使用 Sitemap Index 动态获取子 sitemap，按 lastmod 倒序爬取
Sitemap Index: https://www.flokq.com/blog/sitemap_index.xml
"""
from typing import List, Optional, Generator, Tuple
from xml.etree import ElementTree

from base_scraper import BaseScraper, Article
from config import SITE_CONFIGS


class FlokqBlogScraper(BaseScraper):
    """
    Flokq Blog 爬虫

    从 Sitemap Index 动态获取子 sitemap，按 lastmod 倒序爬取
    只爬取 post-sitemap*.xml（排除 page/category/tag sitemap）

    URL模式:
    - Sitemap Index: /blog/sitemap_index.xml
    - 子 Sitemap: /blog/post-sitemap1.xml, post-sitemap2.xml, ...
    - 详情页: /blog/[lang]/[article-slug]
    """

    # 配置 key
    CONFIG_KEY = "flokq_blog"

    def __init__(self, use_proxy: bool = False, categories: List[str] = None):
        """
        初始化爬虫

        Args:
            use_proxy: 是否使用代理
            categories: 要爬取的分类列表，None表示全部
        """
        config = SITE_CONFIGS.get(self.CONFIG_KEY, {})
        super().__init__(
            name=config.get("name", "Flokq Blog"),
            base_url=config.get("base_url", "https://www.flokq.com/blog"),
            delay=config.get("delay", 0.5),
            use_proxy=use_proxy,
            country=config.get("country", "Indonesia"),
            city=config.get("city", "Jakarta"),
        )
        self.categories = categories
        self.sitemap_index_url = "https://www.flokq.com/blog/sitemap_index.xml"
        self._article_urls_cache = None

    def _get_child_sitemaps(self) -> List[Tuple[str, str]]:
        """
        从 Sitemap Index 获取所有 post-sitemap URL 和 lastmod

        Returns:
            [(sitemap_url, lastmod), ...] 按 lastmod 倒序
        """
        sitemaps = []
        try:
            resp = self.session.get(self.sitemap_index_url, timeout=30)
            resp.raise_for_status()

            root = ElementTree.fromstring(resp.content)
            ns = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}

            for sitemap_elem in root.findall('.//sm:sitemap', ns):
                loc = sitemap_elem.find('sm:loc', ns)
                lastmod = sitemap_elem.find('sm:lastmod', ns)
                if loc is not None and loc.text:
                    sitemap_url = loc.text
                    # 只要 post-sitemap，排除 page/category/tag
                    if 'post-sitemap' in sitemap_url:
                        lastmod_val = lastmod.text if lastmod is not None else ""
                        sitemaps.append((sitemap_url, lastmod_val))

            # 按 lastmod 倒序排列
            sitemaps.sort(key=lambda x: x[1], reverse=True)
            self.logger.info(f"从 Sitemap Index 获取到 {len(sitemaps)} 个子 sitemap")
        except Exception as e:
            self.logger.error(f"获取 Sitemap Index 失败: {e}")

        return sitemaps

    def fetch_urls_from_sitemap(self) -> List[Tuple[str, str]]:
        """
        从所有子 Sitemap 获取文章URL，按lastmod倒序排列

        Returns:
            [(url, lastmod), ...] 按lastmod倒序排列
        """
        if self._article_urls_cache is not None:
            return self._article_urls_cache

        url_with_dates = []
        child_sitemaps = self._get_child_sitemaps()

        for sitemap_url, _ in child_sitemaps:
            try:
                resp = self.session.get(sitemap_url, timeout=30)
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

                self.logger.info(f"子 Sitemap {sitemap_url}: {len(url_with_dates)} 篇文章（累计）")
            except Exception as e:
                self.logger.error(f"获取子 Sitemap {sitemap_url} 失败: {e}")

        # 按lastmod倒序排列（最新的在前）
        url_with_dates.sort(key=lambda x: x[1] if x[1] else "", reverse=True)

        self.logger.info(f"从 Sitemap 共获取 {len(url_with_dates)} 篇文章URL (按lastmod倒序)")
        self._article_urls_cache = url_with_dates
        return url_with_dates

    def get_article_list_urls(self) -> Generator[str, None, None]:
        """生成列表页URL - 使用特殊标记"""
        yield "sitemap://flokq-blog"

    def is_valid_article_url(self, url: str) -> bool:
        """检查是否为有效的文章URL"""
        if not url or "flokq.com/blog" not in url:
            return False

        # 排除分类、分页、作者页、首页
        exclude_patterns = [
            "/category/", "/page/", "/author/",
            "/tag/", "/search",
        ]
        if any(pattern in url for pattern in exclude_patterns):
            return False

        # 排除首页
        if url.rstrip("/") == "https://www.flokq.com/blog":
            return False

        # Flokq 文章URL: /blog/en/article-slug 或 /blog/id/article-slug
        path = url.replace("https://www.flokq.com/blog", "")
        if not path or path == "/":
            return False

        return True

    def parse_article_list(self, html: str, list_url: str) -> List[str]:
        """解析文章列表页 - 保留兼容性，返回纯URL列表"""
        return [url for url, _ in self.fetch_urls_from_sitemap()]

    def extract_content(self, html: str) -> str:
        """
        从原始 HTML 提取正文内容

        Flokq Blog 用 .entry-content 作为主内容区域
        """
        soup = self.parse_html(html)

        content_selectors = [
            ".entry-content",
            ".post-content",
            "article .content",
            "main article",
        ]
        for selector in content_selectors:
            content_el = soup.select_one(selector)
            if content_el:
                # 移除不需要的标签元素
                for tag in content_el.find_all(["script", "style", "nav", "aside"]):
                    tag.decompose()
                # 移除不需要的 class 元素
                for css_sel in [".share", ".related"]:
                    for el in content_el.select(css_sel):
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
        title_el = soup.select_one("h1")
        if title_el:
            title = self.clean_text(title_el.get_text())

        if not title:
            return None

        # 内容 - 调用 extract_content 方法
        content = self.extract_content(html)

        # 作者
        author = ""
        author_el = soup.select_one(".author a, .byline, [class*='author']")
        if author_el:
            author = self.clean_text(author_el.get_text())

        # 发布日期
        publish_date = ""
        date_el = soup.select_one("time[datetime], .date, .published, [class*='date']")
        if date_el:
            publish_date = date_el.get("datetime") or self.clean_text(date_el.get_text())

        # 分类
        category = ""
        cat_el = soup.select_one(".category a, [class*='category'] a")
        if cat_el:
            category = self.clean_text(cat_el.get_text())

        # 标签
        tags = []
        for tag_el in soup.select(".tag a, .tags a"):
            tag = self.clean_text(tag_el.get_text())
            if tag and tag not in tags:
                tags.append(tag)

        # 语言检测 - 从URL判断
        language = "id"  # 默认印尼语
        if "/en/" in url:
            language = "en"

        # 图片
        images = []
        for img in soup.select("article img, .entry-content img, .featured-image img"):
            src = img.get("src") or img.get("data-src")
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
            language=language,
        )
