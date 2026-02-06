# -*- coding: utf-8 -*-
"""
Exquisite Taste Magazine 爬虫 (Sitemap 模式)
https://exquisite-taste-magazine.com/
印尼高端餐饮和生活方式杂志

使用 Sitemap 获取文章列表
Sitemap Index: https://exquisite-taste-magazine.com/sitemap.xml
文章 Sitemap: /post-sitemap1.xml ~ /post-sitemap5.xml
"""
import re
from typing import List, Optional, Generator, Tuple
from xml.etree import ElementTree

from base_scraper import BaseScraper, Article
from config import SITE_CONFIGS


class ExquisiteTasteScraper(BaseScraper):
    """
    Exquisite Taste Magazine 爬虫 (Sitemap 模式)

    WordPress 网站，文章分布在多个 sitemap 文件中
    - post-sitemap1.xml ~ post-sitemap5.xml

    URL模式:
    - Sitemap Index: /sitemap.xml
    - 文章: /[article-slug]/
    """

    CONFIG_KEY = "exquisite_taste"

    def __init__(self, use_proxy: bool = False):
        config = SITE_CONFIGS.get(self.CONFIG_KEY, {})
        super().__init__(
            name=config.get("name", "Exquisite Taste Magazine"),
            base_url=config.get("base_url", "https://exquisite-taste-magazine.com"),
            delay=config.get("delay", 0.5),
            use_proxy=use_proxy,
            country=config.get("country", "Indonesia"),
            city=config.get("city", ""),
        )
        self.sitemap_index_url = f"{self.base_url}/sitemap.xml"
        self._article_urls_cache = None
        # 分类过滤配置（从页面解析分类并过滤）
        self.categories = config.get("categories", [])

    def _get_post_sitemap_urls(self) -> List[str]:
        """
        从 sitemap index 获取所有 post-sitemap 文件URL

        Returns:
            post-sitemap URL 列表
        """
        sitemap_urls = []

        try:
            proxies = self._get_proxy()
            resp = self.session.get(self.sitemap_index_url, timeout=30, proxies=proxies)
            resp.raise_for_status()

            root = ElementTree.fromstring(resp.content)
            ns = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}

            for sitemap in root.findall('.//sm:sitemap', ns):
                loc = sitemap.find('sm:loc', ns)
                if loc is not None and loc.text:
                    # 只要 post-sitemap 文件
                    if "post-sitemap" in loc.text:
                        sitemap_urls.append(loc.text)

            self.logger.info(f"找到 {len(sitemap_urls)} 个 post-sitemap 文件")

        except Exception as e:
            self.logger.error(f"获取 sitemap index 失败: {e}")

        return sitemap_urls

    def fetch_urls_from_sitemap(self) -> List[Tuple[str, str]]:
        """
        从所有 post-sitemap 获取文章URL

        Returns:
            [(url, lastmod), ...] 按 lastmod 倒序排列
        """
        if self._article_urls_cache is not None:
            return self._article_urls_cache

        url_with_dates = []
        sitemap_urls = self._get_post_sitemap_urls()

        for sitemap_url in sitemap_urls:
            try:
                proxies = self._get_proxy()
                resp = self.session.get(sitemap_url, timeout=30, proxies=proxies)
                if resp.status_code != 200:
                    continue

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

                self.logger.info(f"Sitemap {sitemap_url.split('/')[-1]}: 获取 {count} 篇文章")

            except Exception as e:
                self.logger.warning(f"获取 Sitemap {sitemap_url} 失败: {e}")

        url_with_dates.sort(key=lambda x: x[1] if x[1] else "", reverse=True)
        self.logger.info(f"从 Sitemap 共获取 {len(url_with_dates)} 篇文章URL (按lastmod倒序)")
        self._article_urls_cache = url_with_dates
        return url_with_dates

    def get_article_list_urls(self) -> Generator[str, None, None]:
        """生成列表页URL - 使用特殊标记"""
        yield "sitemap://exquisite-taste"

    def is_valid_article_url(self, url: str) -> bool:
        """检查是否为有效的文章URL"""
        if not url or "exquisite-taste-magazine.com" not in url:
            return False

        # 排除非文章页
        exclude_patterns = [
            "/wp-admin/", "/wp-content/", "/wp-includes/",
            "/tag/", "/category/", "/author/", "/page/",
            "/search/", "/attachment/", "/feed/",
            "/about", "/contact", "/privacy", "/terms",
        ]
        url_lower = url.lower()
        if any(p in url_lower for p in exclude_patterns):
            return False

        # 必须有文章 slug（至少一级路径）
        path = url.replace(self.base_url, "").strip("/")
        if not path or "/" in path.strip("/"):
            # 允许单级路径（文章）但排除多级路径（分类等）
            # 实际上 WordPress 文章通常是单级路径
            pass

        return True

    def parse_article_list(self, html: str, list_url: str) -> List[str]:
        """解析文章列表页 - sitemap 模式不使用"""
        return []

    def extract_content(self, html: str) -> str:
        """
        从原始 HTML 提取正文内容

        WordPress 站点，用 .entry-content 作为主内容区域
        """
        soup = self.parse_html(html)

        content_selectors = [
            ".entry-content",
            ".post-content",
            "article .content",
            ".article-content",
            "article",
        ]
        for selector in content_selectors:
            content_el = soup.select_one(selector)
            if content_el:
                # 移除不需要的标签元素
                for tag in content_el.find_all([
                    "script", "style", "nav", "aside", "iframe",
                    "button", "form"
                ]):
                    tag.decompose()
                # 移除不需要的 class 元素（WordPress 插件相关）
                for css_sel in [".sharedaddy", ".jp-relatedposts"]:
                    for el in content_el.select(css_sel):
                        el.decompose()
                content = content_el.decode_contents()
                if len(content) > 200:
                    return content
        return ""

    def parse_article(self, html: str, url: str) -> Optional[Article]:
        """解析文章详情页"""
        soup = self.parse_html(html)

        # 标题 - WordPress h1.entry-title
        title = ""
        title_selectors = [
            "h1.entry-title",
            "h1.post-title",
            ".entry-header h1",
            "article h1",
            "h1",
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

        # 作者
        author = ""
        author_selectors = [
            ".author-name",
            ".entry-author a",
            "a[rel='author']",
            ".byline a",
            ".author a",
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
            ".posted-on time",
            "meta[property='article:published_time']",
        ]
        for selector in date_selectors:
            date_el = soup.select_one(selector)
            if date_el:
                publish_date = date_el.get("datetime") or date_el.get("content") or self.clean_text(date_el.get_text())
                if publish_date:
                    break

        # 分类 - 从页面链接中提取（/category/xxx/ 格式）
        category = ""
        article_categories = []  # 文章所属的所有分类
        cat_selectors = [
            ".cat-links a",
            ".entry-categories a",
            "a[rel='category tag']",
            "a[href*='/category/']",  # 任何分类链接
        ]
        for selector in cat_selectors:
            for cat_el in soup.select(selector):
                href = cat_el.get("href", "")
                cat_name = self.clean_text(cat_el.get_text())
                # 从 href 提取分类 slug
                if "/category/" in href:
                    match = re.search(r'/category/([^/]+)/?', href)
                    if match:
                        article_categories.append(match.group(1).lower())
                if cat_name and not category:
                    category = cat_name

        # 分类过滤：如果配置了 categories 且文章有分类信息，检查是否匹配
        # 注意：该网站文章页面可能没有分类链接，所以没有分类信息的文章默认通过
        if self.categories and article_categories:
            config_cats = [c.lower() for c in self.categories]
            # 检查文章任意分类是否在配置中
            matched = any(cat in config_cats for cat in article_categories)
            if not matched:
                self.logger.debug(f"文章分类 {article_categories} 不在配置 {config_cats} 中，跳过")
                return None

        # 标签
        tags = []
        for tag_el in soup.select(".tag-links a, .entry-tags a, a[rel='tag']"):
            tag = self.clean_text(tag_el.get_text())
            if tag and tag not in tags:
                tags.append(tag)

        # 图片
        images = []
        # 特色图
        featured = soup.select_one(".post-thumbnail img, .entry-thumbnail img, .featured-image img")
        if featured:
            src = featured.get("src") or featured.get("data-src")
            if src:
                images.append(self.absolute_url(src))

        # 内容图片
        for img in soup.select(".entry-content img, article img"):
            src = img.get("src") or img.get("data-src") or img.get("data-lazy-src")
            if src and not src.endswith(".svg"):
                full_src = self.absolute_url(src)
                if full_src not in images:
                    images.append(full_src)

        return Article(
            url=url,
            title=title,
            content=content,
            author=author or "Exquisite Taste",
            publish_date=publish_date,
            category=category,
            tags=tags,
            images=images[:10],
            language="en",
        )
