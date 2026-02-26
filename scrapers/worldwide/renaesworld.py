# -*- coding: utf-8 -*-
"""
Renae's World 爬虫 (Sitemap 模式)
https://renaesworld.com.au/
澳大利亚旅游和生活方式博客
"""
import json
import re
from typing import List, Optional, Generator
from xml.etree import ElementTree as ET

from base_scraper import BaseScraper, Article
from config import SITE_CONFIGS


class RenaesWorldScraper(BaseScraper):
    """
    Renae's World 爬虫

    WordPress + All in One SEO
    Sitemap: post-sitemap.xml, post-sitemap2.xml

    特性:
    - 澳大利亚旅游博客
    - 覆盖全球旅游目的地
    - JSON-LD 结构化数据
    """

    CONFIG_KEY = "renaesworld"

    def __init__(self, use_proxy: bool = False):
        config = SITE_CONFIGS.get(self.CONFIG_KEY, {})

        super().__init__(
            name=config.get("name", "Renae's World"),
            base_url=config.get("base_url", "https://renaesworld.com.au"),
            delay=config.get("delay", 0.5),
            use_proxy=use_proxy,
            country=config.get("country", ""),
            city=config.get("city", ""),
        )

    def get_article_list_urls(self) -> Generator[str, None, None]:
        """返回 sitemap 标记"""
        yield "sitemap://"

    def parse_article_list(self, html: str, list_url: str) -> List[str]:
        """不使用列表页模式"""
        return []

    def fetch_urls_from_sitemap(self) -> List[tuple]:
        """从 Sitemap 获取文章URL"""
        sitemap_urls = [
            f"{self.base_url}/post-sitemap.xml",
            f"{self.base_url}/post-sitemap2.xml",
        ]

        all_urls = []
        ns = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}

        for sitemap_url in sitemap_urls:
            response = self.fetch(sitemap_url)
            if not response:
                continue

            try:
                # 移除 CDATA 包装
                content = response.text
                content = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', content, flags=re.DOTALL)
                root = ET.fromstring(content)

                for url_el in root.findall(".//ns:url", ns):
                    loc = url_el.find("ns:loc", ns)
                    lastmod = url_el.find("ns:lastmod", ns)

                    if loc is not None and loc.text:
                        url = loc.text.strip()
                        if self.is_valid_article_url(url):
                            mod_date = lastmod.text.strip() if lastmod is not None and lastmod.text else ""
                            all_urls.append((url, mod_date))

            except ET.ParseError as e:
                self.logger.error(f"解析 sitemap 失败: {sitemap_url} - {e}")

        self.logger.info(f"从 Sitemap 获取到 {len(all_urls)} 篇文章")
        return all_urls

    def is_valid_article_url(self, url: str) -> bool:
        """检查是否为有效的文章URL"""
        if not url or "renaesworld.com.au" not in url:
            return False

        exclude_patterns = [
            "/category/", "/tag/", "/author/", "/page/",
            "/about", "/contact", "/privacy", "/terms",
            "/wp-admin/", "/wp-content/", "/wp-includes/",
            "wp-json", "feed", "xmlrpc",
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

        return True

    def _parse_json_ld(self, soup) -> dict:
        """从 JSON-LD 提取结构化数据"""
        result = {}

        for script in soup.select('script[type="application/ld+json"]'):
            try:
                data = json.loads(script.string or "")
                items = data if isinstance(data, list) else [data]

                for item in items:
                    if item.get("@type") in ["Article", "BlogPosting", "WebPage"]:
                        if item.get("datePublished"):
                            result["datePublished"] = item["datePublished"]
                        if item.get("headline"):
                            result["headline"] = item["headline"]

                    if "author" in item:
                        author = item["author"]
                        if isinstance(author, dict):
                            result["author"] = author.get("name", "")
                        elif isinstance(author, str):
                            result["author"] = author

                    # @graph 格式
                    if "@graph" in item:
                        for graph_item in item["@graph"]:
                            if graph_item.get("@type") in ["Article", "BlogPosting"]:
                                if graph_item.get("datePublished"):
                                    result["datePublished"] = graph_item["datePublished"]
                                if graph_item.get("headline"):
                                    result["headline"] = graph_item["headline"]
                            if graph_item.get("@type") == "Person":
                                result["author"] = graph_item.get("name", "")

            except (json.JSONDecodeError, TypeError, KeyError):
                continue

        return result

    def _extract_categories(self, soup) -> tuple:
        """
        从导航菜单提取主分类和子分类
        Returns: (main_category, sub_category)
        """
        main_category = ""
        sub_category = ""

        # 从 current-post-parent 菜单项提取分类
        for el in soup.select(".current-post-parent"):
            link = el.find("a", recursive=False) or el.select_one("a")
            if not link:
                continue

            href = link.get("href", "")
            text = self.clean_text(link.get_text())

            if not href or not text:
                continue

            # 通过URL路径深度判断是主分类还是子分类
            # /category/hotel-reviews/ -> 主分类
            # /category/hotel-reviews/asia-hotels-2/ -> 子分类
            from urllib.parse import urlparse
            path = urlparse(href).path.strip("/")
            parts = [p for p in path.split("/") if p and p != "category"]

            if len(parts) == 1:
                # 一级分类 = 主分类
                main_category = text
            elif len(parts) >= 2:
                # 二级以上 = 子分类
                sub_category = text

        return main_category, sub_category

    def extract_content(self, html: str) -> str:
        """提取正文内容"""
        soup = self.parse_html(html)

        content_selectors = [
            ".entry-content",
            ".post-content",
            "article .content",
            "article",
        ]

        for selector in content_selectors:
            content_el = soup.select_one(selector)
            if content_el:
                for tag in content_el.find_all([
                    "script", "style", "nav", "aside", "iframe",
                    "noscript", "button", "form"
                ]):
                    tag.decompose()
                for css_sel in [
                    ".share", ".social", ".ad", ".advertisement",
                    ".related", ".newsletter", ".comments",
                ]:
                    for el in content_el.select(css_sel):
                        el.decompose()
                content = content_el.decode_contents()
                if len(content) > 200:
                    return content
        return ""

    def parse_article(self, html: str, url: str) -> Optional[Article]:
        """解析文章详情页"""
        soup = self.parse_html(html)
        json_ld = self._parse_json_ld(soup)

        # 标题
        title = json_ld.get("headline", "")
        if not title:
            title_el = soup.select_one("h1.entry-title, h1.post-title, h1")
            if title_el:
                title = self.clean_text(title_el.get_text())

        if not title:
            og_title = soup.select_one("meta[property='og:title']")
            if og_title:
                title = og_title.get("content", "")

        if not title:
            return None

        # 内容
        content = self.extract_content(html)

        # 作者
        author = json_ld.get("author", "")
        if not author:
            author_el = soup.select_one(".author-name, .byline a, a[rel='author']")
            if author_el:
                author = self.clean_text(author_el.get_text())

        # 发布日期
        publish_date = json_ld.get("datePublished", "")
        if not publish_date:
            date_el = soup.select_one("time[datetime], .entry-date, .post-date")
            if date_el:
                publish_date = date_el.get("datetime") or self.clean_text(date_el.get_text())

        # 分类：从导航菜单的 current-post-parent 提取
        main_category, sub_category = self._extract_categories(soup)
        category = main_category

        # 过滤掉非旅游核心内容的分类
        if category in ("Airlines", "Interviews"):
            return None

        # 标签：子分类作为第一个标签
        tags = []
        if sub_category and sub_category not in tags:
            tags.append(sub_category)

        for tag_el in soup.select(".tag-links a, .tags a, a[rel='tag']"):
            tag = self.clean_text(tag_el.get_text())
            if tag and tag not in tags:
                tags.append(tag)

        # 图片
        images = []
        featured = soup.select_one(".post-thumbnail img, .featured-image img")
        if featured:
            src = featured.get("src") or featured.get("data-src")
            if src:
                images.append(self.absolute_url(src))

        for img in soup.select(".entry-content img"):
            src = img.get("src") or img.get("data-src")
            if src and not src.endswith(".svg"):
                full_src = self.absolute_url(src)
                if full_src not in images:
                    images.append(full_src)

        return Article(
            url=url,
            title=title,
            content=content,
            author=author or "Renae",
            publish_date=publish_date,
            category=category,
            tags=tags,
            images=images[:10],
            language="en",
            country=self.country,
            city=self.city,
        )
