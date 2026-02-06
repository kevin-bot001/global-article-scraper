# -*- coding: utf-8 -*-
"""
The Culture Trip 爬虫 (Sitemap 模式)
https://theculturetrip.com/
全球旅游和文化网站，支持多地区和城市

使用 Sitemap 获取文章列表
Sitemap Index: https://theculturetrip.com/sitemap.xml
文章 Sitemap: https://theculturetrip.com/sitemap/articles/YYYY-MM.xml

URL 结构: /{continent}/{country}/{city}/articles/xxx
支持路径: asia/indonesia (国家级) 或 asia/indonesia/jakarta (城市级)
使用方式: --scraper culture_trip:asia/indonesia/jakarta 或 --scraper culture_trip:asia/japan/tokyo
"""
import re
from datetime import datetime
from typing import List, Optional, Generator, Tuple
from xml.etree import ElementTree

from base_scraper import BaseScraper, Article
from config import SITE_CONFIGS


class CultureTripScraper(BaseScraper):
    """
    The Culture Trip 爬虫 (Sitemap 模式，支持多城市)

    使用 Sitemap 获取指定城市的文章
    - sitemap 按月份分割
    - 支持国家级 (indonesia) 或城市级 (jakarta) 参数

    URL模式:
    - Sitemap Index: /sitemap.xml
    - 文章 Sitemap: /sitemap/articles/YYYY-MM.xml
    - 详情页: /{continent}/{country}/{city}/articles/xxx
    """

    CONFIG_KEY = "culture_trip"

    # city 参数到 URL path 的映射（只保留城市级别）
    CITY_TO_PATH = {
        # 印尼
        "jakarta": "asia/indonesia/jakarta",
        "bali": "asia/indonesia/bali",
        "yogyakarta": "asia/indonesia/yogyakarta",
        "bandung": "asia/indonesia/bandung",
        # 日本
        "tokyo": "asia/japan/tokyo",
        "osaka": "asia/japan/osaka",
        "kyoto": "asia/japan/kyoto",
        # 泰国
        "bangkok": "asia/thailand/bangkok",
        "phuket": "asia/thailand/phuket",
        "chiang-mai": "asia/thailand/chiang-mai",
        # 新加坡（城市国家）
        "singapore": "asia/singapore",
        # 马来西亚
        "kuala-lumpur": "asia/malaysia/kuala-lumpur",
        # 越南
        "ho-chi-minh-city": "asia/vietnam/ho-chi-minh-city",
        "hanoi": "asia/vietnam/hanoi",
        # 菲律宾
        "manila": "asia/philippines/manila",
        # 韩国
        "seoul": "asia/south-korea/seoul",
        # 中国
        "beijing": "asia/china/beijing",
        "shanghai": "asia/china/shanghai",
        "hong-kong": "asia/china/hong-kong",
        # 印度
        "mumbai": "asia/india/mumbai",
        "delhi": "asia/india/delhi",
    }

    def __init__(self, city: str = None, use_proxy: bool = False, months_to_crawl: int = 120):
        """
        初始化爬虫

        Args:
            city: 城市名 (jakarta, tokyo, singapore 等)
            use_proxy: 是否使用代理
            months_to_crawl: 要爬取的月份数量，默认120个月（约10年）
        """
        config = SITE_CONFIGS.get(self.CONFIG_KEY, {})
        cities_config = config.get("cities", {})

        # 使用指定城市（没有默认值，必须指定）
        if not city:
            available = list(cities_config.keys())
            raise ValueError(f"必须指定城市，可选: {available}")
        self.city = city
        if self.city not in cities_config:
            available = list(cities_config.keys())
            raise ValueError(f"不支持的城市: {self.city}，可选: {available}")

        # 从 config 获取 country，从内部映射获取 URL path
        country = cities_config[self.city]
        self.location = self.CITY_TO_PATH.get(self.city, f"asia/{self.city}")

        super().__init__(
            name="Culture Trip",
            base_url=f"https://theculturetrip.com/{self.location}",
            delay=config.get("delay", 1.0),
            use_proxy=use_proxy,
            country=country,
            city=self.city,
        )
        self.sitemap_base = "https://theculturetrip.com"
        self.months_to_crawl = months_to_crawl
        self._article_urls_cache = None

    def _get_sitemap_urls(self) -> List[str]:
        """
        生成要爬取的月份 sitemap URL 列表

        注意：Culture Trip 的 sitemap 按发布月份分割，但旧文章更新后 lastmod 会变新。
        所以不能按 sitemap 文件名过滤，必须获取全部再按 lastmod 过滤。

        Returns:
            sitemap URL 列表（从最新到最旧）
        """
        urls = []
        now = datetime.now()
        year = now.year
        month = now.month

        for _ in range(self.months_to_crawl):
            url = f"{self.sitemap_base}/sitemap/articles/{year}-{month:02d}.xml"
            urls.append(url)

            # 往前推一个月
            month -= 1
            if month < 1:
                month = 12
                year -= 1

        return urls

    def fetch_urls_from_sitemap(self) -> List[Tuple[str, str]]:
        """
        从 Sitemap 获取指定地区文章URL，按 lastmod 倒序排列

        Returns:
            [(url, lastmod), ...] 按 lastmod 倒序排列
        """
        if self._article_urls_cache is not None:
            return self._article_urls_cache

        url_with_dates = []
        sitemap_urls = self._get_sitemap_urls()

        for sitemap_url in sitemap_urls:
            try:
                proxies = self._get_proxy()
                resp = self.session.get(sitemap_url, timeout=30, proxies=proxies)
                if resp.status_code != 200:
                    self.logger.warning(f"Sitemap {sitemap_url} -> HTTP {resp.status_code}")
                    continue

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

                if count > 0:
                    self.logger.info(f"Sitemap {sitemap_url.split('/')[-1]}: 获取 {count} 篇 {self.city} 文章")

            except Exception as e:
                self.logger.warning(f"获取 Sitemap {sitemap_url} 失败: {e}")

        # 按 lastmod 倒序排列（最新的在前）
        url_with_dates.sort(key=lambda x: x[1] if x[1] else "", reverse=True)

        self.logger.info(f"从 Sitemap 共获取 {len(url_with_dates)} 篇 {self.city} 文章URL (按lastmod倒序)")
        self._article_urls_cache = url_with_dates
        return url_with_dates

    def get_article_list_urls(self) -> Generator[str, None, None]:
        """生成列表页URL - 使用特殊标记"""
        yield f"sitemap://culture-trip-{self.location.replace('/', '-')}"

    def is_valid_article_url(self, url: str) -> bool:
        """检查是否为有效的指定地区文章URL"""
        if not url or "theculturetrip.com" not in url:
            return False

        # 必须包含指定地区
        if f"/{self.location}" not in url:
            return False

        # Culture Trip 文章URL必须包含 /articles/ 路径
        if "/articles/" not in url:
            return False

        # 排除非内容页
        exclude_patterns = [
            "/search", "/profile", "/login", "/newsletter",
            "/about-us", "/contact", "/advertise", "/privacy",
            "/trips", "/collections",
        ]
        url_lower = url.lower()
        if any(pattern in url_lower for pattern in exclude_patterns):
            return False

        return True

    def parse_article_list(self, html: str, list_url: str) -> List[str]:
        """解析文章列表页 - sitemap 模式不使用"""
        return []

    def extract_content(self, html: str) -> str:
        """
        从原始 HTML 提取正文内容

        Culture Trip 用 article main 作为主内容区域
        """
        soup = self.parse_html(html)

        content_selectors = [
            "article main",  # Culture Trip 文章主体
            "article [class*='content']",
            "article",
        ]
        for selector in content_selectors:
            content_el = soup.select_one(selector)
            if content_el:
                # 移除不需要的元素
                for tag in content_el.find_all([
                    "script", "style", "nav", "aside", "iframe",
                    "button", "form", "footer"
                ]):
                    tag.decompose()
                # 移除newsletter等干扰内容
                for tag in content_el.select("[class*='newsletter'], [class*='signup'], [class*='ad-']"):
                    tag.decompose()
                content = content_el.decode_contents()
                if len(content) > 200:
                    return content
        return ""

    def parse_article(self, html: str, url: str) -> Optional[Article]:
        """解析文章详情页"""
        soup = self.parse_html(html)

        # 标题 - h1
        title = ""
        title_el = soup.select_one("h1")
        if title_el:
            title = self.clean_text(title_el.get_text())

        if not title:
            return None

        # 内容 - 调用 extract_content 方法
        content = self.extract_content(html)

        # 作者 - 在 a[href*='/authors/'] 里的 strong 标签
        author = ""
        author_el = soup.select_one("a[href*='/authors/'] strong")
        if author_el:
            author = self.clean_text(author_el.get_text())
        if not author:
            # 备用：直接取作者链接文本
            author_link = soup.select_one("a[href*='/authors/']")
            if author_link:
                text = self.clean_text(author_link.get_text())
                # 移除日期部分（格式如 "Geri Moore 08 May 2019"）
                author = re.sub(r'\s+\d{1,2}\s+\w+\s+\d{4}$', '', text).strip()

        # 发布日期 - time 标签
        publish_date = ""
        time_el = soup.select_one("article time")
        if time_el:
            publish_date = time_el.get("datetime") or self.clean_text(time_el.get_text())

        # 分类 - 从URL提取城市
        category = ""
        # 从URL提取：/{region}/[city]/articles/xxx 或 /{region}/articles/xxx
        path = url.replace(f"https://theculturetrip.com/{self.location}/", "")
        parts = [p for p in path.split("/") if p]
        if len(parts) >= 2 and parts[0] != "articles":
            # 有城市：/jakarta/articles/xxx
            category = parts[0].replace("-", " ").title()

        # 标签 - 文章页似乎没有明显的标签区域
        tags = []

        # 图片
        images = []
        for img in soup.select("article img"):
            src = img.get("src") or img.get("data-src")
            if src and not src.endswith(".svg") and "theculturetrip" in src:
                if src not in images:
                    images.append(src)

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
        )
