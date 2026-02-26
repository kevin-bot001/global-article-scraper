# -*- coding: utf-8 -*-
"""
Food Fun Travel 爬虫 (Sitemap 模式)
https://foodfuntravel.com/
跨区域美食旅行博客，涵盖巴厘岛、欧洲、东南亚等地区的餐厅推荐和旅行指南
"""
import json
from typing import List, Optional, Generator
from xml.etree import ElementTree as ET

from base_scraper import BaseScraper, Article
from config import SITE_CONFIGS


class FoodFunTravelScraper(BaseScraper):
    """
    Food Fun Travel 爬虫

    WordPress + Yoast SEO + SASWP (Schema & Structured Data for WP)
    Sitemap: post-sitemap.xml

    特性:
    - 跨区域美食旅行博客
    - 覆盖巴厘岛、格鲁吉亚、意大利、泰国、墨西哥等
    - 英语内容
    - JSON-LD 使用 SASWP 插件 (数组格式而非 @graph)
    - 图片懒加载 (data-src)
    """

    CONFIG_KEY = "food_fun_travel"

    def __init__(self, use_proxy: bool = False):
        config = SITE_CONFIGS.get(self.CONFIG_KEY, {})

        super().__init__(
            name=config.get("name", "Food Fun Travel"),
            base_url=config.get("base_url", "https://foodfuntravel.com"),
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
        sitemap_url = f"{self.base_url}/post-sitemap.xml"

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
        if not url or "foodfuntravel.com" not in url:
            return False

        exclude_patterns = [
            "/category/", "/tag/", "/author/", "/page/",
            "/about", "/contact", "/privacy", "/terms",
            "/disclaimer", "/advertising",
            "/wp-admin/", "/wp-content/", "/wp-includes/",
            "wp-json", "feed", "xmlrpc",
            # 非文章页面 (hub页/landing page)
            "/destinations/", "/hub-", "/news/",
            "/thedish/", "/tbilisipodcast/",
            "/food-fun-travel-shop/",
            "/subscribed", "/you-are-subscribed",
            "/eat-this/", "/links/",
            "/media-packages/", "/press-media",
            "/girlstalk", "/gttresources/", "/gttguests/",
            # 地图和资源页
            "-map-free", "-map-new", "/cantina-map",
            # ebook和下载页
            "/free-ebook", "/free-e-book", "/budget-burma",
            "/saving-to-travel", "/blog-roll/",
            # 酒店推荐页 (非文章，是聚合页)
            "/best-hotels-", "/best-places-to-stay",
            # 礼物指南
            "/world-nomads-",
            # 酒庄提交页
            "/georgian-wineries-online-project-submit/",
            # 旅游预订页
            "/1-day-wine-food-history-tour-",
            # 其他杂项
            "/house-sitters-",
            "/top-10-food-worldwide/", "/top-20-booze-experiences/",
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
        """
        从 JSON-LD 提取结构化数据

        SASWP 插件格式: 数组 [{SiteNavigationElement...}, {Article...}]
        也兼容标准 Yoast @graph 格式
        """
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
                            if item_type == "Person":
                                result["author"] = graph_item.get("name", "")

                    # SASWP 直接 Article 格式 (非 @graph)
                    item_type = item.get("@type")
                    if item_type in ("Article", "NewsArticle", "BlogPosting"):
                        if item.get("datePublished"):
                            result["datePublished"] = item["datePublished"]
                        if item.get("headline"):
                            result["headline"] = item["headline"]
                        if item.get("articleSection"):
                            sections = item["articleSection"]
                            if isinstance(sections, list) and sections:
                                result["category"] = sections[0]
                            elif isinstance(sections, str):
                                result["category"] = sections
                        if item.get("keywords"):
                            keywords = item["keywords"]
                            if isinstance(keywords, str):
                                kw_list = [k.strip() for k in keywords.split(",")]
                                result["keywords"] = [k for k in kw_list if k]
                            elif isinstance(keywords, list):
                                result["keywords"] = keywords
                        # SASWP 嵌套 author
                        author_data = item.get("author")
                        if isinstance(author_data, dict):
                            result["author"] = author_data.get("name", "")
                        elif isinstance(author_data, str):
                            result["author"] = author_data

            except (json.JSONDecodeError, TypeError, KeyError):
                continue

        return result

    def extract_content(self, html: str) -> str:
        """提取正文内容"""
        soup = self.parse_html(html)

        # Food Fun Travel 使用 .entry-content.mvt-content
        content_selectors = [
            ".entry-content.mvt-content",
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
                    ".mv-ad-box", ".mv-trellis-socials",
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
            title_el = soup.select_one("h1.entry-title, h1.article-heading, h1")
            if title_el:
                title = self.clean_text(title_el.get_text())

        if not title:
            og_title = soup.select_one("meta[property='og:title']")
            if og_title:
                title = og_title.get("content", "")
                # 移除站点名后缀
                if title and " | Food Fun Travel" in title:
                    title = title.split(" | Food Fun Travel")[0].strip()

        if not title:
            return None

        # 内容
        content = self.extract_content(html)

        # 作者
        author = json_ld.get("author", "")
        if not author:
            author_el = soup.select_one(
                ".byline a.url.fn.n, .author-name a, a[rel='author'], .byline a"
            )
            if author_el:
                author = self.clean_text(author_el.get_text())

        # 发布日期
        publish_date = json_ld.get("datePublished", "")
        if not publish_date:
            # meta 标签
            date_meta = soup.select_one("meta[property='article:published_time']")
            if date_meta:
                publish_date = date_meta.get("content", "")
        if not publish_date:
            date_el = soup.select_one("time.entry-date[datetime], time[datetime], .entry-date")
            if date_el:
                publish_date = date_el.get("datetime") or self.clean_text(date_el.get_text())

        # 分类
        category = json_ld.get("category", "")
        if not category:
            cat_el = soup.select_one(
                ".entry-category a, a[rel='category tag'], .post-category a, .cat-links a"
            )
            if cat_el:
                category = self.clean_text(cat_el.get_text())

        # 标签：优先 JSON-LD keywords
        tags = json_ld.get("keywords", [])
        if not tags:
            for tag_el in soup.select(".post-tags a, .tag-links a, a[rel='tag']"):
                tag = self.clean_text(tag_el.get_text())
                if tag and tag not in tags and tag.lower() != "tags":
                    tags.append(tag)

        # 图片
        images = []
        # 特色图片
        featured = soup.select_one(".post-thumbnail img, .featured-image img, article img")
        if featured:
            src = featured.get("data-src") or featured.get("src")
            if src and not src.startswith("data:"):
                images.append(self.absolute_url(src))

        # 正文图片 (懒加载: data-src)
        for img in soup.select(".entry-content img"):
            src = img.get("data-src") or img.get("src")
            if src and not src.startswith("data:") and not src.endswith(".svg"):
                full_src = self.absolute_url(src)
                if full_src not in images:
                    images.append(full_src)

        return Article(
            url=url,
            title=title,
            content=content,
            author=author or "Food Fun Travel",
            publish_date=publish_date,
            category=category,
            tags=tags,
            images=images[:10],
            language="en",
            country="",  # 跨区域网站，由 detect_location_from_title 自动识别
            city="",
        )
