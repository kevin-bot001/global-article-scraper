# -*- coding: utf-8 -*-
"""
Booky.ph 爬虫 (分类分页模式)
https://booky.ph/blog/
菲律宾餐厅预订/榜单平台博客，主要覆盖 Metro Manila
"""
from typing import List, Optional, Generator
from concurrent.futures import ThreadPoolExecutor, as_completed

from base_scraper import BaseScraper, Article, normalize_date
from config import SITE_CONFIGS, CONCURRENCY_CONFIG


class BookyPhScraper(BaseScraper):
    """
    Booky.ph 爬虫

    从 Food 分类分页获取文章（按时间倒序）
    WordPress 标准分页: /blog/food/page/{N}/

    特性:
    - 菲律宾餐厅推荐平台
    - 主要覆盖 Metro Manila (BGC, Makati, Pasig 等)
    - 分页按时间倒序，支持 --since 提前终止
    - Meta 标签提供 article:published_time
    """

    CONFIG_KEY = "booky_ph"

    # 分类分页 URL 模板
    CATEGORY_URL = "https://booky.ph/blog/{category}/page/{page}/"
    CATEGORY_FIRST_PAGE_URL = "https://booky.ph/blog/{category}/"

    def __init__(self, use_proxy: bool = False):
        config = SITE_CONFIGS.get(self.CONFIG_KEY, {})

        super().__init__(
            name=config.get("name", "Booky.ph"),
            base_url=config.get("base_url", "https://booky.ph/blog"),
            delay=config.get("delay", 0.5),
            use_proxy=use_proxy,
            country=config.get("country", "Philippines"),
            city=config.get("city", "Metro Manila"),
        )

        self.categories = config.get("categories", ["food"])
        self.max_pages = config.get("max_pages", 50)

    def get_article_list_urls(self) -> Generator[str, None, None]:
        """不使用默认分页模式"""
        yield "category://"

    def parse_article_list(self, html: str, list_url: str) -> List[str]:
        """不使用默认分页模式"""
        return []

    def fetch_urls_from_sitemap(self) -> List[tuple]:
        """不使用 sitemap 模式，返回空让 scrape_all 走自定义逻辑"""
        return []

    def _fetch_page_urls(self, category: str, page: int) -> List[str]:
        """从分类分页获取文章 URL 列表"""
        if page == 1:
            url = self.CATEGORY_FIRST_PAGE_URL.format(category=category)
        else:
            url = self.CATEGORY_URL.format(category=category, page=page)

        response = self.fetch(url)
        if not response:
            return []

        soup = self.parse_html(response.text)
        urls = []

        # 文章链接在 article a[href*="/blog/"] 中
        for article in soup.select("article"):
            link = article.select_one("a[href*='/blog/']")
            if link:
                href = link.get("href", "")
                if href and self.is_valid_article_url(href):
                    full_url = self.absolute_url(href)
                    if full_url not in urls:
                        urls.append(full_url)

        return urls

    def scrape_all(self, limit: int = 0, since: str = None, exclude_urls: set = None) -> List[Article]:
        """
        从分类分页爬取文章

        分页按时间倒序，支持 --since 提前终止：
        - 如果当前页最后一篇文章的 publish_date < since，停止翻页

        Args:
            limit: 限制文章数量，0 表示不限制
            since: 只爬取该日期之后的文章，格式如 "2025-01-01"
            exclude_urls: 要排除的 URL 集合

        Returns:
            文章列表
        """
        self.logger.info(f"开始爬取 {self.name} (分类分页模式)...")
        if since:
            self.logger.info(f"启用时间过滤: since={since} (基于 publish_date，支持提前终止)")

        exclude_urls = exclude_urls or set()
        all_articles = []
        max_workers = CONCURRENCY_CONFIG.get("max_workers", 5)

        for category in self.categories:
            self.logger.info(f"开始爬取分类: {category}")
            page = 1
            consecutive_old_pages = 0
            max_consecutive_old = 2

            while page <= self.max_pages:
                # 检查是否已达到 limit
                if limit and len(all_articles) >= limit:
                    self.logger.info(f"已达到限制 {limit} 篇，停止爬取")
                    break

                self.logger.info(f"正在获取 {category} 第 {page} 页文章列表...")
                page_urls = self._fetch_page_urls(category, page)

                if not page_urls:
                    self.logger.info(f"{category} 第 {page} 页无文章，停止翻页")
                    break

                # 排除已爬取的 URL
                page_urls = [url for url in page_urls if url not in exclude_urls]
                if not page_urls:
                    self.logger.info(f"{category} 第 {page} 页文章都已爬取过，继续下一页")
                    page += 1
                    continue

                self.logger.info(f"{category} 第 {page} 页获取到 {len(page_urls)} 篇文章，开始并发爬取...")

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

                self.logger.info(f"{category} 第 {page} 页爬取到 {len(page_articles)} 篇有效文章")
                all_articles.extend(page_articles)

                # 检查是否达到 limit
                if limit and len(all_articles) >= limit:
                    self.logger.info(f"已达到限制 {limit} 篇，停止爬取")
                    all_articles = all_articles[:limit]
                    break

                # 提前终止判断
                if since and oldest_date_in_page:
                    if oldest_date_in_page < since:
                        consecutive_old_pages += 1
                        self.logger.info(
                            f"{category} 第 {page} 页最老文章 ({oldest_date_in_page}) < since ({since})，"
                            f"连续老页 {consecutive_old_pages}/{max_consecutive_old}"
                        )
                        if consecutive_old_pages >= max_consecutive_old:
                            self.logger.info(f"连续 {max_consecutive_old} 页都是老文章，停止翻页")
                            break
                    else:
                        consecutive_old_pages = 0

                page += 1

            if limit and len(all_articles) >= limit:
                break

        self.logger.info(f"爬取完成，共获取 {len(all_articles)} 篇文章")
        return all_articles

    def is_valid_article_url(self, url: str) -> bool:
        if not url or "booky.ph" not in url:
            return False

        # 只要 /blog/ 路径下的文章
        if "/blog/" not in url:
            return False

        # 排除分类页、标签页、作者页
        exclude_patterns = [
            "/blog/food/",
            "/blog/beauty/",
            "/blog/fitness/",
            "/blog/activities/",
            "/blog/wellness/",
            "/blog/smartness/",
            "/blog/tag/",
            "/blog/author/",
            "/blog/page/",
            "/blog/category/",
        ]
        url_lower = url.lower().rstrip("/") + "/"

        # 检查是否是分类首页（精确匹配）
        for pattern in exclude_patterns:
            if url_lower.endswith(pattern) or f"{pattern}page/" in url_lower:
                return False

        return True

    def extract_content(self, html: str) -> str:
        soup = self.parse_html(html)

        # Booky 文章内容区域
        content_selectors = [
            "article > div > div:nth-child(2)",  # 主内容区域
            ".entry-content",
            ".post-content",
            "article",
        ]

        for selector in content_selectors:
            content_el = soup.select_one(selector)
            if content_el:
                # 移除无用元素
                for tag in content_el.find_all(["script", "style", "nav", "aside", "iframe", "noscript"]):
                    tag.decompose()
                for css_sel in [".share", ".social", ".ad", ".related", ".newsletter", ".sidebar"]:
                    for el in content_el.select(css_sel):
                        el.decompose()
                content = content_el.decode_contents()
                if len(content) > 200:
                    return content
        return ""

    def parse_article(self, html: str, url: str) -> Optional[Article]:
        soup = self.parse_html(html)

        # 标题
        title = ""
        title_el = soup.select_one("h1")
        if title_el:
            title = self.clean_text(title_el.get_text())

        if not title:
            og_title = soup.select_one("meta[property='og:title']")
            if og_title:
                title = og_title.get("content", "").replace(" | Booky", "")

        if not title:
            return None

        content = self.extract_content(html)

        # 作者
        author = ""
        author_el = soup.select_one("a[href*='/author/']")
        if author_el:
            author = self.clean_text(author_el.get_text())
        if not author or author == "":
            # 从页面文本中查找 "by xxx"
            author_text = soup.find(string=lambda t: t and t.strip().startswith("by "))
            if author_text:
                author = self.clean_text(author_text.strip()[3:])  # 移除 "by "
        author = author or "The Booky Team"

        # 发布日期 - 优先从 meta 标签获取
        publish_date = ""
        meta_date = soup.select_one("meta[property='article:published_time']")
        if meta_date:
            publish_date = meta_date.get("content", "")

        # 备用：从 time 元素获取
        if not publish_date:
            time_el = soup.select_one("time")
            if time_el:
                publish_date = time_el.get("datetime") or self.clean_text(time_el.get_text())

        # 分类
        category = ""
        cat_el = soup.select_one("article a[href*='/blog/food/'], article a[href*='/blog/beauty/'], "
                                 "article a[href*='/blog/fitness/'], article a[href*='/blog/activities/'], "
                                 "article a[href*='/blog/wellness/'], article a[href*='/blog/smartness/']")
        if cat_el:
            category = self.clean_text(cat_el.get_text())
        category = category or "Food"

        # 标签
        tags = []
        for tag_el in soup.select("a[href*='/blog/tag/']"):
            tag = self.clean_text(tag_el.get_text())
            if tag and tag not in tags:
                tags.append(tag)

        # 图片
        images = []
        # OG 图片
        og_image = soup.select_one("meta[property='og:image']")
        if og_image:
            src = og_image.get("content")
            if src:
                images.append(src)

        # 内容图片
        for img in soup.select("article img"):
            src = img.get("src") or img.get("data-src")
            if src and not src.endswith(".svg") and "gravatar" not in src:
                full_src = self.absolute_url(src)
                if full_src not in images:
                    images.append(full_src)

        # 描述
        description = ""
        og_desc = soup.select_one("meta[property='og:description']")
        if og_desc:
            description = og_desc.get("content", "")

        return Article(
            url=url,
            title=title,
            content=content,
            author=author,
            publish_date=publish_date,
            category=category,
            tags=tags,
            images=images[:10],
            language="en",
            country="Philippines",
            city="Metro Manila",
        )
