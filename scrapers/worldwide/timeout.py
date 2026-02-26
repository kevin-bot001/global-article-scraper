# -*- coding: utf-8 -*-
"""
Time Out 爬虫
https://www.timeout.com/
全球城市指南品牌，支持多城市

使用 Sitemap Index 动态获取子 sitemap，按 lastmod 倒序爬取
Sitemap Index: https://www.timeout.com/{city}/sitemap.xml.gz

支持城市: jakarta, singapore, hong-kong, tokyo, bangkok, kuala-lumpur 等
使用方式: --scraper timeout:jakarta 或 --scraper timeout:singapore
"""
import gzip
import io
from typing import List, Optional, Generator, Tuple

from base_scraper import BaseScraper, Article
from config import SITE_CONFIGS


class TimeOutScraper(BaseScraper):
    """
    Time Out 爬虫（支持多城市）

    从 Sitemap Index 动态获取子 sitemap，按 lastmod 倒序爬取

    URL模式:
    - Sitemap Index: /{city}/sitemap.xml.gz
    - 子 Sitemap: /{city}/sitemap_0.xml.gz, sitemap_1.xml.gz, ...
    - 详情页: /{city}/[article-slug] 或 /{city}/[category]/[article-slug]
    """

    CONFIG_KEY = "timeout"

    def __init__(self, city: str = None, use_proxy: bool = False):
        """
        初始化 Time Out 爬虫

        Args:
            city: 城市名称 (jakarta/singapore/hong-kong/tokyo/bangkok 等)
            use_proxy: 是否使用代理
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

        # cities_config[city] 直接是 country 字符串
        country = cities_config[self.city]

        super().__init__(
            name="Time Out",
            base_url=f"https://www.timeout.com/{self.city}",
            delay=config.get("delay", 0.5),
            use_proxy=use_proxy,
            country=country,
            city=self.city,
        )
        self.sitemap_index_url = f"https://www.timeout.com/{self.city}/sitemap.xml.gz"
        self._article_urls_cache = None
        # 分类过滤配置
        self.categories = config.get("categories", [])

    def _fetch_gzip_xml(self, url: str) -> Optional[str]:
        """获取并解压 gzip XML 内容"""
        try:
            proxies = self._get_proxy()
            resp = self.session.get(url, timeout=30, proxies=proxies)
            resp.raise_for_status()

            # 尝试解压 gzip
            try:
                with gzip.GzipFile(fileobj=io.BytesIO(resp.content)) as f:
                    return f.read().decode('utf-8')
            except (gzip.BadGzipFile, OSError):
                return resp.text
        except Exception as e:
            self.logger.error(f"获取 {url} 失败: {e}")
            return None

    def _get_child_sitemaps(self) -> List[Tuple[str, str]]:
        """
        从 Sitemap Index 获取所有子 sitemap URL 和 lastmod

        Returns:
            [(sitemap_url, lastmod), ...] 按 lastmod 倒序
        """
        xml_content = self._fetch_gzip_xml(self.sitemap_index_url)
        if not xml_content:
            return []

        sitemaps = []
        try:
            from xml.etree import ElementTree
            root = ElementTree.fromstring(xml_content)
            ns = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}

            for sitemap_elem in root.findall('.//sm:sitemap', ns):
                loc = sitemap_elem.find('sm:loc', ns)
                lastmod = sitemap_elem.find('sm:lastmod', ns)
                if loc is not None and loc.text:
                    sitemap_url = loc.text
                    lastmod_val = lastmod.text if lastmod is not None else ""
                    sitemaps.append((sitemap_url, lastmod_val))

            # 按 lastmod 倒序排列
            sitemaps.sort(key=lambda x: x[1], reverse=True)
            self.logger.info(f"从 Sitemap Index 获取到 {len(sitemaps)} 个子 sitemap")
        except Exception as e:
            self.logger.error(f"解析 Sitemap Index 失败: {e}")

        return sitemaps

    def fetch_urls_from_sitemap(self) -> List[Tuple[str, str]]:
        """
        从所有子 Sitemap 获取文章URL

        Returns:
            [(url, lastmod), ...] 按 lastmod 倒序
        """
        if self._article_urls_cache is not None:
            return self._article_urls_cache

        article_urls = []
        child_sitemaps = self._get_child_sitemaps()

        for sitemap_url, _ in child_sitemaps:
            xml_content = self._fetch_gzip_xml(sitemap_url)
            if not xml_content:
                continue

            try:
                from xml.etree import ElementTree
                root = ElementTree.fromstring(xml_content)
                ns = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}

                for url_elem in root.findall('.//sm:url', ns):
                    loc = url_elem.find('sm:loc', ns)
                    lastmod = url_elem.find('sm:lastmod', ns)
                    if loc is not None and loc.text:
                        url = loc.text
                        if self.is_valid_article_url(url):
                            lastmod_val = lastmod.text if lastmod is not None else ""
                            article_urls.append((url, lastmod_val))
            except Exception as e:
                self.logger.error(f"解析子 Sitemap {sitemap_url} 失败: {e}")

        # 按 lastmod 倒序排列
        article_urls.sort(key=lambda x: x[1], reverse=True)
        self.logger.info(f"从 Sitemap 获取到 {len(article_urls)} 篇文章URL")
        self._article_urls_cache = article_urls

        return article_urls

    def get_article_list_urls(self) -> Generator[str, None, None]:
        """生成列表页URL - 使用特殊标记"""
        yield f"sitemap://timeout-{self.city}"

    def is_valid_article_url(self, url: str) -> bool:
        """检查是否为有效的文章URL"""
        if not url or f"timeout.com/{self.city}" not in url:
            return False

        # 排除列表页、搜索、sitemap等
        exclude_patterns = [
            "/search?", "/profile", "/newsletter",
            "/login", "/register", "/sitemap",
            "sitemap.xml", ".xml.gz",
        ]
        if any(pattern in url for pattern in exclude_patterns):
            return False

        # Time Out 文章URL格式: /{city}/[slug] 或 /{city}/category/[slug]
        path = url.replace(f"https://www.timeout.com/{self.city}", "").rstrip("/")
        parts = [p for p in path.split("/") if p]

        # 至少需要有一个slug
        if len(parts) < 1:
            return False

        # 分类过滤：如果配置了 categories，只爬取指定分类
        if self.categories and len(parts) >= 1:
            category = parts[0]
            if category not in self.categories:
                return False

        return True

    def parse_article_list(self, html: str, list_url: str) -> List[str]:
        """解析文章列表页 - 保留兼容性，返回纯URL列表"""
        return [url for url, _ in self.fetch_urls_from_sitemap()]

    def extract_content(self, html: str) -> str:
        """
        从原始 HTML 提取正文内容

        Time Out 用 CSS Modules，需要用属性选择器
        """
        soup = self.parse_html(html)

        content_selectors = [
            "[class*='main_content']",  # Timeout的主内容区域
            "main",
            ".article-content",
            ".content-body",
        ]
        for selector in content_selectors:
            content_el = soup.select_one(selector)
            if content_el:
                # 移除不需要的标签元素
                for tag in content_el.find_all(["script", "style", "nav", "aside"]):
                    tag.decompose()
                # 移除不需要的 class 元素
                for css_sel in ["[class*='Ad']", "[class*='Newsletter']"]:
                    for el in content_el.select(css_sel):
                        el.decompose()
                content = content_el.decode_contents()
                if len(content) > 100:
                    return content
        return ""

    def parse_article(self, html: str, url: str) -> Optional[Article]:
        """解析文章详情页"""
        soup = self.parse_html(html)

        # 标题
        title = ""
        title_el = soup.select_one("h1")
        if title_el:
            title = self.clean_text(title_el.get_text())

        if not title:
            return None

        # 内容 - 调用 extract_content 方法
        content = self.extract_content(html)

        # 作者 - Timeout 用 CSS Modules
        author = ""
        author_selectors = [
            "[class*='authorDetails']",
            "[class*='authorOverride']",
            "[class*='Author']",
            ".author",
            ".byline",
        ]
        for selector in author_selectors:
            author_el = soup.select_one(selector)
            if author_el:
                author = self.clean_text(author_el.get_text())
                if author.lower().startswith("by "):
                    author = author[3:]
                if " for time out" in author.lower():
                    author = author.split(" for ")[0].strip()
                if author:
                    break

        # 发布日期
        publish_date = ""
        date_el = soup.select_one("time[datetime], [class*='Date'], .published")
        if date_el:
            publish_date = date_el.get("datetime") or self.clean_text(date_el.get_text())

        # 分类 - 从URL提取
        category = ""
        path = url.replace(f"https://www.timeout.com/{self.city}/", "")
        parts = path.split("/")
        if parts:
            category = parts[0].replace("-", " ").title()

        # 图片
        images = []
        for img in soup.select("article img, .hero img, .featured-image img"):
            src = img.get("src") or img.get("data-src")
            if src and "timeout.com" in src:
                images.append(src)

        return Article(
            url=url,
            title=title,
            content=content,
            author=author,
            publish_date=publish_date,
            category=category,
            tags=[],
            images=images[:10],
            language="en",
        )
