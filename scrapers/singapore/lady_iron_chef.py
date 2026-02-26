# -*- coding: utf-8 -*-
"""
LadyIronChef 爬虫 (分页模式)
https://www.ladyironchef.com/
新加坡顶级美食博客，餐厅推荐和美食指南
"""
import re
from typing import List, Optional, Generator
from concurrent.futures import ThreadPoolExecutor, as_completed

from base_scraper import BaseScraper, Article, normalize_date
from config import SITE_CONFIGS, CONCURRENCY_CONFIG


class LadyIronChefScraper(BaseScraper):
    """
    LadyIronChef 爬虫

    从首页分页获取文章（按时间倒序）

    特性:
    - 新加坡美食博客
    - 分页按时间倒序，支持 --since 提前终止
    - Open Graph 元数据丰富
    - URL 格式: /YYYY/MM/slug/
    """

    CONFIG_KEY = "lady_iron_chef"

    # 分页 URL 模板
    ARCHIVE_URL = "https://www.ladyironchef.com/page/{page}/"
    MAX_PAGES = 560  # 安全限制

    def __init__(self, use_proxy: bool = False):
        config = SITE_CONFIGS.get(self.CONFIG_KEY, {})

        super().__init__(
            name=config.get("name", "LadyIronChef"),
            base_url=config.get("base_url", "https://www.ladyironchef.com"),
            delay=config.get("delay", 0.5),
            use_proxy=use_proxy,
            country=config.get("country", "Singapore"),
            city=config.get("city", "Singapore"),
        )

    def get_article_list_urls(self) -> Generator[str, None, None]:
        """不使用默认分页模式"""
        yield "pagination://"

    def parse_article_list(self, html: str, list_url: str) -> List[str]:
        """不使用默认分页模式"""
        return []

    def fetch_urls_from_sitemap(self) -> List[tuple]:
        """不使用 sitemap 模式，返回空让 scrape_all 走自定义逻辑"""
        return []

    def _fetch_page_urls(self, page: int) -> List[str]:
        """从分页获取文章 URL 列表"""
        if page == 1:
            url = "https://www.ladyironchef.com/"
        else:
            url = self.ARCHIVE_URL.format(page=page)

        response = self.fetch(url)
        if not response:
            return []

        soup = self.parse_html(response.text)
        urls = []

        # 文章链接在 h1.entry-title > a
        for link in soup.select("h1.entry-title a"):
            href = link.get("href", "")
            if href and self.is_valid_article_url(href):
                full_url = self.absolute_url(href)
                if full_url not in urls:
                    urls.append(full_url)

        return urls

    def scrape_all(self, limit: int = 0, since: str = None, exclude_urls: set = None) -> List[Article]:
        """
        从首页分页爬取文章

        分页按时间倒序，支持 --since 提前终止：
        - 如果当前页最后一篇文章的 publish_date < since，停止翻页

        Args:
            limit: 限制文章数量，0 表示不限制
            since: 只爬取该日期之后的文章，格式如 "2025-01-01"
            exclude_urls: 要排除的 URL 集合

        Returns:
            文章列表
        """
        self.logger.info(f"开始爬取 {self.name} (分页模式)...")
        if since:
            self.logger.info(f"启用时间过滤: since={since} (基于 publish_date，支持提前终止)")

        exclude_urls = exclude_urls or set()
        all_articles = []
        page = 1
        consecutive_old_pages = 0  # 连续老文章页计数
        max_consecutive_old = 2  # 连续 N 页都是老文章就停止

        max_workers = CONCURRENCY_CONFIG.get("max_workers", 5)

        while page <= self.MAX_PAGES:
            self.logger.info(f"正在获取第 {page} 页文章列表...")
            page_urls = self._fetch_page_urls(page)

            if not page_urls:
                self.logger.info(f"第 {page} 页无文章，停止翻页")
                break

            # 排除已爬取的 URL
            page_urls = [url for url in page_urls if url not in exclude_urls]
            if not page_urls:
                self.logger.info(f"第 {page} 页文章都已爬取过，继续下一页")
                page += 1
                continue

            self.logger.info(f"第 {page} 页获取到 {len(page_urls)} 篇文章，开始并发爬取...")

            # 并发爬取当前页的文章
            page_articles = []
            oldest_date_in_page = None

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_url = {executor.submit(self.scrape_article, url): url for url in page_urls}
                for future in as_completed(future_to_url):
                    url = future_to_url[future]
                    try:
                        article = future.result()
                        if article:
                            # 获取 publish_date 用于 since 过滤和提前终止判断
                            pub_date = normalize_date(article.publish_date) if article.publish_date else ""

                            # 更新当前页最老的日期
                            if pub_date:
                                if oldest_date_in_page is None or pub_date < oldest_date_in_page:
                                    oldest_date_in_page = pub_date

                            # since 过滤
                            if since and pub_date:
                                if pub_date < since:
                                    self.logger.debug(f"since 过滤跳过: {article.title} ({pub_date})")
                                    continue

                            page_articles.append(article)
                    except Exception as e:
                        self.logger.error(f"爬取失败 {url}: {e}")

            self.logger.info(f"第 {page} 页爬取到 {len(page_articles)} 篇有效文章")
            all_articles.extend(page_articles)

            # 检查是否达到 limit
            if limit and len(all_articles) >= limit:
                self.logger.info(f"已达到限制 {limit} 篇，停止爬取")
                all_articles = all_articles[:limit]
                break

            # 提前终止判断：如果当前页最老的文章已经比 since 还老，可能可以停止了
            if since and oldest_date_in_page:
                if oldest_date_in_page < since:
                    consecutive_old_pages += 1
                    self.logger.info(
                        f"第 {page} 页最老文章 ({oldest_date_in_page}) < since ({since})，"
                        f"连续老页 {consecutive_old_pages}/{max_consecutive_old}"
                    )
                    if consecutive_old_pages >= max_consecutive_old:
                        self.logger.info(f"连续 {max_consecutive_old} 页都是老文章，停止翻页")
                        break
                else:
                    consecutive_old_pages = 0  # 重置计数

            page += 1

        self.logger.info(f"爬取完成，共获取 {len(all_articles)} 篇文章")
        return all_articles

    def is_valid_article_url(self, url: str) -> bool:
        if not url or "ladyironchef.com" not in url:
            return False

        # 文章 URL 格式: /YYYY/MM/slug/
        if not re.search(r'/\d{4}/\d{2}/[^/]+/?$', url):
            return False

        # 排除非文章页
        exclude_patterns = [
            "/tag/", "/category/", "/author/", "/page/",
            "/about", "/contact", "/advertising", "/index",
            "/restaurants-index", "/delicious",
        ]
        url_lower = url.lower()
        if any(p in url_lower for p in exclude_patterns):
            return False

        return True

    def extract_content(self, html: str) -> str:
        soup = self.parse_html(html)

        # LadyIronChef 正文在 .entry-content
        content_el = soup.select_one(".entry-content")
        if content_el:
            # 移除无用元素
            for tag in content_el.find_all(["script", "style", "nav", "aside", "iframe"]):
                tag.decompose()
            # 移除分享按钮和广告
            for css_sel in [".share", ".social", ".ad", ".related", ".no-break", "[class*='st_']"]:
                for el in content_el.select(css_sel):
                    el.decompose()
            content = content_el.decode_contents()
            if len(content) > 200:
                return content
        return ""

    def parse_article(self, html: str, url: str) -> Optional[Article]:
        soup = self.parse_html(html)

        # 标题 - h1.entry-title
        title = ""
        title_el = soup.select_one("h1.entry-title")
        if title_el:
            title = self.clean_text(title_el.get_text())

        if not title:
            og_title = soup.select_one("meta[property='og:title']")
            if og_title:
                title = og_title.get("content", "")

        if not title:
            return None

        content = self.extract_content(html)

        # 作者 - 从 byline 或默认为 ladyironchef
        author = ""
        author_el = soup.select_one(".author.vcard a, .byline a")
        if author_el:
            author = self.clean_text(author_el.get_text())

        # 发布日期 - 优先从 meta 标签获取
        publish_date = ""
        meta_date = soup.select_one("meta[property='article:published_time']")
        if meta_date:
            publish_date = meta_date.get("content", "")

        if not publish_date:
            time_el = soup.select_one("time.entry-date[datetime]")
            if time_el:
                publish_date = time_el.get("datetime", "")

        # 分类 - #cat-box a
        category = ""
        cat_el = soup.select_one("#cat-box a")
        if cat_el:
            category = self.clean_text(cat_el.get_text())

        # 标签 - #tag-box a
        tags = []
        for tag_el in soup.select("#tag-box a"):
            tag = self.clean_text(tag_el.get_text())
            if tag and tag not in tags:
                tags.append(tag)

        # 图片 - 从 og:image 和正文中提取
        images = []
        # 特色图从 og:image
        og_image = soup.select_one("meta[property='og:image']")
        if og_image:
            src = og_image.get("content", "")
            if src:
                images.append(src)

        # 内容图片
        for img in soup.select(".entry-content img"):
            src = img.get("src") or img.get("data-src")
            if src and not src.endswith(".svg"):
                full_src = self.absolute_url(src)
                if full_src not in images:
                    images.append(full_src)

        # 描述 - 从 og:description
        description = ""
        og_desc = soup.select_one("meta[property='og:description']")
        if og_desc:
            description = og_desc.get("content", "")

        return Article(
            url=url,
            title=title,
            content=content,
            author=author or "ladyironchef",
            publish_date=publish_date,
            category=category,
            tags=tags,
            images=images[:10],
            language="en",
            country="Singapore",
            city="Singapore",
        )
