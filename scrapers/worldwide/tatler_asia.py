# -*- coding: utf-8 -*-
"""
Tatler Asia 爬虫 (分类分页模式)
https://www.tatlerasia.com/
亚洲高端生活杂志，专注餐厅、美食内容

无 Sitemap，使用分页模式爬取 /dining 分类
"""
import json
from typing import List, Optional, Generator
from concurrent.futures import ThreadPoolExecutor, as_completed

from base_scraper import BaseScraper, Article, normalize_date
from config import SITE_CONFIGS, CONCURRENCY_CONFIG


class TatlerAsiaScraper(BaseScraper):
    """
    Tatler Asia 爬虫

    从 /dining 分类分页获取文章（按时间倒序）

    特性:
    - 亚洲高端生活杂志，Tatler Best Indonesia 餐厅榜单
    - 分页按时间倒序，支持 --since 提前终止
    - JSON-LD @graph 格式提取元数据
    - 专注 /dining/food 和 /dining/drinks 内容
    """

    CONFIG_KEY = "tatler_asia"

    # Dining 分类分页 URL 模板
    DINING_PAGE_URL = "https://www.tatlerasia.com/dining/page/{page}"
    DINING_FIRST_PAGE = "https://www.tatlerasia.com/dining"

    def __init__(self, use_proxy: bool = False):
        config = SITE_CONFIGS.get(self.CONFIG_KEY, {})

        super().__init__(
            name=config.get("name", "Tatler Asia"),
            base_url=config.get("base_url", "https://www.tatlerasia.com"),
            delay=config.get("delay", 1.0),  # robots.txt 建议 Crawl-delay: 10，我们用 1 秒
            use_proxy=use_proxy,
            country=config.get("country", ""),  # 亚洲多国，从内容识别
            city=config.get("city", ""),
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
        """从 dining 分页获取文章 URL 列表"""
        if page == 1:
            url = self.DINING_FIRST_PAGE
        else:
            url = self.DINING_PAGE_URL.format(page=page)

        response = self.fetch(url)
        if not response:
            return []

        soup = self.parse_html(response.text)
        urls = []

        # 文章链接格式: /dining/food/slug 或 /dining/drinks/slug
        for a in soup.select("a[href*='/dining/']"):
            href = a.get("href", "")
            if self.is_valid_article_url(href):
                full_url = self.absolute_url(href)
                if full_url not in urls:
                    urls.append(full_url)

        return urls

    def scrape_all(self, limit: int = 0, since: str = None, exclude_urls: set = None) -> List[Article]:
        """
        从 dining 分类分页爬取文章

        分页按时间倒序，支持 --since 提前终止：
        - 如果当前页最后一篇文章的 publish_date < since，停止翻页

        Args:
            limit: 限制文章数量，0 表示不限制
            since: 只爬取该日期之后的文章，格式如 "2025-01-01"
            exclude_urls: 要排除的 URL 集合

        Returns:
            文章列表
        """
        self.logger.info(f"开始爬取 {self.name} (Dining 分类分页模式)...")
        if since:
            self.logger.info(f"启用时间过滤: since={since} (基于 publish_date，支持提前终止)")

        exclude_urls = exclude_urls or set()
        all_articles = []
        page = 1
        max_pages = 100  # 安全限制
        consecutive_old_pages = 0
        max_consecutive_old = 2

        max_workers = CONCURRENCY_CONFIG.get("max_workers", 5)

        while page <= max_pages:
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
                            pub_date = normalize_date(article.publish_date) if article.publish_date else ""

                            if pub_date:
                                if oldest_date_in_page is None or pub_date < oldest_date_in_page:
                                    oldest_date_in_page = pub_date

                            if since and pub_date:
                                if pub_date < since:
                                    self.logger.debug(f"since 过滤跳过: {article.title} ({pub_date})")
                                    continue

                            page_articles.append(article)
                    except Exception as e:
                        self.logger.error(f"爬取失败 {url}: {e}")

            self.logger.info(f"第 {page} 页爬取到 {len(page_articles)} 篇有效文章")
            all_articles.extend(page_articles)

            if limit and len(all_articles) >= limit:
                self.logger.info(f"已达到限制 {limit} 篇，停止爬取")
                all_articles = all_articles[:limit]
                break

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
                    consecutive_old_pages = 0

            page += 1

        self.logger.info(f"爬取完成，共获取 {len(all_articles)} 篇 Dining 文章")
        return all_articles

    def is_valid_article_url(self, url: str) -> bool:
        """检查是否为有效的文章 URL"""
        if not url:
            return False

        # 只要 /dining/ 下的文章
        if "/dining/" not in url:
            return False

        # 文章 URL 格式: /dining/food/slug 或 /dining/drinks/slug
        # 排除分类页
        parts = url.rstrip("/").split("/")
        if len(parts) < 4:
            return False

        # 检查是否是具体文章（有 slug）
        # /dining/food -> 不是文章
        # /dining/food/chocolate-cultures -> 是文章
        valid_categories = {"food", "drinks", "guides", "others"}
        for i, part in enumerate(parts):
            if part == "dining" and i + 2 < len(parts):
                cat = parts[i + 1]
                slug = parts[i + 2]
                if cat in valid_categories and slug and slug != "page":
                    return True

        return False

    def _extract_json_ld(self, soup) -> dict:
        """从页面提取 JSON-LD 数据"""
        for script in soup.select('script[type="application/ld+json"]'):
            try:
                data = json.loads(script.string)
                # 处理 @graph 格式
                if "@graph" in data:
                    for item in data["@graph"]:
                        if item.get("@type") == "Article":
                            return item
                elif data.get("@type") == "Article":
                    return data
            except (json.JSONDecodeError, TypeError):
                continue
        return {}

    def extract_content(self, html: str) -> str:
        """提取文章正文内容"""
        soup = self.parse_html(html)

        # Tatler Asia 特有选择器 - 正文在 .rich-text.text-body-base 中
        content_parts = []
        for rich_text in soup.select(".rich-text.text-body-base"):
            # 移除无用元素
            for tag in rich_text.find_all(["script", "style", "iframe", "noscript"]):
                tag.decompose()
            content = rich_text.decode_contents()
            if len(content) > 50:
                content_parts.append(content)

        if content_parts:
            return "\n\n".join(content_parts)

        # 备用：尝试 article 标签
        article = soup.select_one("article")
        if article:
            for tag in article.find_all(["script", "style", "nav", "aside", "iframe"]):
                tag.decompose()
            for css_sel in [".share", ".social", ".ad", ".related", ".newsletter"]:
                for el in article.select(css_sel):
                    el.decompose()
            content = article.decode_contents()
            if len(content) > 200:
                return content

        return ""

    def parse_article(self, html: str, url: str) -> Optional[Article]:
        """解析文章详情页"""
        soup = self.parse_html(html)

        # 从 JSON-LD 提取元数据
        json_ld = self._extract_json_ld(soup)

        # 标题
        title = json_ld.get("headline") or json_ld.get("name", "")
        if not title:
            h1 = soup.select_one("h1")
            if h1:
                title = self.clean_text(h1.get_text())

        if not title:
            og_title = soup.select_one("meta[property='og:title']")
            if og_title:
                title = og_title.get("content", "")

        if not title:
            return None

        # 正文内容
        content = self.extract_content(html)

        # 作者
        author = ""
        if json_ld.get("author"):
            author_data = json_ld["author"]
            if isinstance(author_data, dict):
                author = author_data.get("name", "")
            elif isinstance(author_data, str):
                author = author_data

        if not author:
            meta_author = soup.select_one("meta[name='author']")
            if meta_author:
                author = meta_author.get("content", "")

        # 发布日期
        publish_date = json_ld.get("datePublished", "")

        # 分类 - 从 URL 提取
        category = ""
        if "/dining/food/" in url:
            category = "Food"
        elif "/dining/drinks/" in url:
            category = "Drinks"
        elif "/dining/guides/" in url:
            category = "Guides"
        elif "/dining/" in url:
            category = "Dining"

        # 标签 - Tatler Asia 没有明显的标签系统
        tags = []

        # 图片
        images = []
        # 从 JSON-LD 获取主图
        if json_ld.get("image"):
            img_url = json_ld["image"]
            if isinstance(img_url, str):
                images.append(img_url)
            elif isinstance(img_url, dict):
                images.append(img_url.get("url", ""))

        # 从页面获取其他图片
        for img in soup.select("article img, .rich-text img"):
            src = img.get("src") or img.get("data-src")
            if src and not src.endswith(".svg"):
                full_src = self.absolute_url(src)
                if full_src not in images:
                    images.append(full_src)

        return Article(
            url=url,
            title=title,
            content=content,
            author=author or "Tatler Asia",
            publish_date=publish_date,
            category=category,
            tags=tags,
            images=images[:10],
            language="en",
            country="",  # 亚洲多国，从标题/内容自动识别
            city="",
        )
