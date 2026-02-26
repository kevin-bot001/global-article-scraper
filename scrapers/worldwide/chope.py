# -*- coding: utf-8 -*-
"""
Chope 爬虫 (Sitemap 模式)
https://www.chope.co/
餐厅预订平台的美食指南，支持多个城市

使用 Sitemap 获取 guides 页面（榜单、指南等）
Sitemap: https://www.chope.co/sitemap.xml

支持城市: jakarta, bangkok, bali, singapore, phuket
使用方式: --scraper chope:jakarta 或 --scraper chope:bali
"""
import re
from typing import List, Optional, Generator, Tuple
from xml.etree import ElementTree

from base_scraper import BaseScraper, Article
from config import SITE_CONFIGS


class ChopeScraper(BaseScraper):
    """
    Chope 爬虫 (Sitemap 模式)

    从 sitemap 获取指定城市的 guides 页面
    - 只爬取 /{city}-restaurants/pages/ 下的 guide 类内容
    - 排除非内容页（loyalty、exclusives等）

    URL模式:
    - Sitemap: /sitemap.xml
    - Guides: /{city}-restaurants/pages/[guide-name]
    """

    CONFIG_KEY = "chope"

    # 要排除的页面（非内容型或结构特殊难以解析）
    EXCLUDE_PAGES = {
        # 功能/导航页面
        "chopeguides", "loyalty-programme", "chope-exclusives",
        "about-chope-dollars", "dinerfaq", "valentines-day",
        "valentinesdaypromo", "loyalty", "passport",
        "press", "chope-dollars-rewards", "partners",
        # 奖项评选页面（结构复杂难以统一解析）
        "diners-choice-winners", "diners-choice-awards-2022-winners",
        "diners-choice-2021-winners",
    }

    def __init__(self, city: str = None, use_proxy: bool = False):
        """
        初始化 Chope 爬虫

        Args:
            city: 城市名称 (jakarta/bangkok/bali/singapore/phuket)
            use_proxy: 是否使用代理
        """
        config = SITE_CONFIGS.get(self.CONFIG_KEY)
        if not config:
            raise ValueError(f"找不到配置: {self.CONFIG_KEY}")

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
        self.url_segment = f"{self.city}-restaurants"

        # 分类过滤配置（如 buffet-guides, pizzaguide 等）
        self.categories = config.get("categories", [])

        super().__init__(
            name="Chope",
            base_url=f"{config.get('base_url')}/{self.url_segment}",
            delay=config.get("delay", 0.5),
            use_proxy=use_proxy,
            country=country,
            city=self.city,
        )
        self.sitemap_url = "https://www.chope.co/sitemap.xml"
        self._article_urls_cache = None

    def fetch_urls_from_sitemap(self) -> List[Tuple[str, str]]:
        """
        从 Sitemap 获取指定城市的 guides 页面URL

        Returns:
            [(url, lastmod), ...] 按 lastmod 倒序排列
        """
        if self._article_urls_cache is not None:
            return self._article_urls_cache

        url_with_dates = []

        try:
            proxies = self._get_proxy()
            resp = self.session.get(self.sitemap_url, timeout=30, proxies=proxies)
            resp.raise_for_status()

            root = ElementTree.fromstring(resp.content)
            ns = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}

            for url_elem in root.findall('.//sm:url', ns):
                loc = url_elem.find('sm:loc', ns)
                lastmod = url_elem.find('sm:lastmod', ns)

                if loc is not None:
                    url = loc.text
                    mod_date = lastmod.text if lastmod is not None else ""

                    if url and self.is_valid_article_url(url):
                        clean_url = url.replace("&amp;", "&").split("?")[0]
                        if clean_url not in [u for u, _ in url_with_dates]:
                            url_with_dates.append((clean_url, mod_date))

            self.logger.info(f"Sitemap: 获取 {len(url_with_dates)} 个 {self.city.title()} guides 页面")

        except Exception as e:
            self.logger.error(f"获取 Sitemap 失败: {e}")

        url_with_dates.sort(key=lambda x: x[1] if x[1] else "", reverse=True)
        self._article_urls_cache = url_with_dates
        return url_with_dates

    def get_article_list_urls(self) -> Generator[str, None, None]:
        """生成列表页URL - 使用特殊标记"""
        yield f"sitemap://chope-{self.city}"

    def is_valid_article_url(self, url: str) -> bool:
        """检查是否为有效的 guide 页面URL"""
        if not url:
            return False

        if f"/{self.url_segment}/pages/" not in url:
            return False

        match = re.search(r'/pages/([^/?]+)', url)
        if not match:
            return False

        page_name = match.group(1).lower()
        if page_name in self.EXCLUDE_PAGES:
            return False

        if "?lang=" in url or "&lang=" in url:
            return False

        # 分类过滤：如果配置了 categories，只爬取指定分类
        if self.categories:
            # 检查 page_name 是否匹配任意配置的分类
            matched = any(cat.lower() in page_name for cat in self.categories)
            if not matched:
                return False

        return True

    def parse_article_list(self, html: str, list_url: str) -> List[str]:
        """解析文章列表页 - sitemap 模式不使用"""
        return []

    def extract_content(self, html: str) -> str:
        """
        从原始 HTML 提取正文内容

        Chope 有三种页面类型:
        - Type A: 有 .new-pages-4-nav-right (buffet-guides, steak-guide 等)
        - Type B: 无 .new-pages-4-nav-right，h1 + 描述 + 餐厅卡片列表 (plaza-indonesia-guide 等)
        - Type D: 专题指南页面，无 h1，有 banner 描述 + 餐厅卡片 (korean-eateries-guide 等)
        """
        soup = self.parse_html(html)

        # 检测页面类型
        right_el = soup.select_one(".new-pages-4-nav-right")
        is_type_a = right_el is not None

        if is_type_a:
            # Type A: 只提取右侧 POI 卡片列表区域
            for tag in right_el.find_all(["script", "style", "noscript", "iframe"]):
                tag.decompose()
            return right_el.decode_contents()

        # Type B/D: 提取描述 + 餐厅卡片列表
        content_parts = []

        # 找 h1 元素（Type B）
        h1_el = soup.select_one("h1")
        if h1_el:
            # 找 h1 后紧跟的描述段落
            parent = h1_el.parent
            if parent:
                found_h1 = False
                for el in parent.children:
                    if el == h1_el:
                        found_h1 = True
                        continue
                    if found_h1 and hasattr(el, 'name'):
                        if el.name in ["script", "style", "noscript", "iframe"]:
                            continue
                        if el.name in ["div", "p", "span"] and el.get_text(strip=True):
                            text = self.clean_text(el.get_text())
                            if text and len(text) > 20:
                                content_parts.append(f"<p>{text}</p>")
                                break
        else:
            # Type D: 没有 h1，从 banner/header 区域获取描述
            for p in soup.select("header p, .banner p, [class*='banner'] p"):
                text = self.clean_text(p.get_text())
                if text and len(text) > 30:
                    content_parts.append(f"<p>{text}</p>")
                    break

        # 找餐厅卡片列表
        restaurant_list = soup.select_one("ul[class*='restaurant'], div.restaurant-list")
        if not restaurant_list:
            # 备选1：找包含餐厅预订链接的 ul
            for ul in soup.select("ul"):
                links = ul.select("a[href*='/restaurant/']")
                if len(links) >= 3:
                    restaurant_list = ul
                    break

        if not restaurant_list:
            # 备选2 (Type D)：找包含多个餐厅卡片的容器
            restaurant_cards = []
            for h3 in soup.select("h3"):
                link = h3.select_one("a[href*='/restaurant/']") or h3.select_one("a[href*='book.chope.co']")
                if link:
                    name = self.clean_text(link.get_text()) or self.clean_text(h3.get_text())
                    href = link.get("href", "")
                    h4 = h3.find_next_sibling("h4") or h3.parent.select_one("h4")
                    location = self.clean_text(h4.get_text()) if h4 else ""
                    if name:
                        card_html = f'<div class="restaurant-card"><h3><a href="{href}">{name}</a></h3>'
                        if location:
                            card_html += f'<p class="location">{location}</p>'
                        card_html += '</div>'
                        restaurant_cards.append(card_html)

            if restaurant_cards:
                content_parts.append('<div class="restaurants">' + '\n'.join(restaurant_cards) + '</div>')

        if restaurant_list:
            for tag in restaurant_list.find_all(["script", "style", "noscript", "iframe"]):
                tag.decompose()
            content_parts.append(restaurant_list.decode_contents())

        return "\n".join(content_parts)

    def parse_article(self, html: str, url: str) -> Optional[Article]:
        """解析 guide 页面"""
        soup = self.parse_html(html)

        # 检测页面类型：是否有 Type A 特有的右侧导航
        right_el = soup.select_one(".new-pages-4-nav-right")
        is_type_a = right_el is not None

        # ========== 提取标题 ==========
        title = ""
        if is_type_a:
            # Type A: 优先从左边标题区域获取
            title_el = soup.select_one(".new-pages-4-nav-left-top")
            if title_el:
                title = self.clean_text(title_el.get_text())

        if not title:
            title_el = soup.select_one("h1")
            if title_el:
                title = self.clean_text(title_el.get_text())
        if not title:
            title_el = soup.select_one("title")
            if title_el:
                title = self.clean_text(title_el.get_text())
                title = re.sub(r'\s*\|\s*Chope.*$', '', title)

        if not title:
            return None

        # ========== 提取内容 - 调用 extract_content 方法 ==========
        content = self.extract_content(html)

        # ========== 提取作者 ==========
        author = ""
        author_el = soup.select_one(".auth-name")
        if author_el:
            author = self.clean_text(author_el.get_text())

        # ========== 提取发布日期 ==========
        # 日期格式: "DD Mon YYYY" (如 "15 Oct 2024", "24 Apr 2025")
        date_pattern = r'(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4})'
        publish_date = ""

        # 1. 优先从 .update-time 选择器获取（Type A）
        date_el = soup.select_one(".update-time")
        if date_el:
            date_text = self.clean_text(date_el.get_text())
            date_match = re.search(date_pattern, date_text)
            if date_match:
                publish_date = date_match.group(1)

        # 2. 备选：从页面内容中搜索 "Last Updated on" 或 "Updated on" 格式
        if not publish_date:
            # 搜索包含日期的文本（通常在 p 标签里）
            for el in soup.select("p, span, div"):
                text = el.get_text()
                if "Updated on" in text or "updated on" in text:
                    date_match = re.search(date_pattern, text)
                    if date_match:
                        publish_date = date_match.group(1)
                        break

        # 3. 最后备选：从 meta 标签获取
        if not publish_date:
            meta_date = soup.select_one("meta[property='article:published_time']")
            if meta_date:
                publish_date = meta_date.get("content", "").split("T")[0]

        # ========== 提取分类 ==========
        category = ""
        match = re.search(r'/pages/([^/?]+)', url)
        if match:
            category = match.group(1).replace("-", " ").title()

        # ========== 提取图片 ==========
        images = []
        # 限制图片搜索范围，避免抓到 header/footer 的图标
        img_container = right_el if is_type_a else soup.select_one("main, article, .content")
        search_area = img_container or soup
        for img in search_area.select("img[src]"):
            src = img.get("src") or img.get("data-src")
            if src and not src.endswith(".svg"):
                if "chope.co" in src or src.startswith("/"):
                    full_src = self.absolute_url(src)
                    if full_src not in images:
                        images.append(full_src)

        return Article(
            url=url,
            title=title,
            content=content,
            author=author or "Chope",
            publish_date=publish_date,
            category=category,
            tags=[],
            images=images[:10],
            language="en",
        )
