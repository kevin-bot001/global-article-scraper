# -*- coding: utf-8 -*-
"""
Clever Thai 爬虫 (Sitemap 模式)
https://www.cleverthai.com/
泰国生活指南网站，涵盖餐厅、娱乐、购物等推荐
"""
import json
import re
from typing import List, Optional, Generator
from xml.etree import ElementTree as ET

from base_scraper import BaseScraper, Article
from config import SITE_CONFIGS


class CleverThaiScraper(BaseScraper):
    """
    Clever Thai 爬虫

    WordPress + Yoast SEO
    Sitemap Index: sitemap_index.xml -> post-sitemap.xml, post-sitemap2.xml

    特性:
    - 泰国生活指南（餐厅、娱乐、购物等）
    - 英语内容
    - JSON-LD @graph 格式（WebPage + Person，无 Article 节点）
    - 日期从 meta article:published_time 获取
    - 分类从 article 元素 class 提取 (如 category-guides-and-tips)
    """

    CONFIG_KEY = "clever_thai"

    def __init__(self, use_proxy: bool = False):
        config = SITE_CONFIGS.get(self.CONFIG_KEY, {})

        super().__init__(
            name=config.get("name", "Clever Thai"),
            base_url=config.get("base_url", "https://www.cleverthai.com"),
            delay=config.get("delay", 0.5),
            use_proxy=use_proxy,
            country=config.get("country", "Thailand"),
            city=config.get("city", ""),
        )

    def get_article_list_urls(self) -> Generator[str, None, None]:
        """返回 sitemap 标记"""
        yield "sitemap://"

    def parse_article_list(self, html: str, list_url: str) -> List[str]:
        """不使用列表页模式"""
        return []

    def fetch_urls_from_sitemap(self) -> List[tuple]:
        """从 Sitemap 获取文章URL (post-sitemap.xml + post-sitemap2.xml)"""
        all_urls = []
        ns = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}

        # Yoast SEO sitemap index -> 获取所有 post-sitemap
        index_url = f"{self.base_url}/sitemap_index.xml"
        response = self.fetch(index_url)
        if not response:
            self.logger.error(f"无法获取 sitemap index: {index_url}")
            return all_urls

        sitemap_urls = []
        try:
            root = ET.fromstring(response.text)
            for sitemap_el in root.findall(".//ns:sitemap", ns):
                loc = sitemap_el.find("ns:loc", ns)
                if loc is not None and loc.text:
                    url = loc.text.strip()
                    # 只要 post-sitemap，排除 page/category/author
                    if "post-sitemap" in url:
                        sitemap_urls.append(url)
        except ET.ParseError as e:
            self.logger.error(f"解析 sitemap index 失败: {e}")
            return all_urls

        self.logger.info(f"找到 {len(sitemap_urls)} 个 post-sitemap")

        # 遍历每个 post-sitemap
        for sitemap_url in sitemap_urls:
            response = self.fetch(sitemap_url)
            if not response:
                self.logger.warning(f"无法获取 sitemap: {sitemap_url}")
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
        if not url or "cleverthai.com" not in url:
            return False

        exclude_patterns = [
            "/category/", "/tag/", "/author/", "/page/",
            "/about", "/contact", "/privacy", "/terms",
            "/wp-admin/", "/wp-content/", "/wp-includes/",
            "wp-json", "feed", "xmlrpc",
            "/recent-articles/",  # 聚合页，非文章
            "/sample-page/", "/careers/", "/how-we-review",
            "/disclosure/", "/feedback-submitted/", "/resume-submitted/",
            "/site-map/", "/catupdpg/",
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
        """从 JSON-LD 提取结构化数据 (Yoast SEO @graph 格式)"""
        result = {}

        for script in soup.select('script[type="application/ld+json"]'):
            try:
                data = json.loads(script.string or "")
                items = data if isinstance(data, list) else [data]

                for item in items:
                    # @graph 格式 (Yoast SEO)
                    if "@graph" in item:
                        for graph_item in item["@graph"]:
                            item_type = graph_item.get("@type")

                            # WebPage 节点包含 datePublished 和 name
                            if item_type == "WebPage":
                                if graph_item.get("datePublished"):
                                    result["datePublished"] = graph_item["datePublished"]
                                if graph_item.get("dateModified"):
                                    result["dateModified"] = graph_item["dateModified"]
                                if graph_item.get("name"):
                                    result["headline"] = graph_item["name"]

                            # Article / BlogPosting 节点 (如果存在)
                            if item_type in ("Article", "NewsArticle", "BlogPosting"):
                                if graph_item.get("datePublished"):
                                    result["datePublished"] = graph_item["datePublished"]
                                if graph_item.get("headline"):
                                    result["headline"] = graph_item["headline"]
                                if graph_item.get("articleSection"):
                                    sections = graph_item["articleSection"]
                                    if isinstance(sections, list) and sections:
                                        result["category"] = sections[0]
                                    elif isinstance(sections, str):
                                        result["category"] = sections
                                if graph_item.get("keywords"):
                                    keywords = graph_item["keywords"]
                                    if isinstance(keywords, str):
                                        result["keywords"] = [k.strip() for k in keywords.split(",")]
                                    elif isinstance(keywords, list):
                                        result["keywords"] = keywords

                            # Person 节点
                            if item_type == "Person":
                                result["author"] = graph_item.get("name", "")

            except (json.JSONDecodeError, TypeError, KeyError):
                continue

        return result

    def extract_content(self, html: str) -> str:
        """提取正文内容"""
        soup = self.parse_html(html)

        content_selectors = [
            ".entry-content",
            ".post-content",
            "article .content",
        ]

        for selector in content_selectors:
            content_el = soup.select_one(selector)
            if content_el:
                # 移除不需要的元素
                for tag in content_el.find_all([
                    "script", "style", "nav", "aside", "iframe",
                    "noscript", "button", "form"
                ]):
                    tag.decompose()
                for css_sel in [
                    ".share", ".social", ".ad", ".advertisement",
                    ".related", ".newsletter", ".comments",
                    ".post-sharing", ".post-tags",
                    ".toc_criteria",  # 评分标准区块
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

        # 标题: 优先 h1.entry-title，其次 JSON-LD，最后 og:title
        title = ""
        title_el = soup.select_one("h1.entry-title")
        if title_el:
            title = self.clean_text(title_el.get_text())

        if not title:
            title = json_ld.get("headline", "")

        if not title:
            og_title = soup.select_one("meta[property='og:title']")
            if og_title:
                title = og_title.get("content", "")

        if not title:
            return None

        # 内容
        content = self.extract_content(html)

        # 作者: 优先 JSON-LD Person，其次 meta[name=author]
        author = json_ld.get("author", "")
        if not author:
            author_meta = soup.select_one("meta[name='author']")
            if author_meta:
                author = author_meta.get("content", "")
        if not author:
            author_el = soup.select_one(".author-name a, a[rel='author'], .byline a")
            if author_el:
                author = self.clean_text(author_el.get_text())

        # 发布日期: 优先 meta article:published_time，其次 JSON-LD
        publish_date = ""
        date_meta = soup.select_one("meta[property='article:published_time']")
        if date_meta:
            publish_date = date_meta.get("content", "")
        if not publish_date:
            publish_date = json_ld.get("datePublished", "")
        if not publish_date:
            date_el = soup.select_one("time[datetime], .entry-date, .post-date")
            if date_el:
                publish_date = date_el.get("datetime") or self.clean_text(date_el.get_text())

        # 分类: 从 article 元素的 class 提取 (如 category-guides-and-tips)
        category = json_ld.get("category", "")
        if not category:
            article_el = soup.find("article")
            if article_el:
                classes = article_el.get("class", [])
                for cls in classes:
                    if cls.startswith("category-"):
                        # category-guides-and-tips -> Guides And Tips
                        cat_name = cls.replace("category-", "").replace("-", " ").title()
                        category = cat_name
                        break
        if not category:
            cat_el = soup.select_one(".entry-category a, a[rel='category tag'], .post-category a")
            if cat_el:
                category = self.clean_text(cat_el.get_text())

        # 标签: 优先 JSON-LD keywords
        tags = json_ld.get("keywords", [])
        if not tags:
            for tag_el in soup.select(".post-tags a, .tag-links a, a[rel='tag']"):
                tag = self.clean_text(tag_el.get_text())
                if tag and tag not in tags and tag.lower() != "tags":
                    tags.append(tag)

        # 图片
        images = []
        # 特色图片 (wp-post-image)
        featured = soup.select_one(".wp-post-image, .post-thumbnail img, .featured-image img")
        if featured:
            src = featured.get("src") or featured.get("data-src")
            if src:
                images.append(self.absolute_url(src))

        # OG 图片备选
        if not images:
            og_img = soup.select_one("meta[property='og:image']")
            if og_img:
                src = og_img.get("content", "")
                if src:
                    images.append(src)

        # 正文图片
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
            author=author or "Clever Thai",
            publish_date=publish_date,
            category=category,
            tags=tags,
            images=images[:10],
            language="en",
            country="Thailand",
            city="",  # 从标题/URL 自动识别
        )
