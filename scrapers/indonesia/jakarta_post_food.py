# -*- coding: utf-8 -*-
"""
Jakarta Post Food 爬虫 (Sitemap 模式)
https://www.thejakartapost.com/culture/food

印尼最大英文报纸的美食频道
"""
import json
import re
from typing import List, Optional, Generator
from xml.etree import ElementTree as ET

from base_scraper import BaseScraper, Article
from config import SITE_CONFIGS


class JakartaPostFoodScraper(BaseScraper):
    """
    Jakarta Post Food 爬虫

    新闻 Sitemap 格式 (Google News)
    Sitemap:
    - https://www.thejakartapost.com/culture/food/news/sitemap.xml
    - https://www.thejakartapost.com/culture/food/web/sitemap.xml

    特性:
    - 印尼最大英文报纸
    - 美食餐厅评测文章
    - 英语内容
    - News sitemap 格式，CDATA 包裹
    """

    CONFIG_KEY = "jakarta_post_food"

    def __init__(self, use_proxy: bool = False):
        config = SITE_CONFIGS.get(self.CONFIG_KEY, {})

        super().__init__(
            name=config.get("name", "Jakarta Post Food"),
            base_url=config.get("base_url", "https://www.thejakartapost.com"),
            delay=config.get("delay", 0.5),
            use_proxy=use_proxy,
            country=config.get("country", "Indonesia"),
            city=config.get("city", "Jakarta"),
        )

    def get_article_list_urls(self) -> Generator[str, None, None]:
        yield "sitemap://"

    def parse_article_list(self, html: str, list_url: str) -> List[str]:
        return []

    def fetch_urls_from_sitemap(self) -> List[tuple]:
        """从新闻格式 Sitemap 获取文章URL (CDATA 格式)"""
        # 两个 sitemap：news 包含发布时间，web 是简化版
        sitemap_urls = [
            f"{self.base_url}/culture/food/news/sitemap.xml",
            f"{self.base_url}/culture/food/web/sitemap.xml",
        ]

        all_urls = []
        seen_urls = set()

        ns = {
            "ns": "http://www.sitemaps.org/schemas/sitemap/0.9",
            "news": "http://www.google.com/schemas/sitemap-news/0.9",
        }

        for sitemap_url in sitemap_urls:
            response = self.fetch(sitemap_url)
            if not response:
                continue

            try:
                # 处理 CDATA：先清理 CDATA 标签
                xml_content = response.text
                # 移除 CDATA 包裹（如果有）
                xml_content = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', xml_content, flags=re.DOTALL)

                root = ET.fromstring(xml_content)

                for url_el in root.findall(".//ns:url", ns):
                    loc = url_el.find("ns:loc", ns)

                    # 从 news:news 提取发布时间
                    news_el = url_el.find("news:news", ns)
                    pub_date = ""
                    if news_el is not None:
                        pub_date_el = news_el.find("news:publication_date", ns)
                        if pub_date_el is not None and pub_date_el.text:
                            pub_date = pub_date_el.text.strip()

                    if loc is not None and loc.text:
                        url = loc.text.strip()
                        if url not in seen_urls and self.is_valid_article_url(url):
                            seen_urls.add(url)
                            all_urls.append((url, pub_date))

            except ET.ParseError as e:
                self.logger.error(f"解析 sitemap 失败: {sitemap_url} - {e}")

        self.logger.info(f"从 Sitemap 获取到 {len(all_urls)} 篇文章")
        return all_urls

    def is_valid_article_url(self, url: str) -> bool:
        """检查是否为有效的文章URL"""
        if not url:
            return False

        # 必须是 thejakartapost.com/culture/ 下的文章
        if "thejakartapost.com/culture/" not in url:
            return False

        # 必须以 .html 结尾
        if not url.endswith(".html"):
            return False

        # 排除非文章URL
        exclude_patterns = [
            "/tag/", "/author/", "/search/",
            "/photo/", "/video/", "/page/",
        ]
        url_lower = url.lower()
        if any(p in url_lower for p in exclude_patterns):
            return False

        return True

    def _parse_json_ld(self, soup) -> dict:
        """解析 JSON-LD 结构化数据"""
        result = {}
        for script in soup.select('script[type="application/ld+json"]'):
            try:
                data = json.loads(script.string or "")
                items = data if isinstance(data, list) else [data]

                for item in items:
                    if item.get("@type") in ["NewsArticle", "Article"]:
                        if item.get("datePublished"):
                            result["datePublished"] = item["datePublished"]
                        if item.get("dateModified"):
                            result["dateModified"] = item["dateModified"]
                        if item.get("headline"):
                            result["headline"] = item["headline"]
                        if "author" in item:
                            author = item["author"]
                            if isinstance(author, dict):
                                result["author"] = author.get("name", "")
                            elif isinstance(author, list) and author:
                                result["author"] = author[0].get("name", "") if isinstance(author[0], dict) else str(author[0])

            except (json.JSONDecodeError, TypeError, KeyError):
                continue
        return result

    def extract_content(self, html: str) -> str:
        """提取文章正文内容"""
        soup = self.parse_html(html)

        # Jakarta Post 特有选择器
        for selector in [".tjp-single__content", ".article-content", "article"]:
            content_el = soup.select_one(selector)
            if content_el:
                # 移除无用元素
                for tag in content_el.find_all(["script", "style", "nav", "aside", "iframe", "noscript"]):
                    tag.decompose()
                # 移除广告、分享、相关文章等
                for css_sel in [
                    ".share", ".social", ".ad", ".related",
                    ".tjp-sticky-popup", ".tjp-payment", ".jpx-widget",
                    ".tjp-single__content-list", ".tjp-single__content-ads",
                ]:
                    for el in content_el.select(css_sel):
                        el.decompose()

                content = content_el.decode_contents()
                if len(content) > 200:
                    return content
        return ""

    def parse_article(self, html: str, url: str) -> Optional[Article]:
        """解析文章"""
        soup = self.parse_html(html)
        json_ld = self._parse_json_ld(soup)

        # 标题 - 优先从 JSON-LD 获取
        title = json_ld.get("headline", "")
        if not title:
            # 从 meta 标签获取
            og_title = soup.select_one('meta[property="og:title"]')
            if og_title:
                title = og_title.get("content", "")
                # 清理标题后缀
                title = re.sub(r'\s*-\s*Food\s*-\s*The Jakarta Post$', '', title)
        if not title:
            title_el = soup.select_one("h1")
            if title_el:
                title = self.clean_text(title_el.get_text())

        if not title:
            return None

        # 正文内容
        content = self.extract_content(html)

        # 作者
        author = json_ld.get("author", "")
        if not author:
            author_meta = soup.select_one('meta[name="author"]')
            if author_meta:
                author = author_meta.get("content", "")

        # 发布日期
        publish_date = json_ld.get("datePublished", "")
        if not publish_date:
            date_meta = soup.select_one('meta[name="datePublished"]')
            if date_meta:
                publish_date = date_meta.get("content", "")
        if not publish_date:
            published_meta = soup.select_one('meta[name="published-at"]')
            if published_meta:
                publish_date = published_meta.get("content", "")

        # 分类 - 从 meta 标签获取
        category = ""
        channel_meta = soup.select_one('meta[name="tjp-sub-channel-name"]')
        if channel_meta:
            category = channel_meta.get("content", "").capitalize()

        # 标签 - 从 meta keywords 获取
        tags = []
        keywords_meta = soup.select_one('meta[name="keywords"]')
        if keywords_meta:
            keywords = keywords_meta.get("content", "")
            if keywords:
                tags = [t.strip() for t in keywords.split(",") if t.strip()]

        # 图片
        images = []
        og_image = soup.select_one('meta[property="og:image"]')
        if og_image:
            src = og_image.get("content", "")
            if src:
                images.append(src)

        # 从正文中提取更多图片
        content_el = soup.select_one(".tjp-single__content")
        if content_el:
            for img in content_el.select("img"):
                src = img.get("src") or img.get("data-src")
                if src and not src.endswith(".svg") and src not in images:
                    images.append(self.absolute_url(src))

        # 摘要/描述
        description = ""
        og_desc = soup.select_one('meta[property="og:description"]')
        if og_desc:
            description = og_desc.get("content", "")

        return Article(
            url=url,
            title=title,
            content=content,
            author=author or "The Jakarta Post",
            publish_date=publish_date,
            category=category or "Food",
            tags=tags,
            images=images[:10],
            language="en",  # Jakarta Post 是英文报纸
            country="Indonesia",
            city=self.city,
        )
