# -*- coding: utf-8 -*-
"""
IndoIndians 爬虫 (Sitemap 模式)
https://www.indoindians.com/
印度人在印尼的社区网站，涵盖生活、美食、文化等内容
"""
import json
import re
from typing import List, Optional, Generator
from xml.etree import ElementTree as ET

from base_scraper import BaseScraper, Article
from config import SITE_CONFIGS


class IndoIndiansScraper(BaseScraper):
    """
    IndoIndians 爬虫

    WordPress + Yoast SEO + Flavor Theme
    Sitemap: post-sitemap.xml ~ post-sitemap5.xml

    特性:
    - 印度人在印尼社区
    - 涵盖生活、美食、文化、旅游等
    - 英语内容
    - 只抓取 Jakarta/Bali/Life(Food/Travel) 相关文章
    """

    CONFIG_KEY = "indoindians"

    # 目标分类过滤 - 组合匹配：地点 + 内容类型
    # 必须同时满足两类标签才通过
    LOCATION_TAGS = {"jakarta", "bali", "living in indonesia"}
    CONTENT_TAGS = {"food", "travel"}

    def __init__(self, use_proxy: bool = False):
        config = SITE_CONFIGS.get(self.CONFIG_KEY, {})

        super().__init__(
            name=config.get("name", "IndoIndians"),
            base_url=config.get("base_url", "https://www.indoindians.com"),
            delay=config.get("delay", 0.5),
            use_proxy=use_proxy,
            country=config.get("country", "Indonesia"),
            city=config.get("city", "Jakarta"),
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
            f"{self.base_url}/post-sitemap3.xml",
            f"{self.base_url}/post-sitemap4.xml",
            f"{self.base_url}/post-sitemap5.xml",
        ]

        all_urls = []
        ns = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}

        for sitemap_url in sitemap_urls:
            response = self.fetch(sitemap_url)
            if not response:
                continue

            try:
                root = ET.fromstring(response.text)
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
        if not url or "indoindians.com" not in url:
            return False

        exclude_patterns = [
            "/category/", "/tag/", "/author/", "/page/",
            "/about", "/contact", "/privacy", "/terms",
            "/wp-admin/", "/wp-content/", "/wp-includes/",
            "wp-json", "feed", "xmlrpc",
            # 过滤测试页面
            "td_d_slug",
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
                    # @graph 格式 (Yoast SEO)
                    if "@graph" in item:
                        for graph_item in item["@graph"]:
                            if graph_item.get("@type") == "Article":
                                if graph_item.get("datePublished"):
                                    result["datePublished"] = graph_item["datePublished"]
                                if graph_item.get("headline"):
                                    result["headline"] = graph_item["headline"]
                                # articleSection 提取分类
                                if graph_item.get("articleSection"):
                                    sections = graph_item["articleSection"]
                                    if isinstance(sections, list) and sections:
                                        result["category"] = sections[0]
                                    elif isinstance(sections, str):
                                        result["category"] = sections
                            if graph_item.get("@type") == "Person":
                                result["author"] = graph_item.get("name", "")

            except (json.JSONDecodeError, TypeError, KeyError):
                continue

        return result

    def extract_content(self, html: str) -> str:
        """提取正文内容"""
        soup = self.parse_html(html)

        # Flavor Theme 使用 td-post-content
        content_selectors = [
            ".td-post-content",
            ".entry-content",
            ".post-content",
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
                    ".td-post-sharing", ".td-post-source-tags",
                ]:
                    for el in content_el.select(css_sel):
                        el.decompose()
                content = content_el.decode_contents()
                if len(content) > 200:
                    return content
        return ""

    def _matches_allowed_tags(self, category: str, tags: List[str]) -> bool:
        """
        组合匹配：地点 + 内容类型，两者都要满足
        例如：Jakarta + Food, Bali + Travel, Living in Indonesia + Food
        """
        all_labels = [category] + tags if category else tags
        all_labels_lower = {label.lower() for label in all_labels if label}

        # 检查是否有地点标签
        has_location = any(
            loc in label or label in loc
            for label in all_labels_lower
            for loc in self.LOCATION_TAGS
        )

        # 检查是否有内容类型标签
        has_content = any(
            content in label or label in content
            for label in all_labels_lower
            for content in self.CONTENT_TAGS
        )

        # 两者都满足才通过
        return has_location and has_content

    def parse_article(self, html: str, url: str) -> Optional[Article]:
        """解析文章详情页"""
        soup = self.parse_html(html)
        json_ld = self._parse_json_ld(soup)

        # 标题
        title = json_ld.get("headline", "")
        if not title:
            title_el = soup.select_one("h1.entry-title, h1.td-page-title, h1")
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
            author_el = soup.select_one(".td-post-author-name a, .author-name, a[rel='author']")
            if author_el:
                author = self.clean_text(author_el.get_text())

        # 发布日期
        publish_date = json_ld.get("datePublished", "")
        if not publish_date:
            date_el = soup.select_one("time[datetime], .td-post-date time, .entry-date")
            if date_el:
                publish_date = date_el.get("datetime") or self.clean_text(date_el.get_text())

        # 分类：优先 JSON-LD，备选页面元素
        category = json_ld.get("category", "")
        if not category:
            cat_el = soup.select_one(".td-category a, .entry-category a, a[rel='category tag']")
            if cat_el:
                category = self.clean_text(cat_el.get_text())

        # 标签
        tags = []
        for tag_el in soup.select(".td-tags a, .tag-links a, a[rel='tag']"):
            tag = self.clean_text(tag_el.get_text())
            if tag and tag not in tags and tag.lower() != "tags":
                tags.append(tag)

        # 图片
        images = []
        featured = soup.select_one(".td-post-featured-image img, .post-thumbnail img")
        if featured:
            src = featured.get("src") or featured.get("data-src")
            if src:
                images.append(self.absolute_url(src))

        for img in soup.select(".td-post-content img, .entry-content img"):
            src = img.get("src") or img.get("data-src")
            if src and not src.endswith(".svg"):
                full_src = self.absolute_url(src)
                if full_src not in images:
                    images.append(full_src)

        # 标签过滤：只保留 Jakarta/Bali/Life(Food/Travel) 相关文章
        if not self._matches_allowed_tags(category, tags):
            self.logger.debug(f"跳过文章（标签不匹配）: {title[:50]}... | 分类: {category} | 标签: {tags}")
            return None

        return Article(
            url=url,
            title=title,
            content=content,
            author=author or "IndoIndians",
            publish_date=publish_date,
            category=category,
            tags=tags,
            images=images[:10],
            language="en",
            country="Indonesia",
            city="Jakarta",
        )
