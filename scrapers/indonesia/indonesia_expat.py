# -*- coding: utf-8 -*-
"""
Indonesia Expat 爬虫 (Sitemap 模式)
https://indonesiaexpat.id/

印尼外籍人士社区网站，提供餐厅、生活方式等资讯
只爬取 /lifestyle/food-drink/ 分类的文章

使用 Sitemap 获取文章列表
Sitemap Index: https://indonesiaexpat.id/sitemap_index.xml
文章 Sitemap: /post-sitemap1~11.xml (Yoast SEO)
"""
import json
from typing import List, Optional, Generator, Tuple
from xml.etree import ElementTree

from base_scraper import BaseScraper, Article
from config import SITE_CONFIGS


class IndonesiaExpatScraper(BaseScraper):
    """
    Indonesia Expat 爬虫 (Sitemap 模式)

    WordPress + Yoast SEO + Penci 主题
    - 多个分页 sitemap (post-sitemap1~11.xml)
    - 日期从 <time datetime="..."> 获取
    - 内容在 div.penci-entry-content.entry-content

    URL模式:
    - Sitemap Index: /sitemap_index.xml
    - 文章 Sitemap: /post-sitemap{N}.xml
    - Food-drink 文章: /lifestyle/food-drink/{slug}/
    """

    CONFIG_KEY = "indonesia_expat"

    def __init__(self, use_proxy: bool = False):
        config = SITE_CONFIGS.get(self.CONFIG_KEY, {})
        super().__init__(
            name=config.get("name", "Indonesia Expat"),
            base_url=config.get("base_url", "https://indonesiaexpat.id"),
            delay=config.get("delay", 0.5),
            use_proxy=use_proxy,
            country=config.get("country", "Indonesia"),
            city=config.get("city", ""),
        )
        self.sitemap_index_url = f"{self.base_url}/sitemap_index.xml"
        self._article_urls_cache = None

    def _get_post_sitemap_urls(self) -> List[str]:
        """
        从 sitemap index 获取所有 post-sitemap URL

        Returns:
            post-sitemap URL 列表
        """
        sitemap_urls = []
        try:
            proxies = self._get_proxy()
            resp = self.session.get(self.sitemap_index_url, timeout=30, proxies=proxies)
            resp.raise_for_status()

            root = ElementTree.fromstring(resp.content)
            ns = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}

            for sitemap in root.findall('.//sm:sitemap', ns):
                loc = sitemap.find('sm:loc', ns)
                if loc is not None and 'post-sitemap' in loc.text:
                    sitemap_urls.append(loc.text)

            self.logger.info(f"Sitemap Index: 找到 {len(sitemap_urls)} 个 post-sitemap")

        except Exception as e:
            self.logger.error(f"获取 sitemap index 失败: {e}")

        return sitemap_urls

    def fetch_urls_from_sitemap(self) -> List[Tuple[str, str]]:
        """
        从多个 Sitemap 获取文章URL

        Returns:
            [(url, lastmod), ...] 按 lastmod 倒序排列
        """
        if self._article_urls_cache is not None:
            return self._article_urls_cache

        url_with_dates = []
        sitemap_urls = self._get_post_sitemap_urls()

        for sitemap_url in sitemap_urls:
            try:
                proxies = self._get_proxy()
                resp = self.session.get(sitemap_url, timeout=30, proxies=proxies)
                resp.raise_for_status()

                root = ElementTree.fromstring(resp.content)
                ns = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}

                count = 0
                for url_elem in root.findall('.//sm:url', ns):
                    loc = url_elem.find('sm:loc', ns)
                    lastmod = url_elem.find('sm:lastmod', ns)

                    if loc is not None:
                        url = loc.text
                        mod_date = lastmod.text if lastmod is not None else ""

                        if url and self.is_valid_article_url(url):
                            url_with_dates.append((url, mod_date))
                            count += 1

                self.logger.info(f"{sitemap_url}: 获取 {count} 篇 food-drink 文章")

            except Exception as e:
                self.logger.warning(f"获取 {sitemap_url} 失败: {e}")
                continue

        self.logger.info(f"Sitemap 总计: 获取 {len(url_with_dates)} 篇 food-drink 文章")

        # 按 lastmod 倒序排列
        url_with_dates.sort(key=lambda x: x[1] if x[1] else "", reverse=True)
        self._article_urls_cache = url_with_dates
        return url_with_dates

    def get_article_list_urls(self) -> Generator[str, None, None]:
        """生成列表页URL - 使用特殊标记"""
        yield "sitemap://indonesia-expat"

    def is_valid_article_url(self, url: str) -> bool:
        """
        检查是否为有效的 food-drink 文章URL

        只抓取 /lifestyle/food-drink/ 分类的文章
        """
        if not url or "indonesiaexpat.id" not in url:
            return False

        # 只要 /lifestyle/food-drink/ 分类
        if "/lifestyle/food-drink/" not in url.lower():
            return False

        # 排除非文章页
        exclude_patterns = [
            "/wp-admin/", "/wp-content/", "/wp-includes/",
            "/tag/", "/category/", "/author/", "/page/",
            "/search/", "/attachment/", "/feed/",
        ]
        url_lower = url.lower()
        if any(p in url_lower for p in exclude_patterns):
            return False

        return True

    def parse_article_list(self, html: str, list_url: str) -> List[str]:
        """解析文章列表页 - sitemap 模式不使用"""
        return []

    def extract_content(self, html: str) -> str:
        """
        从原始 HTML 提取正文内容

        Indonesia Expat 用 Penci 主题
        内容选择器: div.penci-entry-content.entry-content
        """
        soup = self.parse_html(html)

        content_selectors = [
            "div.penci-entry-content.entry-content",
            "div.entry-content",
            ".penci-entry-content",
            "article .entry-content",
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
                # 移除相关文章、分享按钮等
                for css_sel in [
                    ".penci-post-related", ".penci-social-share",
                    ".penci-entry-footer", ".penci-tags-links",
                    ".share-buttons", ".related-posts",
                    ".fb-comments", ".penci-facebook-comments",
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
                    if item.get("@type") in ["WebPage", "Article", "BlogPosting", "NewsArticle"]:
                        if item.get("datePublished"):
                            result["datePublished"] = item["datePublished"]
                        if item.get("dateModified"):
                            result["dateModified"] = item["dateModified"]
                        if "author" in item:
                            author = item["author"]
                            if isinstance(author, dict):
                                result["author"] = author.get("name", "")
                            elif isinstance(author, str):
                                result["author"] = author

                    # Yoast SEO 的特殊格式：通过 @graph 嵌套
                    if "@graph" in item:
                        for graph_item in item["@graph"]:
                            if graph_item.get("@type") in ["WebPage", "Article", "BlogPosting", "NewsArticle"]:
                                if graph_item.get("datePublished"):
                                    result["datePublished"] = graph_item["datePublished"]
                                if graph_item.get("dateModified"):
                                    result["dateModified"] = graph_item["dateModified"]
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

        # 标题
        title = ""
        title_selectors = [
            "h1.entry-title",
            "h1.penci-entry-title",
            ".entry-header h1",
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
                ".author.vcard a",
                ".entry-meta .author a",
                "a[rel='author']",
                ".byline a",
            ]
            for selector in author_selectors:
                author_el = soup.select_one(selector)
                if author_el:
                    author = self.clean_text(author_el.get_text())
                    if author:
                        break

        # 发布日期 - 优先 JSON-LD，其次 time 元素
        publish_date = json_ld.get("datePublished", "")
        if not publish_date:
            date_selectors = [
                "time.entry-date[datetime]",
                "time[datetime]",
                ".entry-date",
                "meta[property='article:published_time']",
            ]
            for selector in date_selectors:
                date_el = soup.select_one(selector)
                if date_el:
                    publish_date = date_el.get("datetime") or date_el.get("content") or self.clean_text(date_el.get_text())
                    if publish_date:
                        break

        # 分类
        category = "Food & Drink"  # 我们只爬 food-drink 分类
        cat_selectors = [
            ".penci-cat-links a",
            ".entry-categories a",
            "a[href*='/lifestyle/food-drink/']",
        ]
        for selector in cat_selectors:
            cat_el = soup.select_one(selector)
            if cat_el:
                cat_text = self.clean_text(cat_el.get_text())
                if cat_text and "food" in cat_text.lower():
                    category = cat_text
                    break

        # 标签
        tags = []
        for tag_el in soup.select(".penci-tags-links a, .tags-links a, a[rel='tag']"):
            tag = self.clean_text(tag_el.get_text())
            if tag and tag not in tags:
                tags.append(tag)

        # 图片
        images = []
        # 特色图 (文章顶部大图)
        featured = soup.select_one(".post-image img, .penci-standard-format img, .entry-media img")
        if featured:
            src = featured.get("src") or featured.get("data-src")
            if src and not src.endswith(".svg"):
                images.append(self.absolute_url(src))

        # 内容图片
        content_el = soup.select_one("div.penci-entry-content.entry-content, div.entry-content")
        if content_el:
            for img in content_el.select("img"):
                src = img.get("src") or img.get("data-src") or img.get("data-lazy-src")
                if src and not src.endswith(".svg") and "data:image" not in src:
                    full_src = self.absolute_url(src)
                    if full_src not in images:
                        images.append(full_src)

        return Article(
            url=url,
            title=title,
            content=content,
            author=author or "Indonesia Expat",
            publish_date=publish_date,
            category=category,
            tags=tags,
            images=images[:10],
            language="en",
        )
