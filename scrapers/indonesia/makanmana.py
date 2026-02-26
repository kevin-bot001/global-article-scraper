# -*- coding: utf-8 -*-
"""
MakanMana 爬虫 (Sitemap 模式)
https://makanmana.id/
印尼本土美食点评平台

使用 Sitemap 获取文章列表
Sitemap Index: https://makanmana.id/sitemap_index.xml
文章 Sitemap: /post-sitemap.xml (Yoast SEO)

分类:
- /rekomendasi/ - 推荐
- /ragam-kuliner/ - 美食种类
- /ulasan-restoran/ - 餐厅评论
"""
import json
import re
from typing import List, Optional, Generator, Tuple
from xml.etree import ElementTree

from base_scraper import BaseScraper, Article
from config import SITE_CONFIGS


class MakanManaScraper(BaseScraper):
    """
    MakanMana 爬虫 (Sitemap 模式)

    WordPress + Yoast SEO 网站
    - 有完整的 JSON-LD 结构化数据
    - 文章 URL 格式: /{category}/{slug}/
    - 分类: rekomendasi, ragam-kuliner, ulasan-restoran

    URL模式:
    - Sitemap Index: /sitemap_index.xml
    - 文章 Sitemap: /post-sitemap.xml
    """

    CONFIG_KEY = "makanmana"

    def __init__(self, use_proxy: bool = False):
        config = SITE_CONFIGS.get(self.CONFIG_KEY, {})
        super().__init__(
            name=config.get("name", "MakanMana"),
            base_url=config.get("base_url", "https://makanmana.id"),
            delay=config.get("delay", 0.5),
            use_proxy=use_proxy,
            country=config.get("country", "Indonesia"),
            city=config.get("city", ""),
        )
        self.sitemap_url = f"{self.base_url}/post-sitemap.xml"
        self._article_urls_cache = None

    def get_article_list_urls(self) -> Generator[str, None, None]:
        """生成列表页URL - 使用 sitemap 标记"""
        yield "sitemap://makanmana"

    def parse_article_list(self, html: str, list_url: str) -> List[str]:
        """解析文章列表页 - sitemap 模式不使用"""
        return []

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

    def is_valid_article_url(self, url: str) -> bool:
        """检查是否为有效的文章URL"""
        if not url or "makanmana.id" not in url:
            return False

        # 排除非文章页
        exclude_patterns = [
            "/wp-admin/", "/wp-content/", "/wp-includes/",
            "/tag/", "/category/", "/author/", "/page/",
            "/search/", "/attachment/", "/feed/",
            "/about", "/contact", "/privacy", "/terms",
            "wp-json", "sitemap", "xmlrpc",
        ]
        url_lower = url.lower()
        if any(p in url_lower for p in exclude_patterns):
            return False

        # 排除首页
        from urllib.parse import urlparse
        parsed = urlparse(url)
        path = parsed.path.strip("/")
        if not path:
            return False

        # 检查是否为有效分类路径
        valid_categories = ["rekomendasi", "ragam-kuliner", "ulasan-restoran"]
        parts = path.split("/")
        if len(parts) < 2:
            return False

        # 第一部分应该是分类
        if parts[0] not in valid_categories:
            return False

        return True

    def extract_content(self, html: str) -> str:
        """
        从原始 HTML 提取正文内容

        MakanMana 使用 WordPress 块编辑器格式
        主内容区域: div.entry-content.wp-block-post-content
        """
        soup = self.parse_html(html)

        content_selectors = [
            "div.entry-content",
            ".wp-block-post-content",
            "article .content",
            "article",
        ]

        for selector in content_selectors:
            content_el = soup.select_one(selector)
            if content_el:
                # 移除不需要的标签元素
                for tag in content_el.find_all([
                    "script", "style", "nav", "aside", "iframe",
                    "button", "form", "noscript"
                ]):
                    tag.decompose()
                # 移除 WordPress 插件相关元素
                for css_sel in [
                    ".sharedaddy", ".jp-relatedposts", ".related-posts",
                    ".social-share", ".post-share", ".share-buttons",
                    ".newsletter", ".optin", ".cta-box",
                    ".wp-block-button", ".wp-block-buttons",
                ]:
                    for el in content_el.select(css_sel):
                        el.decompose()
                content = content_el.decode_contents()
                if len(content) > 200:
                    return content
        return ""

    def _parse_json_ld(self, soup) -> dict:
        """
        从 JSON-LD 提取结构化数据

        Returns:
            包含 datePublished, dateModified, author 等的字典
        """
        result = {}

        for script in soup.select('script[type="application/ld+json"]'):
            try:
                data = json.loads(script.string or "")
                items = data if isinstance(data, list) else [data]

                for item in items:
                    # WebPage 或 Article 类型
                    if item.get("@type") in ["WebPage", "Article", "BlogPosting"]:
                        if item.get("datePublished"):
                            result["datePublished"] = item["datePublished"]
                        if item.get("dateModified"):
                            result["dateModified"] = item["dateModified"]

                    # 从嵌套的 author 对象获取作者名
                    if "author" in item:
                        author = item["author"]
                        if isinstance(author, dict):
                            if author.get("name"):
                                result["author"] = author["name"]
                        elif isinstance(author, str):
                            result["author"] = author

                    # Yoast SEO 的特殊格式：通过 @graph 嵌套
                    if "@graph" in item:
                        for graph_item in item["@graph"]:
                            if graph_item.get("@type") in ["WebPage", "Article", "BlogPosting"]:
                                if graph_item.get("datePublished"):
                                    result["datePublished"] = graph_item["datePublished"]
                                if graph_item.get("dateModified"):
                                    result["dateModified"] = graph_item["dateModified"]
                                if graph_item.get("articleSection"):
                                    sections = graph_item["articleSection"]
                                    if isinstance(sections, list) and sections:
                                        result["category"] = sections[0]
                                    elif isinstance(sections, str):
                                        result["category"] = sections
                            if graph_item.get("@type") == "Person" and graph_item.get("name"):
                                result["author"] = graph_item["name"]

            except (json.JSONDecodeError, TypeError, KeyError):
                continue

        return result

    def parse_article(self, html: str, url: str) -> Optional[Article]:
        """解析文章详情页"""
        soup = self.parse_html(html)

        # 从 JSON-LD 提取结构化数据
        json_ld = self._parse_json_ld(soup)

        # 标题 - WordPress 块编辑器格式
        title = ""
        title_selectors = [
            "h1.wp-block-post-title",
            "h1.entry-title",
            "h1.post-title",
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
            # 从 meta 获取
            og_title = soup.select_one("meta[property='og:title']")
            if og_title:
                title = og_title.get("content", "")

        if not title:
            return None

        # 内容
        content = self.extract_content(html)

        # 作者 - 优先 JSON-LD，其次页面元素
        author = json_ld.get("author", "")
        if not author:
            author_selectors = [
                ".author-name",
                ".entry-author a",
                "a[rel='author']",
                ".byline a",
            ]
            for selector in author_selectors:
                author_el = soup.select_one(selector)
                if author_el:
                    author = self.clean_text(author_el.get_text())
                    if author:
                        break

        # 发布日期 - 优先 JSON-LD
        publish_date = json_ld.get("datePublished", "")
        if not publish_date:
            date_selectors = [
                "time[datetime]",
                ".entry-date",
                ".post-date",
                "meta[property='article:published_time']",
            ]
            for selector in date_selectors:
                date_el = soup.select_one(selector)
                if date_el:
                    publish_date = date_el.get("datetime") or date_el.get("content") or self.clean_text(date_el.get_text())
                    if publish_date:
                        break

        # 分类 - 优先从 JSON-LD 获取
        category = json_ld.get("category", "")
        if not category:
            # 从 URL 路径推断分类
            from urllib.parse import urlparse
            parsed = urlparse(url)
            path_parts = parsed.path.strip("/").split("/")
            if path_parts:
                category_map = {
                    "rekomendasi": "Rekomendasi",
                    "ragam-kuliner": "Ragam Kuliner",
                    "ulasan-restoran": "Ulasan Restoran",
                }
                category = category_map.get(path_parts[0], "")

        # 标签
        tags = []
        for tag_el in soup.select(".tag-links a, .entry-tags a, a[rel='tag']"):
            tag = self.clean_text(tag_el.get_text())
            if tag and tag not in tags:
                tags.append(tag)

        # 图片
        images = []
        # 特色图
        featured = soup.select_one(".post-thumbnail img, .entry-thumbnail img, .featured-image img, .wp-block-post-featured-image img")
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
            author=author or "MakanMana",
            publish_date=publish_date,
            category=category,
            tags=tags,
            images=images[:10],
            language="id",  # 印尼语
        )
