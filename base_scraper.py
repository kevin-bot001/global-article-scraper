# -*- coding: utf-8 -*-
"""
基础爬虫类 - 使用 curl_cffi 绕过 Cloudflare + proxy
所有网站爬虫的基类，提供通用的请求、解析、存储功能
"""
import json
import logging
import os
import random
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import List, Optional, Dict, Any, Generator
from urllib.parse import urljoin, urlparse

from curl_cffi import requests  # 使用 curl_cffi 绕过 Cloudflare
from curl_cffi.requests.exceptions import RequestException  # curl_cffi 的异常类
from bs4 import BeautifulSoup

from concurrent.futures import ThreadPoolExecutor, as_completed

from config import (
    PROXY_CONFIG,
    REQUEST_CONFIG,
    USER_AGENTS,
    STORAGE_CONFIG,
    LOG_CONFIG,
    CONCURRENCY_CONFIG,
)

# 地名映射（用于从标题/URL识别城市）
from utils.locations import LOCATION_MAP, COUNTRY_NAMES

# 配置日志
logging.basicConfig(
    level=getattr(logging, LOG_CONFIG["level"]),
    format=LOG_CONFIG["format"],
)


def normalize_date(date_str: str) -> str:
    """
    将各种格式的日期字符串统一转换成 ISO 8601 格式 (YYYY-MM-DD)

    支持的格式：
    - "6th November 2025", "1st January 2024"
    - "November 6, 2025", "Jan 6, 2025"
    - "2025-11-06", "2025/11/06"
    - "06/11/2025", "06-11-2025"
    - "2025-11-06T10:30:00+00:00" (ISO 8601 带时间)
    - 等等

    Args:
        date_str: 原始日期字符串

    Returns:
        ISO 8601 格式的日期字符串 (YYYY-MM-DD)，解析失败返回空字符串
    """
    if not date_str:
        return ""

    date_str = date_str.strip()

    # 如果已经是ISO格式带时间，提取日期部分
    if "T" in date_str:
        date_str = date_str.split("T")[0]
        if len(date_str) == 10 and date_str[4] == "-" and date_str[7] == "-":
            return date_str

    # 移除序数后缀 (1st, 2nd, 3rd, 4th, etc.)
    import re
    date_str = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', date_str)

    # 尝试多种格式解析
    formats = [
        "%Y-%m-%d",           # 2025-11-06
        "%Y/%m/%d",           # 2025/11/06
        "%d/%m/%Y",           # 06/11/2025
        "%d-%m-%Y",           # 06-11-2025
        "%m/%d/%Y",           # 11/06/2025 (美式)
        "%B %d, %Y",          # November 6, 2025
        "%b %d, %Y",          # Nov 6, 2025
        "%d %B %Y",           # 6 November 2025
        "%d %b %Y",           # 6 Nov 2025
        "%B %d %Y",           # November 6 2025 (无逗号)
        "%b %d %Y",           # Nov 6 2025 (无逗号)
        "%d %B, %Y",          # 6 November, 2025
        "%Y年%m月%d日",        # 2025年11月06日
        "%d %b, %Y",          # 6 Nov, 2025
    ]

    for fmt in formats:
        try:
            parsed = datetime.strptime(date_str, fmt)
            return parsed.strftime("%Y-%m-%d")
        except ValueError:
            continue

    # 如果都失败了，尝试用 dateutil（如果安装了的话）
    try:
        from dateutil import parser as date_parser
        parsed = date_parser.parse(date_str)
        return parsed.strftime("%Y-%m-%d")
    except (ImportError, ValueError):
        pass

    # 实在解析不了，返回空字符串
    return ""


@dataclass
class Article:
    """文章数据模型"""
    url: str
    title: str
    content: str = ""           # 处理后的正文内容
    raw_html: str = ""          # 原始完整页面 HTML（用于后置处理）
    author: str = ""
    publish_date: str = ""
    category: str = ""
    tags: List[str] = field(default_factory=list)
    images: List[str] = field(default_factory=list)
    source: str = ""
    language: str = "id"  # 默认印尼语
    country: str = ""     # 国家
    city: str = ""        # 城市
    scraped_at: str = ""

    def __post_init__(self):
        """统一格式化字段（确保大小写一致）"""
        # country 和 city 统一 Title Case（首字母大写）
        if self.country:
            self.country = self.country.strip().title()
        if self.city:
            self.city = self.city.strip().title()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)


