# -*- coding: utf-8 -*-
"""
OpenRice 香港爬虫 (API 分页模式)
https://www.openrice.com/en/hongkong

香港最大餐廳評價平台
通過內部 JSON API (/api/articles) 獲取文章列表，無需 sitemap 或 HTML 解析

特殊架構:
- 網站使用 ByteDance CDN + JS Challenge 反爬，HTML 頁面無法用 curl_cffi 或 Playwright 訪問
- 但內部 API (/api/articles) 未受保護，返回 JSON 格式的文章數據
- API 提供: 標題、摘要(100字)、發布日期、作者、分類、封面圖、文章 URL
- 文章 HTML 詳情頁被 JS challenge 攔截，因此 content 只有 API 提供的摘要
- 總計約 7116+ 篇文章，每頁最多 10 條

API 參數:
- page: 分頁 (1-based)
- 不需要 cityId (HK 版本默認返回香港文章)

與 TW 版本的差異:
- 域名: www.openrice.com (TW 為 tw.openrice.com)
- URL 路徑: /zh/hongkong/article/... (TW 為 /zh/taiwan/article/...)
- 不需要 cityId 參數
- 語言: 繁體中文 (zh-HK)
"""
from typing import List, Optional, Generator

from datetime import datetime

from base_scraper import BaseScraper, Article, normalize_date
from config import SITE_CONFIGS


