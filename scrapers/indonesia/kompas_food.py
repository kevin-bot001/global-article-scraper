# -*- coding: utf-8 -*-
"""
Kompas Food 爬虫 (Sitemap 模式)
https://www.kompas.com/food/
印尼最大新闻门户的美食频道
"""
import json
from typing import List, Optional, Generator
from xml.etree import ElementTree as ET

from base_scraper import BaseScraper, Article
from config import SITE_CONFIGS


class KompasFoodScraper(BaseScraper):
    """
    Kompas Food 爬虫

    新闻 Sitemap 格式 (Google News)
    Sitemap: sitemap-news-food.xml

    特性:
    - 印尼最大新闻门户
    - 美食新闻和食谱
    - 印尼语内容
    - 新闻格式 sitemap (news:news)
    """

    CONFIG_KEY = "kompas_food"

    def __init__(self, use_proxy: bool = False):
        config = SITE_CONFIGS.get(self.CONFIG_KEY, {})

        super().__init__(
            name=config.get("name", "Kompas Food"),
            base_url=config.get("base_url", "https://www.kompas.com"),
            delay=config.get("delay", 0.5),
            use_proxy=use_proxy,
            country=config.get("country", "Indonesia"),
            city=config.get("city", ""),
        )

    def get_article_list_urls(self) -> Generator[str, None, None]:
        yield "sitemap://"

    def parse_article_list(self, html: str, list_url: str) -> List[str]:
        return []

    def fetch_urls_from_sitemap(self) -> List[tuple]:
        """从新闻格式 Sitemap 获取文章URL"""
        sitemap_url = f"{self.base_url}/sitemap-news-food.xml"

        all_urls = []
        ns = {
            "ns": "http://www.sitemaps.org/schemas/sitemap/0.9",
            "news": "http://www.google.com/schemas/sitemap-news/0.9",
        }

        response = self.fetch(sitemap_url)
        if not response:
            return all_urls

        try:
            root = ET.fromstring(response.text)
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
                    if self.is_valid_article_url(url):
                        all_urls.append((url, pub_date))

        except ET.ParseError as e:
            self.logger.error(f"解析 sitemap 失败: {sitemap_url} - {e}")

        self.logger.info(f"从 Sitemap 获取到 {len(all_urls)} 篇文章")
        return all_urls

    def is_valid_article_url(self, url: str) -> bool:
        if not url or "kompas.com/food/read" not in url:
            return False

        exclude_patterns = [
            "/tag/", "/author/", "/search/",
            "/photo/", "/video/",
        ]
        url_lower = url.lower()
        if any(p in url_lower for p in exclude_patterns):
            return False

        return True

    def _parse_json_ld(self, soup) -> dict:
        result = {}
        for script in soup.select('script[type="application/ld+json"]'):
            try:
                data = json.loads(script.string or "")
                items = data if isinstance(data, list) else [data]

                for item in items:
                    if item.get("@type") in ["NewsArticle", "Article"]:
                        if item.get("datePublished"):
                            result["datePublished"] = item["datePublished"]
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
        soup = self.parse_html(html)

        # Kompas 特有选择器
        for selector in [".read__content", ".artikel", ".content__body", "article"]:
            content_el = soup.select_one(selector)
            if content_el:
                for tag in content_el.find_all(["script", "style", "nav", "aside", "iframe"]):
                    tag.decompose()
                for css_sel in [".share", ".social", ".ad", ".related", ".baca-juga"]:
                    for el in content_el.select(css_sel):
                        el.decompose()
                content = content_el.decode_contents()
                if len(content) > 200:
                    return content
        return ""

    def parse_article(self, html: str, url: str) -> Optional[Article]:
        soup = self.parse_html(html)
        json_ld = self._parse_json_ld(soup)

        title = json_ld.get("headline", "")
        if not title:
            title_el = soup.select_one("h1.read__title, h1")
            if title_el:
                title = self.clean_text(title_el.get_text())

        if not title:
            return None

        content = self.extract_content(html)
        author = json_ld.get("author", "")
        publish_date = json_ld.get("datePublished", "")

        if not author:
            author_el = soup.select_one(".read__author, .credit-title-name")
            if author_el:
                author = self.clean_text(author_el.get_text())

        if not publish_date:
            date_el = soup.select_one(".read__time, time[datetime]")
            if date_el:
                publish_date = date_el.get("datetime") or self.clean_text(date_el.get_text())

        # 分类
        category = ""
        cat_el = soup.select_one(".read__channel, .breadcrumb a")
        if cat_el:
            category = self.clean_text(cat_el.get_text())

        # 标签
        tags = []
        for tag_el in soup.select(".tag__article a, .article__tag a"):
            tag = self.clean_text(tag_el.get_text())
            if tag and tag not in tags:
                tags.append(tag)

        # 图片
        images = []
        featured = soup.select_one(".photo__wrap img, .read__photo img")
        if featured:
            src = featured.get("src") or featured.get("data-src")
            if src:
                images.append(self.absolute_url(src))

        for img in soup.select(".read__content img"):
            src = img.get("src") or img.get("data-src")
            if src and not src.endswith(".svg"):
                full_src = self.absolute_url(src)
                if full_src not in images:
                    images.append(full_src)

        return Article(
            url=url,
            title=title,
            content=content,
            author=author or "Kompas Food",
            publish_date=publish_date,
            category=category,
            tags=tags,
            images=images[:10],
            language="id",
            country="Indonesia",
            city=self.city,
        )
