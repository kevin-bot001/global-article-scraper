# -*- coding: utf-8 -*-
"""
The Urban List Singapore 爬虫 (Sitemap 模式)
https://www.theurbanlist.com/singapore
澳洲起源的城市生活方式指南，新加坡版本
"""
from typing import List, Optional, Generator
from xml.etree import ElementTree as ET

from base_scraper import BaseScraper, Article
from config import SITE_CONFIGS


class UrbanListSGScraper(BaseScraper):
    """
    The Urban List Singapore 爬虫

    特性:
    - 城市生活方式指南（餐厅、酒吧、活动）
    - 使用分页式 sitemap (alist-sitemap-entries/P0, P100, P200)
    - 文章 URL 格式: /singapore/a-list/{slug}
    - 英语内容
    - 只爬取 Singapore 版本
    """

    CONFIG_KEY = "urban_list_sg"

    def __init__(self, use_proxy: bool = False):
        config = SITE_CONFIGS.get(self.CONFIG_KEY, {})

        super().__init__(
            name=config.get("name", "The Urban List SG"),
            base_url="https://www.theurbanlist.com/singapore",
            delay=config.get("delay", 0.5),
            use_proxy=use_proxy,
            country="Singapore",
            city="Singapore",
        )

    def get_article_list_urls(self) -> Generator[str, None, None]:
        yield "sitemap://"

    def parse_article_list(self, html: str, list_url: str) -> List[str]:
        return []

    def fetch_urls_from_sitemap(self) -> List[tuple]:
        """从 sitemap index 获取所有文章 URL"""
        all_urls = []
        ns = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}

        # 获取 sitemap index
        index_url = f"{self.base_url}/sitemap"
        response = self.fetch(index_url)
        if not response:
            return all_urls

        # 解析 sitemap index，获取所有 alist-sitemap-entries
        sitemap_urls = []
        try:
            root = ET.fromstring(response.text)
            for sitemap_el in root.findall(".//ns:sitemap", ns):
                loc = sitemap_el.find("ns:loc", ns)
                if loc is not None and loc.text and "alist-sitemap-entries" in loc.text:
                    sitemap_urls.append(loc.text.strip())
        except ET.ParseError as e:
            self.logger.error(f"解析 sitemap index 失败: {e}")
            return all_urls

        self.logger.info(f"发现 {len(sitemap_urls)} 个子 sitemap")

        # 获取每个子 sitemap 的文章
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
        """验证是否为有效的 Singapore 文章 URL"""
        if not url:
            return False

        # 必须是 Singapore 的 a-list 文章
        if "/singapore/a-list/" not in url.lower():
            return False

        # 排除非文章页面
        exclude_patterns = [
            "/category/", "/tag/", "/author/", "/page/",
            "/about", "/contact", "/privacy", "/terms",
            "/best-of/",  # 排除分类聚合页
        ]
        url_lower = url.lower()
        if any(p in url_lower for p in exclude_patterns):
            return False

        return True

    def extract_content(self, html: str) -> str:
        """提取正文内容"""
        soup = self.parse_html(html)

        content_el = soup.select_one(".editable-content")
        if content_el:
            # 移除无用元素
            for tag in content_el.find_all(["script", "style", "nav", "aside", "iframe", "noscript"]):
                tag.decompose()
            # 移除广告、分享等元素
            for css_sel in [".share", ".social", ".ad", ".related", ".newsletter", ".SponsorshipNotice"]:
                for el in content_el.select(css_sel):
                    el.decompose()

            content = content_el.decode_contents()
            if len(content) > 200:
                return content

        return ""

    def parse_article(self, html: str, url: str) -> Optional[Article]:
        """解析文章详情页"""
        soup = self.parse_html(html)

        # 标题
        title = ""
        title_el = soup.select_one("h1.EntryDetailArticle-title")
        if title_el:
            title = self.clean_text(title_el.get_text())

        if not title:
            # Fallback: 尝试 og:title
            og_title = soup.select_one('meta[property="og:title"]')
            if og_title:
                title = og_title.get("content", "")

        if not title:
            return None

        # 正文
        content = self.extract_content(html)

        # 日期 (格式: "6th Feb 2026")
        publish_date = ""
        meta_el = soup.select_one(".EntryDetailArticle-meta")
        if meta_el:
            date_div = meta_el.find("div")
            if date_div:
                publish_date = self.clean_text(date_div.get_text())

        # 作者
        author = ""
        author_els = soup.select(".Author a")
        if author_els:
            authors = [self.clean_text(a.get_text()) for a in author_els[:2]]
            author = ", ".join(authors)

        # 分类
        category = ""
        cat_el = soup.select_one(".EntryDetailArticle-eyebrow a")
        if cat_el:
            category = self.clean_text(cat_el.get_text())

        # 图片
        images = []
        # 首先获取 splide 轮播图
        for img in soup.select(".splide img"):
            src = img.get("src") or img.get("data-src")
            if src and "imgix.theurbanlist.com" in src:
                images.append(src.split("?")[0])  # 移除查询参数

        # 然后获取正文中的图片
        for img in soup.select(".editable-content img"):
            src = img.get("src") or img.get("data-src")
            if src and src not in images:
                images.append(self.absolute_url(src))

        return Article(
            url=url,
            title=title,
            content=content,
            author=author or "The Urban List",
            publish_date=publish_date,
            category=category,
            tags=[],
            images=images[:10],
            language="en",
            country=self.country,
            city=self.city,
        )
