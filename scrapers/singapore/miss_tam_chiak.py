# -*- coding: utf-8 -*-
"""
Miss Tam Chiak 爬虫 (Sitemap 模式)
https://www.misstamchiak.com/
新加坡顶级美食博客
"""
import json
from typing import List, Optional, Generator
from xml.etree import ElementTree as ET

from base_scraper import BaseScraper, Article
from config import SITE_CONFIGS


class MissTamChiakScraper(BaseScraper):
    """
    Miss Tam Chiak 爬虫

    Gatsby 静态站点 + Yoast SEO JSON-LD

    特性:
    - 新加坡顶级美食博客
    - 餐厅评测、小贩中心、美食推荐
    - 英语内容
    - JSON-LD @graph 格式元数据
    - 注意: sitemap 中 URL 域名为 uat.misstamchiak.com，需替换为 www
    """

    CONFIG_KEY = "miss_tam_chiak"

    def __init__(self, use_proxy: bool = False):
        config = SITE_CONFIGS.get(self.CONFIG_KEY, {})

        super().__init__(
            name=config.get("name", "Miss Tam Chiak"),
            base_url=config.get("base_url", "https://www.misstamchiak.com"),
            delay=config.get("delay", 0.5),
            use_proxy=use_proxy,
            country=config.get("country", "Singapore"),
            city=config.get("city", "Singapore"),
        )

    def get_article_list_urls(self) -> Generator[str, None, None]:
        """返回 sitemap 标记，表示使用 sitemap 模式"""
        yield "sitemap://"

    def parse_article_list(self, html: str, list_url: str) -> List[str]:
        """sitemap 模式不使用此方法"""
        return []

    def fetch_urls_from_sitemap(self) -> List[tuple]:
        """
        从 sitemap-0.xml 获取文章 URL

        注意: sitemap 中 URL 使用 uat.misstamchiak.com，需替换为 www.misstamchiak.com
        """
        all_urls = []
        ns = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}

        sitemap_url = f"{self.base_url}/sitemap-0.xml"
        response = self.fetch(sitemap_url)
        if not response:
            self.logger.error(f"获取 sitemap 失败: {sitemap_url}")
            return all_urls

        try:
            root = ET.fromstring(response.text)
            for url_el in root.findall(".//ns:url", ns):
                loc = url_el.find("ns:loc", ns)

                if loc is not None and loc.text:
                    url = loc.text.strip()
                    # 替换 UAT 域名为生产域名
                    url = url.replace("uat.misstamchiak.com", "www.misstamchiak.com")

                    if self.is_valid_article_url(url):
                        # sitemap 没有 lastmod，传空字符串
                        all_urls.append((url, ""))

        except ET.ParseError as e:
            self.logger.error(f"解析 sitemap 失败: {e}")

        self.logger.info(f"从 Sitemap 获取到 {len(all_urls)} 篇文章")
        return all_urls

    def is_valid_article_url(self, url: str) -> bool:
        """检查是否为有效的文章 URL"""
        if not url or "misstamchiak.com" not in url.lower():
            return False

        # 排除非文章 URL
        exclude_patterns = [
            "/category/", "/tag/", "/author/", "/page/",
            "/about", "/contact", "/privacy", "/terms",
            "/advertise", "/work-with-us", "/deals",
            "/wp-admin/", "/wp-content/", "/wp-json/",
            ".jpg", ".png", ".gif", ".pdf",
        ]
        url_lower = url.lower()
        if any(p in url_lower for p in exclude_patterns):
            return False

        # URL 应该是 /article-slug/ 格式
        from urllib.parse import urlparse
        parsed = urlparse(url)
        path = parsed.path.strip("/")

        # 排除根路径和过短的路径
        if not path or len(path) < 3:
            return False

        # 排除纯数字路径
        if path.replace("-", "").isdigit():
            return False

        return True

    def _parse_json_ld(self, soup) -> dict:
        """
        解析 JSON-LD 结构化数据 (Yoast @graph 格式)

        返回:
            {
                "headline": str,
                "author": str,
                "datePublished": str,
                "articleSection": list,
                "keywords": list,
                "thumbnailUrl": str,
            }
        """
        result = {}
        for script in soup.select('script[type="application/ld+json"]'):
            try:
                data = json.loads(script.string or "")
                items = data if isinstance(data, list) else [data]

                for item in items:
                    if "@graph" in item:
                        for graph_item in item["@graph"]:
                            item_type = graph_item.get("@type")

                            if item_type == "Article":
                                if graph_item.get("headline"):
                                    result["headline"] = graph_item["headline"]
                                if graph_item.get("datePublished"):
                                    result["datePublished"] = graph_item["datePublished"]
                                if graph_item.get("articleSection"):
                                    result["articleSection"] = graph_item["articleSection"]
                                if graph_item.get("keywords"):
                                    result["keywords"] = graph_item["keywords"]
                                if graph_item.get("thumbnailUrl"):
                                    result["thumbnailUrl"] = graph_item["thumbnailUrl"]

                                # 作者可能是对象或字符串
                                author = graph_item.get("author")
                                if isinstance(author, dict):
                                    result["author"] = author.get("name", "")
                                elif isinstance(author, str):
                                    result["author"] = author

            except (json.JSONDecodeError, TypeError, KeyError):
                continue
        return result

    def extract_content(self, html: str) -> str:
        """提取正文内容（保留 HTML 结构）"""
        soup = self.parse_html(html)

        # Gatsby 站点内容在 main 元素中
        content_el = soup.select_one("main")
        if content_el:
            # 移除无用元素
            for tag in content_el.find_all([
                "script", "style", "nav", "aside", "iframe",
                "noscript", "header", "footer"
            ]):
                tag.decompose()

            # 移除常见的非正文元素
            for css_sel in [
                ".share", ".social", ".ad", ".advertisement",
                ".related", ".newsletter", ".author-box",
                ".sidebar", ".widget", ".comments"
            ]:
                for el in content_el.select(css_sel):
                    el.decompose()

            content = content_el.decode_contents()
            if len(content) > 200:
                return content

        return ""

    def parse_article(self, html: str, url: str) -> Optional[Article]:
        """解析文章页面"""
        soup = self.parse_html(html)
        json_ld = self._parse_json_ld(soup)

        # 标题: 优先 JSON-LD，备用 h1.title
        title = json_ld.get("headline", "")
        if not title:
            title_el = soup.select_one("h1.title, h1")
            if title_el:
                title = self.clean_text(title_el.get_text())

        if not title:
            return None

        # 内容
        content = self.extract_content(html)

        # 作者: 优先 JSON-LD
        author = json_ld.get("author", "")
        if not author:
            author_el = soup.select_one(".author-name, .author, .byline")
            if author_el:
                author = self.clean_text(author_el.get_text())

        # 发布日期: 优先 JSON-LD
        publish_date = json_ld.get("datePublished", "")
        if not publish_date:
            date_el = soup.select_one("time[datetime], time, .date")
            if date_el:
                publish_date = date_el.get("datetime") or self.clean_text(date_el.get_text())

        # 分类: 从 JSON-LD articleSection
        category = ""
        article_sections = json_ld.get("articleSection", [])
        if article_sections:
            # 取第一个非 "Blog" 的分类
            for section in article_sections:
                if section and section.lower() != "blog":
                    category = section
                    break

        # 标签: 从 JSON-LD keywords
        tags = json_ld.get("keywords", [])
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",") if t.strip()]

        # 图片
        images = []
        # 优先使用 JSON-LD 中的缩略图
        thumbnail = json_ld.get("thumbnailUrl", "")
        if thumbnail:
            images.append(thumbnail)

        # 从内容中提取图片
        for img in soup.select("main img"):
            src = img.get("src")
            if src and not src.endswith(".svg"):
                # 过滤 gravatar 头像
                if "gravatar.com" in src:
                    continue
                full_src = self.absolute_url(src)
                if full_src not in images:
                    images.append(full_src)

        return Article(
            url=url,
            title=title,
            content=content,
            author=author or "Miss Tam Chiak",
            publish_date=publish_date,
            category=category,
            tags=tags,
            images=images[:10],
            language="en",
            country=self.country,
            city=self.city,
        )