class BaseScraper(ABC):
    """
    基础爬虫类
    使用 requests 进行 HTTP 请求，支持代理池
    """

    def __init__(
        self,
        name: str,
        base_url: str,
        delay: float = 1.0,
        use_proxy: bool = False,
        country: str = "",
        city: str = "",
    ):
        self.name = name
        self.base_url = base_url
        self.delay = delay
        self.use_proxy = use_proxy and PROXY_CONFIG["enabled"]
        self.country = country
        self.city = city

        self.logger = logging.getLogger(f"scraper.{name}")
        self.session = self._create_session()

        # 统计
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "articles_scraped": 0,
        }

        # 已爬取的URL（去重）
        self._scraped_urls: set = set()

    def _create_session(self) -> requests.Session:
        """创建请求会话 - 使用 curl_cffi 模拟 Chrome 浏览器"""
        session = requests.Session(impersonate="chrome")
        session.headers.update({
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,id;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        })
        return session

    def _get_random_user_agent(self) -> str:
        """获取随机 User-Agent"""
        return random.choice(USER_AGENTS)

    def _get_proxy(self) -> Optional[Dict[str, str]]:
        """获取代理"""
        if not self.use_proxy:
            return None

        # 从代理池获取
        if PROXY_CONFIG.get("proxy_pool_url"):
            try:
                resp = requests.get(PROXY_CONFIG["proxy_pool_url"], timeout=5)
                if resp.ok:
                    proxy = resp.text.strip()
                    return {"http": proxy, "https": proxy}
            except Exception as e:
                self.logger.warning(f"获取代理失败: {e}")

        # 从静态列表随机选择
        if PROXY_CONFIG.get("proxies"):
            proxy = random.choice(PROXY_CONFIG["proxies"])
            return {"http": proxy, "https": proxy}

        return None

    def fetch(self, url: str, **kwargs) -> Optional[requests.Response]:
        """
        发送 HTTP 请求

        Args:
            url: 请求URL
            **kwargs: 传递给 requests.get 的其他参数

        Returns:
            Response 对象或 None
        """
        self.stats["total_requests"] += 1

        # NOTE: 不设置自定义 User-Agent！
        # curl_cffi 的 impersonate="chrome" 会自动设置正确的 UA 和 TLS 指纹
        # 手动设置 UA 会导致 TLS 指纹与 UA 不匹配，被反爬识别
        headers = kwargs.pop("headers", {})

        # 设置代理
        proxies = self._get_proxy()

        # 重试逻辑
        for attempt in range(REQUEST_CONFIG["max_retries"]):
            try:
                self.logger.debug(f"请求: {url} (尝试 {attempt + 1})")

                response = self.session.get(
                    url,
                    headers=headers,
                    proxies=proxies,
                    timeout=REQUEST_CONFIG["timeout"],
                    **kwargs,
                )
                response.raise_for_status()

                self.stats["successful_requests"] += 1

                # 请求间隔
                time.sleep(self.delay + random.uniform(0, 0.5))

                return response

            except RequestException as e:
                self.logger.warning(f"请求失败 ({attempt + 1}/{REQUEST_CONFIG['max_retries']}): {url} - {e}")

                if attempt < REQUEST_CONFIG["max_retries"] - 1:
                    time.sleep(REQUEST_CONFIG["retry_delay"] * (attempt + 1))
                    # 换代理重试
                    proxies = self._get_proxy()

        self.stats["failed_requests"] += 1
        self.logger.error(f"请求最终失败: {url}")
        return None

    def parse_html(self, html: str) -> BeautifulSoup:
        """解析 HTML"""
        return BeautifulSoup(html, "html.parser")

    def clean_text(self, text: str) -> str:
        """清理文本"""
        if not text:
            return ""
        # 移除多余空白
        text = " ".join(text.split())
        return text.strip()

    def absolute_url(self, url: str) -> str:
        """转换为绝对URL"""
        if not url:
            return ""
        return urljoin(self.base_url, url)

    def detect_location_from_title(self, title: str, url: str = "") -> tuple:
        """
        从标题和URL中识别国家和城市（使用单词边界匹配）

        优先级：标题 > URL slug

        Args:
            title: 文章标题
            url: 文章URL（可选）

        Returns:
            (country, city) 元组，识别不到返回空字符串
        """
        import re

        detected_country = ""
        detected_city = ""

        # 合并标题和URL进行匹配（标题优先，放前面）
        # URL 提取 path 部分，将 - 替换为空格
        search_text = (title or "").lower()
        if url:
            from urllib.parse import urlparse
            path = urlparse(url).path.replace("-", " ").replace("/", " ")
            search_text = f"{search_text} {path}"

        if not search_text.strip():
            return "", ""

        # 按地名长度降序排列，先匹配更具体的地名（如 "nusa dua" 优先于 "bali"）
        sorted_locations = sorted(LOCATION_MAP.items(), key=lambda x: len(x[0]), reverse=True)

        # 匹配地名 → (country, city)，使用单词边界避免误匹配
        for location, (country, city) in sorted_locations:
            # \b 单词边界匹配，避免 "menemukan" 里的 "uk" 被误识别
            pattern = r'\b' + re.escape(location) + r'\b'
            if re.search(pattern, search_text):
                detected_country = country
                detected_city = city
                break

        # 如果没匹配到地名，再匹配国家名（同样用单词边界）
        if not detected_country:
            for country_name in COUNTRY_NAMES:
                pattern = r'\b' + re.escape(country_name) + r'\b'
                if re.search(pattern, search_text):
                    detected_country = country_name.title()
                    break

        return detected_country, detected_city

    def is_valid_article_url(self, url: str) -> bool:
        """检查是否为有效的文章URL（子类可重写）"""
        if not url:
            return False
        # 排除常见的非文章URL
        exclude_patterns = [
            "/tag/", "/category/", "/author/", "/page/",
            "/search/", "/login", "/register", "/cart",
            ".jpg", ".png", ".gif", ".pdf", ".css", ".js",
        ]
        url_lower = url.lower()
        return not any(pattern in url_lower for pattern in exclude_patterns)

    def should_skip_url(self, url: str) -> bool:
        """检查URL是否应该跳过（已爬取）"""
        normalized = url.rstrip("/")
        if normalized in self._scraped_urls:
            return True
        self._scraped_urls.add(normalized)
        return False

    @abstractmethod
    def get_article_list_urls(self) -> Generator[str, None, None]:
        """
        获取文章列表页URL
        子类必须实现

        Yields:
            文章列表页URL
        """
        pass

    @abstractmethod
    def parse_article_list(self, html: str, list_url: str) -> List[str]:
        """
        解析文章列表页，提取文章URL
        子类必须实现

        Args:
            html: 列表页HTML
            list_url: 列表页URL

        Returns:
            文章URL列表
        """
        pass

    @abstractmethod
    def parse_article(self, html: str, url: str) -> Optional[Article]:
        """
        解析文章详情页
        子类必须实现

        Args:
            html: 文章页HTML
            url: 文章URL

        Returns:
            Article 对象或 None
        """
        pass

    def extract_content(self, html: str) -> str:
        """
        从原始 HTML 提取正文内容（默认实现）

        子类可以覆写此方法来定义特定的内容提取逻辑。
        也可以在后置处理阶段统一调用此方法重新提取 content。

        Args:
            html: 原始页面 HTML

        Returns:
            处理后的正文内容
        """
        soup = self.parse_html(html)

        # 默认提取逻辑：尝试常见的内容区域选择器
        content_selectors = [
            ".entry-content",
            ".post-content",
            ".article-content",
            "article .content",
            "article",
            "main",
        ]

        for selector in content_selectors:
            content_el = soup.select_one(selector)
            if content_el:
                # 移除常见的无用元素
                for tag in content_el.find_all([
                    "script", "style", "nav", "aside", "iframe",
                    "noscript", "button", "form", "footer"
                ]):
                    tag.decompose()
                # 移除常见的广告、分享等元素
                for css_sel in [
                    ".share", ".ad", ".advertisement", ".related",
                    ".newsletter", ".social", ".comments"
                ]:
                    for el in content_el.select(css_sel):
                        el.decompose()

                content = content_el.decode_contents()
                if len(content) > 100:
                    return content

        return ""

    def scrape_article(self, url: str) -> Optional[Article]:
        """爬取单篇文章"""
        if self.should_skip_url(url):
            self.logger.debug(f"跳过已爬取URL: {url}")
            return None

        response = self.fetch(url)
        if not response:
            return None

        try:
            raw_html = response.text  # 保存原始完整 HTML
            article = self.parse_article(raw_html, url)
            if article:
                article.raw_html = raw_html  # 自动保存原始 HTML
                article.source = self.name
                article.scraped_at = datetime.utcnow().isoformat()

                # 设置 country 和 city：优先保留 parse_article 设置的值，其次从标题/URL识别，最后用默认值
                detected_country, detected_city = self.detect_location_from_title(article.title, url)
                article.country = article.country or detected_country or self.country
                article.city = article.city or detected_city or self.city

                # 统一日期格式为 ISO 8601
                article.publish_date = normalize_date(article.publish_date)
                self.stats["articles_scraped"] += 1
                self.logger.info(f"成功爬取: {article.title[:50]}...")
            return article
        except Exception as e:
            self.logger.error(f"解析文章失败: {url} - {e}")
            return None

    def scrape_list_page(self, list_url: str, limit: int = 0, current_count: int = 0) -> List[Article]:
        """
        爬取列表页中的文章（支持并发）

        Args:
            list_url: 列表页URL
            limit: 文章数量限制，0表示不限制
            current_count: 当前已爬取数量（用于判断是否达到limit）

        Returns:
            文章列表
        """
        articles = []

        response = self.fetch(list_url)
        if not response:
            return articles

        try:
            article_urls = self.parse_article_list(response.text, list_url)
            self.logger.info(f"从 {list_url} 获取到 {len(article_urls)} 篇文章")

            # 过滤有效URL
            valid_urls = [url for url in article_urls if self.is_valid_article_url(url)]

            # 如果有limit限制，截取需要的数量
            if limit:
                remaining = limit - current_count
                if remaining <= 0:
                    return articles
                valid_urls = valid_urls[:remaining]

            # 使用并发爬取
            if CONCURRENCY_CONFIG.get("enabled", True) and len(valid_urls) > 1:
                articles = self._scrape_articles_concurrent(valid_urls)
            else:
                # 串行爬取（fallback）
                for article_url in valid_urls:
                    article = self.scrape_article(article_url)
                    if article:
                        articles.append(article)

        except Exception as e:
            self.logger.error(f"解析列表页失败: {list_url} - {e}")

        return articles

    def _scrape_articles_concurrent(self, urls: List[str]) -> List[Article]:
        """
        使用线程池并发爬取文章

        Args:
            urls: 文章URL列表

        Returns:
            文章列表（保持原始顺序）
        """
        articles = []
        max_workers = CONCURRENCY_CONFIG.get("max_workers", 5)
        results = {}

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_idx = {
                executor.submit(self.scrape_article, url): idx
                for idx, url in enumerate(urls)
            }

            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                try:
                    article = future.result()
                    if article:
                        results[idx] = article
                except Exception as e:
                    self.logger.error(f"并发爬取失败: {urls[idx]} - {e}")

        # 按原始顺序返回结果
        for idx in sorted(results.keys()):
            articles.append(results[idx])

        return articles

    def fetch_urls_from_sitemap(self) -> List[tuple]:
        """
        从 Sitemap 获取文章URL列表（子类可重写）

        Returns:
            [(url, lastmod), ...] 或 [url, ...] 按需要的顺序排列
        """
        raise NotImplementedError("子类需要实现 fetch_urls_from_sitemap 方法")

    def scrape_all(self, limit: int = 0, since: str = None, exclude_urls: set = None) -> List[Article]:
        """
        爬取所有文章，自动检测 sitemap 模式

        Args:
            limit: 限制爬取数量，0表示不限制
            since: 只爬取该日期之后的文章，格式如 "2025-01-01"（仅 sitemap 模式有效）
            exclude_urls: 要排除的 URL 集合（用于跳过已爬取的文章）

        Returns:
            文章列表
        """
        # 检测是否使用 sitemap 模式
        list_urls = list(self.get_article_list_urls())
        if list_urls and list_urls[0].startswith("sitemap://"):
            return self._scrape_all_sitemap(limit, since, exclude_urls)
        else:
            if since:
                self.logger.warning("since 参数仅在 sitemap 模式下有效，当前为分页模式")
            return self._scrape_all_pagination(limit)

    def _scrape_all_sitemap(self, limit: int = 0, since: str = None, exclude_urls: set = None) -> List[Article]:
        """
        Sitemap 模式爬取（并发）

        Args:
            limit: 限制最终有效文章数量，0表示不限制
            since: 只爬取该日期之后的文章，格式如 "2025-01-01"（基于文章真正的 publish_date）
            exclude_urls: 要排除的URL集合（已爬取过的）

        Returns:
            文章列表
        """
        self.logger.info(f"开始爬取 {self.name} (Sitemap+并发模式)...")

        # 从 Sitemap 获取所有文章URL
        url_data = self.fetch_urls_from_sitemap()

        if not url_data:
            self.logger.warning("未从 Sitemap 获取到任何文章URL")
            return []

        # lastmod 预过滤优化：lastmod >= publish_date 恒成立
        # 所以 lastmod < since 的文章可以直接跳过，不需要下载
        # 但 lastmod >= since 不代表 publish_date >= since，所以下载后还要精确过滤
        if since and url_data and isinstance(url_data[0], tuple):
            original_count = len(url_data)
            filtered_data = []
            for url, lastmod in url_data:
                if lastmod:
                    # 提取日期部分（处理 ISO 格式如 "2025-01-15T10:30:00Z"）
                    lastmod_date = lastmod.split("T")[0] if "T" in lastmod else lastmod[:10]
                    if lastmod_date < since:
                        continue  # lastmod < since，直接跳过
                filtered_data.append((url, lastmod))
            url_data = filtered_data
            skipped = original_count - len(url_data)
            if skipped > 0:
                self.logger.info(f"lastmod 预过滤 (< {since}): {original_count} -> {len(url_data)} 篇（跳过 {skipped} 篇）")

        # 排除已爬取的URL
        if exclude_urls:
            original_count = len(url_data)
            if url_data and isinstance(url_data[0], tuple):
                url_data = [(url, lastmod) for url, lastmod in url_data if url not in exclude_urls]
            else:
                url_data = [url for url in url_data if url not in exclude_urls]
            self.logger.info(f"排除已爬取URL: {original_count} -> {len(url_data)} 篇（跳过 {original_count - len(url_data)} 篇）")

        # 构建 url -> lastmod 映射，用于后续设置 publish_date（仅作备用）
        url_to_lastmod = {}
        if url_data and isinstance(url_data[0], tuple):
            url_to_lastmod = {url: lastmod for url, lastmod in url_data}
            all_urls = [url for url, _ in url_data]
        else:
            all_urls = url_data

        # 如果设置了 limit，分批爬取直到获得足够的有效文章
        # 否则一次性爬取所有
        all_articles = []
        batch_size = CONCURRENCY_CONFIG.get("batch_size", 10) * 2  # 每批多爬一些，留余量给过滤

        if limit:
            # 分批爬取模式：持续爬取直到有效文章数达到 limit
            url_index = 0
            max_batches = 10  # 最多爬取10批，避免 since 过滤导致无限循环
            batch_num = 0
            while len(all_articles) < limit and url_index < len(all_urls):
                batch_num += 1
                if batch_num > max_batches:
                    self.logger.warning(
                        f"已达到最大批次限制({max_batches})，当前有效文章 {len(all_articles)} 篇。"
                        f"可能是 since={since} 过滤条件太严格，大部分文章不满足条件。"
                    )
                    break

                # 计算还需要多少篇
                need_count = limit - len(all_articles)
                # 如果有 since 过滤，多取一些余量；否则精确取需要的数量
                if since:
                    fetch_count = max(batch_size, need_count * 2)
                else:
                    fetch_count = need_count  # 精确取需要的数量，避免浪费请求
                batch_urls = all_urls[url_index:url_index + fetch_count]
                url_index += fetch_count

                if not batch_urls:
                    break

                # 并发爬取这一批
                batch_articles = self._scrape_articles_concurrent(batch_urls)

                # 补充 lastmod 作为 publish_date 备用
                for article in batch_articles:
                    if not article.publish_date and article.url in url_to_lastmod:
                        lastmod = url_to_lastmod[article.url]
                        article.publish_date = lastmod.split("T")[0] if lastmod else ""

                # since 过滤
                if since:
                    filtered_batch = []
                    for article in batch_articles:
                        if article.publish_date:
                            pub_date = article.publish_date.split("T")[0] if "T" in article.publish_date else article.publish_date
                            if pub_date >= since:
                                filtered_batch.append(article)
                            else:
                                self.logger.debug(f"since 过滤跳过: {article.title} (publish_date={pub_date})")
                        else:
                            filtered_batch.append(article)
                    batch_articles = filtered_batch

                all_articles.extend(batch_articles)
                self.logger.debug(f"批次爬取: 请求 {len(batch_urls)} 篇，有效 {len(batch_articles)} 篇，累计 {len(all_articles)} 篇")

            # 截取到 limit
            if len(all_articles) > limit:
                all_articles = all_articles[:limit]
        else:
            # 无 limit，一次性爬取所有
            all_articles = self._scrape_articles_concurrent(all_urls)

            # 补充 lastmod 作为 publish_date 备用
            for article in all_articles:
                if not article.publish_date and article.url in url_to_lastmod:
                    lastmod = url_to_lastmod[article.url]
                    article.publish_date = lastmod.split("T")[0] if lastmod else ""

            # since 过滤
            if since:
                original_count = len(all_articles)
                filtered_articles = []
                for article in all_articles:
                    if article.publish_date:
                        pub_date = article.publish_date.split("T")[0] if "T" in article.publish_date else article.publish_date
                        if pub_date >= since:
                            filtered_articles.append(article)
                        else:
                            self.logger.debug(f"since 过滤跳过: {article.title} (publish_date={pub_date})")
                    else:
                        filtered_articles.append(article)
                all_articles = filtered_articles
                self.logger.info(f"时间过滤 (since={since}, 基于 publish_date): {original_count} -> {len(all_articles)} 篇")

        self.logger.info(
            f"爬取完成: {self.name}\n"
            f"  总请求: {self.stats['total_requests']}\n"
            f"  成功: {self.stats['successful_requests']}\n"
            f"  失败: {self.stats['failed_requests']}\n"
            f"  文章数: {len(all_articles)}"
        )

        return all_articles

    def _scrape_all_pagination(self, limit: int = 0) -> List[Article]:
        """
        分页模式爬取（原有逻辑）

        Args:
            limit: 限制爬取数量，0表示不限制

        Returns:
            文章列表
        """
        self.logger.info(f"开始爬取 {self.name}...")
        all_articles = []

        for list_url in self.get_article_list_urls():
            # 传递limit和当前数量，让列表页爬取时就检查limit
            articles = self.scrape_list_page(list_url, limit=limit, current_count=len(all_articles))
            all_articles.extend(articles)

            if limit and len(all_articles) >= limit:
                all_articles = all_articles[:limit]
                self.logger.info(f"达到限制 {limit}，停止爬取")
                break

        self.logger.info(
            f"爬取完成: {self.name}\n"
            f"  总请求: {self.stats['total_requests']}\n"
            f"  成功: {self.stats['successful_requests']}\n"
            f"  失败: {self.stats['failed_requests']}\n"
            f"  文章数: {self.stats['articles_scraped']}"
        )

        return all_articles

    def save_to_json(self, articles: List[Article], filename: str = None):
        """保存到 JSON 文件"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.name.lower().replace(' ', '_')}_{timestamp}.json"

        output_dir = STORAGE_CONFIG["output_dir"]
        os.makedirs(output_dir, exist_ok=True)

        filepath = os.path.join(output_dir, filename)

        data = [article.to_dict() for article in articles]

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        self.logger.info(f"保存到: {filepath}")
        return filepath


class WordPressScraper(BaseScraper):
    """
    WordPress 网站爬虫基类
    适用于使用 WordPress 的网站（如 NOW! Jakarta, Coconuts, Flokq 等）
    """

    def __init__(self, *args, categories: List[str] = None, max_pages: int = 50, **kwargs):
        super().__init__(*args, **kwargs)
        self.categories = categories or []
        self.max_pages = max_pages

    def get_article_list_urls(self) -> Generator[str, None, None]:
        """生成分类和分页URL"""
        if self.categories:
            for category in self.categories:
                for page in range(1, self.max_pages + 1):
                    if page == 1:
                        yield f"{self.base_url}/category/{category}/"
                    else:
                        yield f"{self.base_url}/category/{category}/page/{page}/"
        else:
            # 如果没有分类，直接爬取首页分页
            for page in range(1, self.max_pages + 1):
                if page == 1:
                    yield f"{self.base_url}/"
                else:
                    yield f"{self.base_url}/page/{page}/"

    def parse_article_list(self, html: str, list_url: str) -> List[str]:
        """WordPress 通用列表页解析"""
        soup = self.parse_html(html)
        article_urls = []

        # 常见的文章链接选择器
        selectors = [
            "article a[href]",
            ".post a[href]",
            ".entry-title a[href]",
            "h2 a[href]",
            "h3 a[href]",
            ".article-title a[href]",
        ]

        for selector in selectors:
            links = soup.select(selector)
            for link in links:
                href = link.get("href")
                if href:
                    full_url = self.absolute_url(href)
                    if self.is_valid_article_url(full_url) and full_url not in article_urls:
                        article_urls.append(full_url)

        return article_urls

    def parse_article(self, html: str, url: str) -> Optional[Article]:
        """WordPress 通用文章解析"""
        soup = self.parse_html(html)

        # 标题
        title = ""
        title_selectors = ["h1.entry-title", "h1.post-title", "h1", ".article-title"]
        for selector in title_selectors:
            el = soup.select_one(selector)
            if el:
                title = self.clean_text(el.get_text())
                break

        if not title:
            return None

        # 内容 - 保留HTML结构以便后续提取结构化数据（如店名、地址等）
        content = ""
        content_selectors = [
            ".entry-content", ".post-content", ".article-content",
            "article .content", ".single-content", "main article"
        ]
        for selector in content_selectors:
            el = soup.select_one(selector)
            if el:
                # 移除脚本和样式，但保留HTML结构
                for tag in el.find_all(["script", "style", "nav", "aside"]):
                    tag.decompose()
                # 保存内部HTML而非纯文本
                content = el.decode_contents()
                break

        # 作者
        author = ""
        author_selectors = [".author", ".byline", ".entry-author", "[rel='author']"]
        for selector in author_selectors:
            el = soup.select_one(selector)
            if el:
                author = self.clean_text(el.get_text())
                break

        # 发布日期
        publish_date = ""
        date_selectors = [
            "time[datetime]", ".published", ".entry-date",
            ".post-date", "meta[property='article:published_time']"
        ]
        for selector in date_selectors:
            el = soup.select_one(selector)
            if el:
                publish_date = el.get("datetime") or el.get("content") or self.clean_text(el.get_text())
                break

        # 分类
        category = ""
        cat_selectors = [".category", ".cat-links a", ".entry-category a"]
        for selector in cat_selectors:
            el = soup.select_one(selector)
            if el:
                category = self.clean_text(el.get_text())
                break

        # 标签
        tags = []
        tag_selectors = [".tags a", ".tag-links a", ".entry-tags a"]
        for selector in tag_selectors:
            for el in soup.select(selector):
                tag = self.clean_text(el.get_text())
                if tag and tag not in tags:
                    tags.append(tag)

        # 图片
        images = []
        for img in soup.select("article img, .entry-content img, .post-content img"):
            src = img.get("src") or img.get("data-src")
            if src:
                images.append(self.absolute_url(src))

        return Article(
            url=url,
            title=title,
            content=content,
            author=author,
            publish_date=publish_date,
            category=category,
            tags=tags,
            images=images[:10],  # 限制图片数量
        )


class PlaywrightScraper(BaseScraper):
    """
    Playwright 爬虫基类
    用于处理有反爬机制的网站（如 reCAPTCHA、Cloudflare）
    注意：所有 Playwright 操作必须在同一事件循环中执行
    """

    def __init__(self, *args, headless: bool = True, **kwargs):
        super().__init__(*args, **kwargs)
        self.headless = headless
        self._browser = None
        self._context = None
        self._page = None
        self._playwright = None

    async def _init_browser(self):
        """初始化浏览器（懒加载）"""
        if self._browser is None:
            from playwright.async_api import async_playwright
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=self.headless,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                    "--no-sandbox",
                ]
            )
            self._context = await self._browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent=self._get_random_user_agent(),
                locale="en-US",
            )
            self._page = await self._context.new_page()
            self.logger.info("Playwright 浏览器已启动")

    async def _close_browser(self):
        """关闭浏览器"""
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
            self.logger.info("Playwright 浏览器已关闭")

    async def fetch_with_playwright(self, url: str, wait_selector: str = None) -> Optional[str]:
        """
        使用 Playwright 获取页面内容

        Args:
            url: 页面URL
            wait_selector: 等待的CSS选择器

        Returns:
            页面HTML或None
        """
        await self._init_browser()
        self.stats["total_requests"] += 1

        try:
            self.logger.debug(f"Playwright 请求: {url}")
            await self._page.goto(url, wait_until="domcontentloaded", timeout=30000)

            if wait_selector:
                try:
                    await self._page.wait_for_selector(wait_selector, timeout=10000)
                except Exception:
                    self.logger.warning(f"等待选择器超时: {wait_selector}")

            # 滚动页面加载懒加载内容
            await self._page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
            await self._page.wait_for_timeout(1000)

            html = await self._page.content()
            self.stats["successful_requests"] += 1

            # 请求间隔
            import asyncio
            await asyncio.sleep(self.delay + random.uniform(0, 0.5))

            return html

        except Exception as e:
            self.stats["failed_requests"] += 1
            self.logger.error(f"Playwright 请求失败: {url} - {e}")
            return None

    async def scrape_article_async(self, url: str, wait_selector: str = None) -> Optional[Article]:
        """异步爬取单篇文章"""
        if self.should_skip_url(url):
            self.logger.debug(f"跳过已爬取URL: {url}")
            return None

        raw_html = await self.fetch_with_playwright(url, wait_selector)
        if not raw_html:
            return None

        try:
            article = self.parse_article(raw_html, url)
            if article:
                article.raw_html = raw_html  # 保存原始 HTML
                article.source = self.name
                article.scraped_at = datetime.utcnow().isoformat()

                # 设置 country 和 city：优先保留 parse_article 设置的值，其次从标题/URL识别，最后用默认值
                detected_country, detected_city = self.detect_location_from_title(article.title, url)
                article.country = article.country or detected_country or self.country
                article.city = article.city or detected_city or self.city

                # 统一日期格式为 ISO 8601
                article.publish_date = normalize_date(article.publish_date)
                self.stats["articles_scraped"] += 1
                self.logger.info(f"成功爬取: {article.title[:50]}...")
            return article
        except Exception as e:
            self.logger.error(f"解析文章失败: {url} - {e}")
            return None

    async def scrape_all_async(self, limit: int = 0, since: str = None, exclude_urls: set = None) -> List[Article]:
        """
        异步爬取所有文章

        Args:
            limit: 限制爬取数量，0表示不限制
            since: 只保留该日期之后的文章，格式如 "2025-01-01"（基于 publish_date 过滤）
            exclude_urls: 要排除的URL集合（已爬取过的）

        Returns:
            文章列表
        """
        if since:
            self.logger.info(f"启用时间过滤: since={since} (基于文章 publish_date)")
        self.logger.info(f"开始爬取 {self.name} (Playwright模式)...")
        all_articles = []
        skipped_by_date = 0  # 记录因日期过滤跳过的文章数
        exclude_urls = exclude_urls or set()

        try:
            for list_url in self.get_article_list_urls():
                # 先检查是否已达到limit
                if limit and len(all_articles) >= limit:
                    break

                html = await self.fetch_with_playwright(list_url)
                if not html:
                    continue

                article_urls = self.parse_article_list(html, list_url)
                self.logger.info(f"从 {list_url} 获取到 {len(article_urls)} 篇文章")

                for article_url in article_urls:
                    # 在爬取每篇文章前检查limit
                    if limit and len(all_articles) >= limit:
                        self.logger.info(f"达到限制 {limit}，停止爬取")
                        break

                    if not self.is_valid_article_url(article_url):
                        continue

                    # 跳过已排除的URL
                    if article_url in exclude_urls:
                        self.logger.debug(f"跳过已存在的URL: {article_url}")
                        continue

                    # 前置过滤：如果子类提供了 get_url_date 方法，在爬取前就过滤
                    if since and hasattr(self, 'get_url_date'):
                        cached_date = self.get_url_date(article_url)
                        if cached_date and cached_date < since:
                            skipped_by_date += 1
                            self.logger.debug(f"前置过滤跳过旧文章 ({cached_date} < {since}): {article_url}")
                            continue

                    article = await self.scrape_article_async(article_url)
                    if article:
                        # 后置过滤：基于 publish_date 进行时间过滤（兜底）
                        if since and article.publish_date:
                            normalized = normalize_date(article.publish_date)
                            if normalized and normalized < since:
                                skipped_by_date += 1
                                self.logger.debug(f"后置过滤跳过旧文章 ({normalized} < {since}): {article.title}")
                                continue
                        all_articles.append(article)

                if limit and len(all_articles) >= limit:
                    break

        finally:
            await self._close_browser()

        # 构建日志消息
        log_lines = [
            f"爬取完成: {self.name}",
            f"  总请求: {self.stats['total_requests']}",
            f"  成功: {self.stats['successful_requests']}",
            f"  失败: {self.stats['failed_requests']}",
            f"  文章数: {self.stats['articles_scraped']}",
        ]
        if since and skipped_by_date > 0:
            log_lines.append(f"  日期过滤跳过: {skipped_by_date}")
        self.logger.info("\n".join(log_lines))

        return all_articles

    def scrape_all(self, limit: int = 0, since: str = None, exclude_urls: set = None) -> List[Article]:
        """同步包装器 - 调用异步方法"""
        import asyncio

        # 获取或创建事件循环
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            # 如果已经在异步上下文中，使用 run_coroutine_threadsafe
            import concurrent.futures
            import threading

            result = []
            event = threading.Event()

            def run():
                nonlocal result
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    result = new_loop.run_until_complete(self.scrape_all_async(limit, since, exclude_urls))
                finally:
                    new_loop.close()
                    event.set()

            thread = threading.Thread(target=run)
            thread.start()
            event.wait()
            return result
        else:
            # 否则直接运行
            return asyncio.run(self.scrape_all_async(limit, since, exclude_urls))