class OpenRiceHKScraper(BaseScraper):
    """
    OpenRice 香港爬虫

    通過 JSON API 獲取文章列表，每頁 10 條
    文章按時間倒序排列，支持 --since 提前終止

    特性:
    - 香港最大餐廳評價/推薦平台
    - 覆蓋港九新界各區餐廳
    - API 返回文章摘要、分類、作者等結構化數據
    - 由於 HTML 頁面反爬，content 為 API 提供的 100 字摘要
    """

    CONFIG_KEY = "openrice_hk"

    # API 端點
    ARTICLES_API = "https://www.openrice.com/api/articles"

    # 每頁文章數 (API 硬限制為 10)
    PAGE_SIZE = 10

    def __init__(self, use_proxy: bool = False):
        config = SITE_CONFIGS.get(self.CONFIG_KEY, {})

        super().__init__(
            name=config.get("name", "OpenRice Hong Kong"),
            base_url=config.get("base_url", "https://www.openrice.com"),
            delay=config.get("delay", 0.5),
            use_proxy=use_proxy,
            country=config.get("country", "Hong Kong"),
            city=config.get("city", "Hong Kong"),
        )

        self.max_pages = config.get("max_pages", 720)

    def get_article_list_urls(self) -> Generator[str, None, None]:
        """使用 API 分页模式，不使用默认分页"""
        yield "api://"

    def parse_article_list(self, html: str, list_url: str) -> List[str]:
        """不使用默认分页模式"""
        return []

    def fetch_urls_from_sitemap(self) -> List[tuple]:
        """不使用 sitemap 模式"""
        return []

    def _fetch_articles_page(self, page: int) -> List[dict]:
        """
        从 API 获取一页文章数据

        Args:
            page: 页码 (1-based)

        Returns:
            文章数据列表 (dict)
        """
        params = {
            "page": str(page),
        }

        # 使用 JSON Accept 头
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-HK,zh-TW;q=0.9,zh;q=0.8,en-US;q=0.7,en;q=0.6",
        }

        response = self.fetch(self.ARTICLES_API, headers=headers, params=params)
        if not response:
            return []

        try:
            data = response.json()
            results = (
                data.get("searchResult", {})
                .get("paginationResult", {})
                .get("results", [])
            )
            return results
        except Exception as e:
            self.logger.error(f"解析 API 响应失败 (page={page}): {e}")
            return []

    def _parse_api_article(self, item: dict) -> Optional[Article]:
        """
        从 API 返回的 JSON 数据解析文章

        Args:
            item: API 返回的单个文章数据

        Returns:
            Article 对象或 None
        """
        title = item.get("titleUI", "").strip()
        if not title:
            return None

        # URL
        url_path = item.get("urlUI", "")
        if not url_path:
            return None
        url = f"https://www.openrice.com{url_path}"

        # 摘要 (API 限制为 100 字)
        body = item.get("bodyUI", "").strip()

        # 发布日期
        publish_time = item.get("publishTime", "")  # e.g. "2026-02-06T00:00:00+08:00"

        # 作者
        author_obj = item.get("authorObj", {})
        author = author_obj.get("authorName", "")

        # 分类
        categories = item.get("articleCategories", [])
        category = categories[0].get("name", "") if categories else ""

        # 封面图
        images = []
        cover_photo = item.get("coverArticlePhoto", {})
        if cover_photo:
            urls_dict = cover_photo.get("urls", {})
            full_url = urls_dict.get("full", "") or cover_photo.get("url", "")
            if full_url:
                images.append(full_url)

        # 标签 (从分类中提取)
        tags = [cat.get("name", "") for cat in categories if cat.get("name")]

        return Article(
            url=url,
            title=title,
            content=f"<p>{body}</p>" if body else "",
            author=author,
            publish_date=publish_time,
            category=category,
            tags=tags,
            images=images,
            language="zh-HK",
            country="Hong Kong",
            city="Hong Kong",
        )

    def scrape_all(
        self,
        limit: int = 0,
        since: str = None,
        exclude_urls: set = None,
    ) -> List[Article]:
        """
        通过 API 分页爬取文章

        API 按时间倒序返回，支持 --since 提前终止

        Args:
            limit: 限制文章数量，0 表示不限制
            since: 只爬取该日期之后的文章，格式如 "2025-01-01"
            exclude_urls: 要排除的 URL 集合

        Returns:
            文章列表
        """
        self.logger.info(f"开始爬取 {self.name} (API 分页模式)...")
        if since:
            self.logger.info(f"启用时间过滤: since={since}")

        exclude_urls = exclude_urls or set()
        all_articles = []
        consecutive_old_pages = 0
        max_consecutive_old = 2  # 连续 N 页都是旧文章则停止

        page = 1
        while page <= self.max_pages:
            # 检查是否已达到 limit
            if limit and len(all_articles) >= limit:
                self.logger.info(f"已达到限制 {limit} 篇，停止爬取")
                break

            self.logger.info(f"正在获取第 {page} 页文章...")
            items = self._fetch_articles_page(page)

            if not items:
                self.logger.info(f"第 {page} 页无文章，停止翻页")
                break

            # 解析本页文章
            page_articles = []
            oldest_date_in_page = None

            for item in items:
                article = self._parse_api_article(item)
                if not article:
                    continue

                # 排除已爬取的 URL
                if article.url in exclude_urls:
                    self.logger.debug(f"跳过已存在的 URL: {article.url}")
                    continue

                # 统一日期格式
                pub_date = normalize_date(article.publish_date)
                article.publish_date = pub_date

                # 更新当前页最老的日期
                if pub_date:
                    if oldest_date_in_page is None or pub_date < oldest_date_in_page:
                        oldest_date_in_page = pub_date

                # since 过滤
                if since and pub_date:
                    if pub_date < since:
                        self.logger.debug(
                            f"since 过滤跳过: {article.title[:30]} ({pub_date})"
                        )
                        continue

                self.stats["articles_scraped"] += 1
                article.source = self.name
                article.scraped_at = datetime.utcnow().isoformat()
                page_articles.append(article)

            self.logger.info(
                f"第 {page} 页解析到 {len(page_articles)} 篇有效文章"
            )
            all_articles.extend(page_articles)

            # 检查是否达到 limit
            if limit and len(all_articles) >= limit:
                all_articles = all_articles[:limit]
                self.logger.info(f"已达到限制 {limit} 篇")
                break

            # 提前终止判断 (API 按时间倒序)
            if since and oldest_date_in_page:
                if oldest_date_in_page < since:
                    consecutive_old_pages += 1
                    self.logger.info(
                        f"第 {page} 页最老文章 ({oldest_date_in_page}) < since ({since})，"
                        f"连续老页 {consecutive_old_pages}/{max_consecutive_old}"
                    )
                    if consecutive_old_pages >= max_consecutive_old:
                        self.logger.info(
                            f"连续 {max_consecutive_old} 页都是旧文章，停止翻页"
                        )
                        break
                else:
                    consecutive_old_pages = 0

            # 如果本页不足 PAGE_SIZE 条，说明没有更多了
            if len(items) < self.PAGE_SIZE:
                self.logger.info("最后一页不足 10 条，已到末尾")
                break

            page += 1

        self.logger.info(
            f"爬取完成: {self.name}\n"
            f"  总请求: {self.stats['total_requests']}\n"
            f"  成功: {self.stats['successful_requests']}\n"
            f"  失败: {self.stats['failed_requests']}\n"
            f"  文章数: {len(all_articles)}"
        )

        return all_articles

    def is_valid_article_url(self, url: str) -> bool:
        """检查是否为有效的文章 URL"""
        if not url:
            return False
        return "/article/" in url and "openrice.com" in url

    def extract_content(self, html: str) -> str:
        """
        由于 HTML 页面被 JS challenge 拦截，不使用此方法
        文章内容直接从 API 的 bodyUI 字段获取
        """
        return ""

    def parse_article(self, html: str, url: str) -> Optional[Article]:
        """
        由于 HTML 页面被 JS challenge 拦截，不使用此方法
        文章数据直接从 API 获取并在 _parse_api_article 中解析
        """
        return None
