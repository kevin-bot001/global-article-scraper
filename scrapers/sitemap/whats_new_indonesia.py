# -*- coding: utf-8 -*-
"""
What's New Indonesia 爬虫
https://whatsnewindonesia.com/
印尼生活方式、美食、旅游指南杂志

使用 Sitemap 获取文章列表，比分页爬取更高效可靠
Sitemap: https://whatsnewindonesia.com/sitemap.xml?page=[1-6]

Sitemap页面内容类型映射：
- Page 1: deal（优惠）
- Page 2-3: event（活动）
- Page 4-5: feature（特写）
- Page 6: ultimate-guide（终极指南）
"""
from typing import List, Optional, Generator, Tuple
from xml.etree import ElementTree

from base_scraper import BaseScraper, Article
from config import SITE_CONFIGS


class WhatsNewIndonesiaScraper(BaseScraper):
    """
    What's New Indonesia 爬虫（支持多城市）

    使用 Sitemap 获取文章列表
    支持按内容类型过滤，按lastmod日期倒序爬取

    URL模式:
    - Sitemap: /sitemap.xml?page=[1-6]
    - 详情页: /{city}/[content-type]/[category]/[slug]

    内容类型 (content_types):
    - deal: 优惠信息
    - event: 活动
    - feature: 特写文章
    - ultimate-guide: 终极指南

    子分类 (subcategories) - 仅对ultimate-guide有效:
    - food-drink, nightlife, things-to-do, family-kids, etc.
    """

    # Sitemap页面到内容类型的映射
    SITEMAP_CONTENT_TYPE_MAP = {
        1: ["deal"],
        2: ["event"],
        3: ["event"],
        4: ["feature"],
        5: ["feature"],
        6: ["ultimate-guide"],
    }

    # 所有可用的内容类型
    AVAILABLE_CONTENT_TYPES = ["deal", "event", "feature", "ultimate-guide"]

    # 所有可用的子分类（仅对ultimate-guide有效）
    AVAILABLE_SUBCATEGORIES = [
        "education-learning",
        "expat-guide",
        "family-kids",
        "food-drink",
        "nightlife",
        "shops",
        "spa-well-being",
        "stay",
        "things-to-do",
        "travel",
    ]

    # 配置 key
    CONFIG_KEY = "whats_new_indonesia"

    def __init__(
        self,
        use_proxy: bool = False,
        city: str = None,
        content_types: List[str] = None,
        subcategories: List[str] = None
    ):
        """
        初始化爬虫

        Args:
            use_proxy: 是否使用代理
            city: 城市（必须指定）
            content_types: 要爬取的内容类型列表，None 表示全部
                          例如: ["ultimate-guide", "feature"]
            subcategories: 要爬取的子分类列表（仅对ultimate-guide有效），None 表示全部
                          例如: ["food-drink", "nightlife"]
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
            name="What's New Indonesia",
            base_url=config.get("base_url", "https://whatsnewindonesia.com"),
            delay=config.get("delay", 0.5),
            use_proxy=use_proxy,
            country=country,
            city=self.city.title(),
        )
        self.content_types = content_types  # None表示全部
        self.subcategories = subcategories  # None表示全部
        self._article_urls_cache = None

    def _get_sitemap_pages_for_content_types(self) -> List[int]:
        """根据指定的内容类型，返回需要爬取的sitemap页码"""
        if not self.content_types:
            # 全部内容类型，爬取所有页
            return list(range(1, 7))

        pages = set()
        for page, types in self.SITEMAP_CONTENT_TYPE_MAP.items():
            if any(t in self.content_types for t in types):
                pages.add(page)
        return sorted(pages)

    def fetch_urls_from_sitemap(self) -> List[Tuple[str, str]]:
        """
        从 Sitemap 获取指定城市文章URL，按lastmod倒序排列

        Returns:
            [(url, lastmod), ...] 按lastmod倒序排列
        """
        if self._article_urls_cache is not None:
            return self._article_urls_cache

        url_with_dates = []
        sitemap_pages = self._get_sitemap_pages_for_content_types()

        self.logger.info(f"将爬取 Sitemap 页面: {sitemap_pages}")

        for page in sitemap_pages:
            sitemap_url = f"{self.base_url}/sitemap.xml?page={page}"
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

                self.logger.info(f"Sitemap page {page}: 新增 {count} 篇 {self.city.title()} 文章")

            except Exception as e:
                self.logger.error(f"获取 Sitemap page {page} 失败: {e}")

        # 按lastmod倒序排列（最新的在前）
        url_with_dates.sort(key=lambda x: x[1] if x[1] else "", reverse=True)

        self.logger.info(f"从 Sitemap 共获取 {len(url_with_dates)} 篇 {self.city.title()} 文章URL (按lastmod倒序)")
        self._article_urls_cache = url_with_dates
        return url_with_dates

    def get_article_list_urls(self) -> Generator[str, None, None]:
        """生成列表页URL - 使用特殊标记，实际获取在 scrape_all 中"""
        yield f"sitemap://whats-new-indonesia-{self.city}"

    def is_valid_article_url(self, url: str) -> bool:
        """检查是否为有效的文章URL，支持内容类型和子分类过滤"""
        if not url or self.base_url not in url:
            return False

        # 必须包含城市
        if f"/{self.city}/" not in url:
            return False

        # 排除分类导航页的slug
        category_slugs = [
            "education-learning", "expat-guide", "family-kids", "food-drink",
            "nightlife", "shops", "spa-well-being", "stay", "things-to-do", "travel",
            "food-and-drink", "indonesia-expat-guide", "family-and-kids",
            "things-do", "service", "lifestyle", "hotel", "experience", "news",
            "music-concerts-and-festivals", "business-social-and-workshop", "wine-and-dine",
        ]

        # 检测内容类型
        content_type = None
        if "/ultimate-guide/" in url:
            content_type = "ultimate-guide"
        elif "/feature/" in url:
            content_type = "feature"
        elif "/event/" in url:
            content_type = "event"
        elif "/deal/" in url:
            content_type = "deal"
        else:
            return False

        # 按内容类型过滤
        if self.content_types and content_type not in self.content_types:
            return False

        # 检查URL路径结构
        if content_type == "ultimate-guide":
            path_after_guide = url.split("/ultimate-guide/")[1].rstrip("/")
            parts = [p for p in path_after_guide.split("/") if p and "?" not in p]

            # 如果只有一个部分且是分类slug，则是分类页
            if len(parts) == 1 and parts[0] in category_slugs:
                return False

            # 子分类过滤（仅对ultimate-guide生效）
            if self.subcategories and len(parts) >= 2:
                subcategory = parts[0]
                if subcategory not in self.subcategories:
                    return False

            return len(parts) >= 1 and parts[-1] not in category_slugs

        elif content_type in ["feature", "event", "deal"]:
            # 文章 URL: /{city}/{type}/... - 城市在前
            # 列表 URL: /{type}/{city}/{category} - 类型在前（要排除）
            path = url.replace(self.base_url, "").strip("/")
            parts = [p for p in path.split("/") if p and "?" not in p]

            # 关键判断：第一段是城市还是类型
            # 如果第一段是类型（deal/event/feature），则是列表页
            if parts and parts[0] == content_type:
                return False  # 列表页，类型在前

            # deal 文章: /{city}/deal/{slug} - 3 段
            # event/feature 文章: /{city}/{type}/{category}/{slug} - 4 段
            if content_type == "deal":
                if len(parts) < 3:
                    return False
            else:
                if len(parts) < 4:
                    return False

            return parts[-1] not in category_slugs

        return False

    def parse_article_list(self, html: str, list_url: str) -> List[str]:
        """
        解析文章列表页
        同时缓存每篇文章的分类标签（h5），供后续使用
        """
        soup = self.parse_html(html)
        article_urls = []

        # What's New Indonesia 文章卡片结构:
        # - h5: 分类标签 (如 "Indonesia Expat Guide", "Food and Drink")
        # - h4 > a: 文章标题和链接
        # 遍历所有文章卡片，同时提取URL和标签
        for h4 in soup.select("h4 a[href]"):
            href = h4.get("href")
            if not href:
                continue

            full_url = self.absolute_url(href)
            if not self.is_valid_article_url(full_url) or full_url in article_urls:
                continue

            article_urls.append(full_url)

            # 查找同级或上级的 h5 标签作为分类
            parent = h4.find_parent()
            while parent:
                h5 = parent.find_previous_sibling("h5") or parent.select_one("h5")
                if h5:
                    tag_text = self.clean_text(h5.get_text())
                    if tag_text:
                        # 缓存标签供后续使用
                        if not hasattr(self, '_url_tags'):
                            self._url_tags = {}
                        self._url_tags[full_url] = tag_text
                    break
                parent = parent.find_parent()

        self.logger.debug(f"从 {list_url} 找到 {len(article_urls)} 篇文章")
        return article_urls

    def extract_content(self, html: str) -> str:
        """
        从原始 HTML 提取正文内容

        What's New Indonesia 用 .article-content 等作为主内容区域
        """
        soup = self.parse_html(html)

        content_selectors = [
            ".article-content",
            ".entry-content",
            ".post-content",
            "article .content",
            "main article",
        ]
        for selector in content_selectors:
            content_el = soup.select_one(selector)
            if content_el:
                # 移除不需要的标签元素
                for tag in content_el.find_all(["script", "style", "nav", "aside"]):
                    tag.decompose()
                # 移除不需要的 class 元素
                for css_sel in [".share", ".ad"]:
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

        # 作者 - What's New Indonesia 用 img[alt="Pen"] 图标标识作者
        author = ""
        # 查找包含 Pen 图标的容器，作者名在同一个容器内
        pen_icon = soup.select_one('img[alt="Pen"]')
        if pen_icon and pen_icon.parent:
            # 获取父容器的所有文本（排除img标签）
            author_text = pen_icon.parent.get_text(strip=True)
            if author_text:
                author = self.clean_text(author_text)

        # 发布日期 - 用 img[alt="Calendar"] 图标标识日期
        publish_date = ""
        cal_icon = soup.select_one('img[alt="Calendar"]')
        if cal_icon and cal_icon.parent:
            date_text = cal_icon.parent.get_text(strip=True)
            if date_text:
                publish_date = self.clean_text(date_text)

        # 分类 - 只用URL主分类
        category = ""
        if "/feature/" in url:
            category = "Feature"
        elif "/ultimate-guide/" in url:
            category = "Ultimate Guide"
        elif "/event/" in url:
            category = "Event"
        elif "/deal/" in url:
            category = "Deal"

        # 标签 - 使用列表页缓存的分类标签
        tags = []
        if hasattr(self, '_url_tags') and url in self._url_tags:
            tags.append(self._url_tags[url])

        # 也尝试从文章页获取额外标签
        for tag_el in soup.select(".tag a, .tags a"):
            tag = self.clean_text(tag_el.get_text())
            if tag and tag not in tags:
                tags.append(tag)

        # 图片
        images = []
        for img in soup.select("article img, .featured-image img, .post-content img"):
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
            images=images[:10],
            language="en",
        )

