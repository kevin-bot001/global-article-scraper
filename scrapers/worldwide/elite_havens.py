# -*- coding: utf-8 -*-
"""
Elite Havens Magazine 爬虫 (Sitemap 模式)
https://www.elitehavens.com/magazine/
高端别墅/美食杂志，覆盖东南亚多个区域（巴厘岛、普吉岛、日本等）
"""
import json
from typing import List, Optional, Generator
from xml.etree import ElementTree as ET

from base_scraper import BaseScraper, Article
from config import SITE_CONFIGS


class EliteHavensScraper(BaseScraper):
    """
    Elite Havens Magazine 爬虫

    WordPress + Avada Theme + Yoast SEO
    Sitemap: magazine-proxy.elitehavens.com/post-sitemap.xml
    实际文章 URL: www.elitehavens.com/magazine/slug/

    特性:
    - 高端别墅杂志，覆盖东南亚多区域
    - 美食、旅行、生活方式内容
    - Yoast SEO @graph JSON-LD 结构化数据
    - sitemap 域名 (magazine-proxy) 与实际域名 (www) 不同，需要做 URL 转换
    - 正文容器: .post-content
    - 英语内容
    """

    CONFIG_KEY = "elite_havens"

    # sitemap 代理域名 -> 实际文章 URL 的映射
    SITEMAP_HOST = "magazine-proxy.elitehavens.com"
    ARTICLE_PATH_PREFIX = "/magazine/"

    def __init__(self, use_proxy: bool = False):
        config = SITE_CONFIGS.get(self.CONFIG_KEY, {})

        super().__init__(
            name=config.get("name", "Elite Havens Magazine"),
            base_url=config.get("base_url", "https://www.elitehavens.com"),
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

    def _convert_sitemap_url(self, sitemap_url: str) -> str:
        """
        将 sitemap 代理域名 URL 转换为实际文章 URL

        magazine-proxy.elitehavens.com/slug/
        -> www.elitehavens.com/magazine/slug/
        """
        from urllib.parse import urlparse

        parsed = urlparse(sitemap_url)
        if parsed.hostname == self.SITEMAP_HOST:
            path = parsed.path  # e.g. /slug/
            return f"{self.base_url}{self.ARTICLE_PATH_PREFIX.rstrip('/')}{path}"
        return sitemap_url

    def fetch_urls_from_sitemap(self) -> List[tuple]:
        """从 Sitemap 获取文章URL"""
        sitemap_url = f"https://{self.SITEMAP_HOST}/post-sitemap.xml"

        all_urls = []
        ns = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}

        response = self.fetch(sitemap_url)
        if not response:
            self.logger.error(f"无法获取 sitemap: {sitemap_url}")
            return all_urls

        try:
            root = ET.fromstring(response.text)
            for url_el in root.findall(".//ns:url", ns):
                loc = url_el.find("ns:loc", ns)
                lastmod = url_el.find("ns:lastmod", ns)

                if loc is not None and loc.text:
                    raw_url = loc.text.strip()
                    # 转换为实际文章 URL
                    url = self._convert_sitemap_url(raw_url)
                    if self.is_valid_article_url(url):
                        mod_date = lastmod.text.strip() if lastmod is not None and lastmod.text else ""
                        all_urls.append((url, mod_date))

        except ET.ParseError as e:
            self.logger.error(f"解析 sitemap 失败: {sitemap_url} - {e}")

        self.logger.info(f"从 Sitemap 获取到 {len(all_urls)} 篇文章")
        return all_urls

    def is_valid_article_url(self, url: str) -> bool:
        """检查是否为有效的文章URL"""
        if not url or "elitehavens.com" not in url:
            return False

        # 必须是 /magazine/ 路径下的文章
        if "/magazine/" not in url:
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

        # 排除 magazine 首页 (只有 /magazine/ 没有 slug)
        from urllib.parse import urlparse
        parsed = urlparse(url)
        path = parsed.path.strip("/")
        # path 应该是 "magazine/slug"，至少两段
        parts = path.split("/")
        if len(parts) < 2 or not parts[1]:
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
                            # Article 或 NewsArticle
                            if item_type in ("Article", "NewsArticle", "BlogPosting"):
                                if graph_item.get("datePublished"):
                                    result["datePublished"] = graph_item["datePublished"]
                                if graph_item.get("headline"):
                                    result["headline"] = graph_item["headline"]
                                # author (嵌套对象)
                                author_obj = graph_item.get("author")
                                if isinstance(author_obj, dict) and author_obj.get("name"):
                                    result["author"] = author_obj["name"]
                                # articleSection 提取分类
                                if graph_item.get("articleSection"):
                                    sections = graph_item["articleSection"]
                                    if isinstance(sections, list) and sections:
                                        result["category"] = sections[0]
                                    elif isinstance(sections, str):
                                        result["category"] = sections
                                # keywords 提取标签
                                if graph_item.get("keywords"):
                                    keywords = graph_item["keywords"]
                                    if isinstance(keywords, str):
                                        result["keywords"] = [k.strip() for k in keywords.split(",")]
                                    elif isinstance(keywords, list):
                                        result["keywords"] = keywords
                                # thumbnailUrl
                                if graph_item.get("thumbnailUrl"):
                                    result["thumbnailUrl"] = graph_item["thumbnailUrl"]
                            if item_type == "Person":
                                if not result.get("author"):
                                    result["author"] = graph_item.get("name", "")

            except (json.JSONDecodeError, TypeError, KeyError):
                continue

        return result

    def extract_content(self, html: str) -> str:
        """提取正文内容"""
        soup = self.parse_html(html)

        # Elite Havens Magazine 使用 Avada 主题，正文在 .post-content
        content_selectors = [
            ".post-content",
            ".entry-content",
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
                    ".fusion-sharing-box", ".related-posts",
                    ".about-author",
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
            title_el = soup.select_one("h1.entry-title, h1")
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
            author_el = soup.select_one(".author-name a, a[rel='author'], .byline a, .vcard .fn a")
            if author_el:
                author = self.clean_text(author_el.get_text())

        # 发布日期
        publish_date = json_ld.get("datePublished", "")
        if not publish_date:
            # OG meta
            og_date = soup.select_one("meta[property='article:published_time']")
            if og_date:
                publish_date = og_date.get("content", "")
        if not publish_date:
            date_el = soup.select_one("time[datetime], .entry-date, .post-date, .updated")
            if date_el:
                publish_date = date_el.get("datetime") or self.clean_text(date_el.get_text())

        # 分类
        category = json_ld.get("category", "")
        if not category:
            cat_el = soup.select_one("a[rel='category tag'], .fusion-meta-info-wrapper a[rel='category tag']")
            if cat_el:
                category = self.clean_text(cat_el.get_text())

        # 标签：优先 JSON-LD keywords
        tags = json_ld.get("keywords", [])
        if not tags:
            for tag_el in soup.select(".post-tags a, .tagcloud a, a[rel='tag']"):
                tag = self.clean_text(tag_el.get_text())
                if tag and tag not in tags and tag.lower() != "tags":
                    tags.append(tag)

        # 图片
        images = []
        # 特色图片 (Avada 主题)
        featured = soup.select_one(".fusion-featured-image-wrapper img, .post-thumbnail img, .featured-image img")
        if featured:
            src = featured.get("data-orig-src") or featured.get("src") or featured.get("data-src")
            if src:
                images.append(self.absolute_url(src))

        # thumbnailUrl from JSON-LD
        if not images and json_ld.get("thumbnailUrl"):
            images.append(json_ld["thumbnailUrl"])

        # 正文图片
        for img in soup.select(".post-content img"):
            src = img.get("data-orig-src") or img.get("src") or img.get("data-src")
            if src and not src.endswith(".svg") and "data:image" not in src:
                full_src = self.absolute_url(src)
                if full_src not in images:
                    images.append(full_src)

        return Article(
            url=url,
            title=title,
            content=content,
            author=author or "Elite Havens",
            publish_date=publish_date,
            category=category,
            tags=tags,
            images=images[:10],
            language="en",
            country="",  # 跨区域网站，由 detect_location_from_title 自动识别
            city="",
        )
