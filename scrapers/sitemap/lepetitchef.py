# -*- coding: utf-8 -*-
"""
Le Petit Chef 爬虫 (Sitemap 模式)
https://lepetitchef.com/blog/
多语言餐厅指南网站 (日语/德语/英语等)

使用 Sitemap 获取文章列表
Sitemap Index: https://lepetitchef.com/blog/sitemap_index.xml
文章 Sitemap: /blog/post-sitemap.xml (Yoast SEO)

使用 Elementor 构建页面
"""
import json
from typing import List, Optional, Generator, Tuple
from xml.etree import ElementTree

from base_scraper import BaseScraper, Article
from config import SITE_CONFIGS


class LePetitChefScraper(BaseScraper):
    """
    Le Petit Chef 爬虫 (Sitemap 模式)

    WordPress + Yoast SEO + Elementor 网站
    - 有完整的 JSON-LD 结构化数据
    - 文章 URL 格式: /blog/[lang]/[article-slug]/
    - 支持多语言: jp (日语), de (德语), en (英语) 等

    URL模式:
    - Sitemap Index: /blog/sitemap_index.xml
    - 文章 Sitemap: /blog/post-sitemap.xml
    """

    CONFIG_KEY = "lepetitchef"

    def __init__(self, use_proxy: bool = False, language: str = None):
        config = SITE_CONFIGS.get(self.CONFIG_KEY, {})
        super().__init__(
            name=config.get("name", "Le Petit Chef"),
            base_url=config.get("base_url", "https://lepetitchef.com/blog"),
            delay=config.get("delay", 0.5),
            use_proxy=use_proxy,
            country=config.get("country", ""),  # Multi-country
            city=config.get("city", ""),
        )
        self.sitemap_url = f"{self.base_url}/post-sitemap.xml"
        self._article_urls_cache = None
        self.categories = config.get("categories", [])
        # 可选语言过滤
        self.language_filter = language

    def fetch_urls_from_sitemap(self) -> List[Tuple[str, str]]:
        """
        从 Sitemap 获取文章URL

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
                        url_with_dates.append((url, mod_date))

            self.logger.info(f"Sitemap: 获取 {len(url_with_dates)} 篇文章")

        except Exception as e:
            self.logger.error(f"获取 Sitemap 失败: {e}")

        url_with_dates.sort(key=lambda x: x[1] if x[1] else "", reverse=True)
        self._article_urls_cache = url_with_dates
        return url_with_dates

    def get_article_list_urls(self) -> Generator[str, None, None]:
        """生成列表页URL - 使用特殊标记"""
        yield "sitemap://lepetitchef"

    def _extract_language_from_url(self, url: str) -> str:
        """从URL提取语言代码"""
        # URL格式: /blog/[lang]/[slug]/
        path = url.replace(self.base_url, "").strip("/")
        parts = path.split("/")
        if parts:
            lang = parts[0]
            # 常见语言代码
            if lang in ["jp", "de", "en", "fr", "es", "it", "pt", "zh", "ko"]:
                return lang
        return ""

    def is_valid_article_url(self, url: str) -> bool:
        """检查是否为有效的文章URL"""
        if not url or "lepetitchef.com/blog" not in url:
            return False

        # 排除非文章页
        exclude_patterns = [
            "/wp-admin/", "/wp-content/", "/wp-includes/",
            "/tag/", "/category/", "/author/", "/page/",
            "/search/", "/attachment/", "/feed/",
            "/about", "/contact", "/privacy", "/terms",
            "/e-landing-page",  # 落地页，不是文章
        ]
        url_lower = url.lower()
        if any(p in url_lower for p in exclude_patterns):
            return False

        # 排除博客首页
        path = url.replace(self.base_url, "").strip("/")
        if not path:
            return False

        # 语言过滤
        if self.language_filter:
            lang = self._extract_language_from_url(url)
            if lang and lang != self.language_filter:
                return False

        return True

    def parse_article_list(self, html: str, list_url: str) -> List[str]:
        """解析文章列表页 - sitemap 模式不使用"""
        return []

    def extract_content(self, html: str) -> str:
        """
        从原始 HTML 提取正文内容

        Le Petit Chef 使用 Elementor 构建
        """
        soup = self.parse_html(html)

        content_selectors = [
            ".elementor-widget-text-editor",  # Elementor 文本块
            ".elementor-widget-container",
            ".entry-content",
            ".post-content",
            "article",
        ]

        # 尝试获取所有 Elementor 文本块并合并
        elementor_texts = soup.select(".elementor-widget-text-editor .elementor-widget-container")
        if elementor_texts:
            combined = []
            for el in elementor_texts:
                # 移除不需要的标签
                for tag in el.find_all(["script", "style", "nav", "aside", "iframe", "noscript"]):
                    tag.decompose()
                html_content = el.decode_contents()
                if html_content.strip():
                    combined.append(html_content)
            if combined:
                content = "\n".join(combined)
                if len(content) > 200:
                    return content

        # 回退到普通选择器
        for selector in content_selectors:
            content_el = soup.select_one(selector)
            if content_el:
                for tag in content_el.find_all([
                    "script", "style", "nav", "aside", "iframe",
                    "button", "form", "noscript"
                ]):
                    tag.decompose()
                for css_sel in [
                    ".sharedaddy", ".jp-relatedposts", ".related-posts",
                    ".social-share", ".post-share", ".share-buttons",
                    ".newsletter", ".optin", ".cta-box",
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
            包含 datePublished, dateModified, author, inLanguage 等的字典
        """
        result = {}

        for script in soup.select('script[type="application/ld+json"]'):
            try:
                data = json.loads(script.string or "")
                items = data if isinstance(data, list) else [data]

                for item in items:
                    # WebPage 或 Article 类型
                    if item.get("@type") in ["WebPage", "Article", "BlogPosting"]:
                        if item.get("datePublished"):
                            result["datePublished"] = item["datePublished"]
                        if item.get("dateModified"):
                            result["dateModified"] = item["dateModified"]
                        if item.get("inLanguage"):
                            result["inLanguage"] = item["inLanguage"]

                    # 从嵌套的 author 对象获取作者名
                    if "author" in item:
                        author = item["author"]
                        if isinstance(author, dict):
                            if author.get("name"):
                                result["author"] = author["name"]
                        elif isinstance(author, str):
                            result["author"] = author

                    # Yoast SEO 的特殊格式：通过 @graph 嵌套
                    if "@graph" in item:
                        for graph_item in item["@graph"]:
                            if graph_item.get("@type") in ["WebPage", "Article", "BlogPosting"]:
                                if graph_item.get("datePublished"):
                                    result["datePublished"] = graph_item["datePublished"]
                                if graph_item.get("dateModified"):
                                    result["dateModified"] = graph_item["dateModified"]
                                if graph_item.get("inLanguage"):
                                    result["inLanguage"] = graph_item["inLanguage"]
                            if graph_item.get("@type") == "Person" and graph_item.get("name"):
                                result["author"] = graph_item["name"]

            except (json.JSONDecodeError, TypeError, KeyError):
                continue

        return result

    # City -> Country mapping for global restaurant guide
    CITY_COUNTRY_MAP = {
        # Germany (most common)
        "frankfurt": ("Germany", "Frankfurt"),
        "berlin": ("Germany", "Berlin"),
        "münchen": ("Germany", "Munich"),
        "munich": ("Germany", "Munich"),
        "hamburg": ("Germany", "Hamburg"),
        "düsseldorf": ("Germany", "Düsseldorf"),
        "duesseldorf": ("Germany", "Düsseldorf"),
        "dortmund": ("Germany", "Dortmund"),
        "offenbach": ("Germany", "Offenbach"),
        "mainz": ("Germany", "Mainz"),
        "aschaffenburg": ("Germany", "Aschaffenburg"),
        "mannheim": ("Germany", "Mannheim"),
        "stuttgart": ("Germany", "Stuttgart"),
        "köln": ("Germany", "Cologne"),
        "cologne": ("Germany", "Cologne"),
        "dresden": ("Germany", "Dresden"),
        "leipzig": ("Germany", "Leipzig"),
        "ulm": ("Germany", "Ulm"),
        "ingolstadt": ("Germany", "Ingolstadt"),
        "hagen": ("Germany", "Hagen"),
        # Japan
        "tokyo": ("Japan", "Tokyo"),
        "osaka": ("Japan", "Osaka"),
        "kyoto": ("Japan", "Kyoto"),
        # USA
        "san-francisco": ("USA", "San Francisco"),
        "phoenix": ("USA", "Phoenix"),
        "nashville": ("USA", "Nashville"),
        "santa-clara": ("USA", "Santa Clara"),
        "new-york": ("USA", "New York"),
        # Indonesia
        "jakarta": ("Indonesia", "Jakarta"),
        "bali": ("Indonesia", "Bali"),
        "bandung": ("Indonesia", "Bandung"),
        # Other
        "singapore": ("Singapore", "Singapore"),
        "seoul": ("South Korea", "Seoul"),
        "hong-kong": ("China", "Hong Kong"),
        "basel": ("Switzerland", "Basel"),
        "hobart": ("Australia", "Hobart"),
        "batumi": ("Georgia", "Batumi"),
        "belgrade": ("Serbia", "Belgrade"),
        "aruba": ("Aruba", "Aruba"),
        "bahrain": ("Bahrain", "Bahrain"),
        "skopje": ("North Macedonia", "Skopje"),
        "cebu": ("Philippines", "Cebu"),
        "antwerp": ("Belgium", "Antwerp"),
        "tenerife": ("Spain", "Tenerife"),
        "birmingham": ("UK", "Birmingham"),
    }

    def _detect_city_and_country(self, title: str, url: str) -> tuple:
        """
        Detect city and country from title or URL

        Returns:
            (country, city) tuple
        """
        text = f"{title} {url}".lower()

        for pattern, (country, city) in self.CITY_COUNTRY_MAP.items():
            if pattern in text:
                return (country, city)

        # Default to Germany if language is German but no city detected
        lang = self._extract_language_from_url(url)
        if lang == "de":
            return ("Germany", "")

        return ("", "")

    def _detect_category_from_url(self, title: str, url: str) -> str:
        """
        Detect category from URL/title keywords

        This site has no category system, so we infer from content type
        """
        text = f"{title} {url}".lower()

        # Category keywords mapping
        category_patterns = {
            # Restaurants
            "restaurant": "Restaurants",
            "restaurants": "Restaurants",
            "essen": "Restaurants",  # German: eat
            "dining": "Restaurants",
            # Cafes
            "cafe": "Cafes",
            "cafes": "Cafes",
            "café": "Cafes",
            "kaffee": "Cafes",  # German: coffee
            # Bars
            "bar": "Bars",
            "bars": "Bars",
            "rooftop": "Bars",
            "cocktail": "Bars",
            # Breakfast/Brunch
            "brunch": "Brunch",
            "frühstück": "Breakfast",  # German: breakfast
            "breakfast": "Breakfast",
            # Specific cuisines
            "sushi": "Japanese",
            "italian": "Italian",
            "italienisch": "Italian",  # German
            "griechisch": "Greek",  # German: Greek
            "greek": "Greek",
            # Fitness (some articles about gyms)
            "fitness": "Fitness",
            "fitnessstudio": "Fitness",  # German: gym
            # Fine dining
            "fine-dining": "Fine Dining",
            "michelin": "Fine Dining",
        }

        for pattern, category in category_patterns.items():
            if pattern in text:
                return category

        # Default category based on site type
        return "Restaurants"

    def parse_article(self, html: str, url: str) -> Optional[Article]:
        """解析文章详情页"""
        soup = self.parse_html(html)

        # 从 JSON-LD 提取结构化数据
        json_ld = self._parse_json_ld(soup)

        # 标题
        title = ""
        title_selectors = [
            "h1.entry-title",
            "h1.elementor-heading-title",
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

        # 作者 - 优先 JSON-LD
        author = json_ld.get("author", "")
        if not author:
            author_selectors = [
                ".author-name",
                ".entry-author a",
                "a[rel='author']",
                ".byline a",
                ".elementor-author-box__name",
            ]
            for selector in author_selectors:
                author_el = soup.select_one(selector)
                if author_el:
                    author = self.clean_text(author_el.get_text())
                    if author:
                        break

        # 发布日期 - 优先 JSON-LD
        publish_date = json_ld.get("datePublished", "")
        if not publish_date:
            date_selectors = [
                "time[datetime]",
                ".entry-date",
                ".post-date",
                "meta[property='article:published_time']",
            ]
            for selector in date_selectors:
                date_el = soup.select_one(selector)
                if date_el:
                    publish_date = date_el.get("datetime") or date_el.get("content") or self.clean_text(date_el.get_text())
                    if publish_date:
                        break

        # 语言 - 从 JSON-LD 或 URL
        language = json_ld.get("inLanguage", "")
        if not language:
            lang_code = self._extract_language_from_url(url)
            # 转换为完整语言代码
            lang_map = {
                "jp": "ja", "de": "de", "en": "en",
                "fr": "fr", "es": "es", "it": "it",
            }
            language = lang_map.get(lang_code, "en")

        # 分类 - 从 URL/标题推断（网站无分类系统）
        category = self._detect_category_from_url(title, url)

        # 标签
        tags = []
        for tag_el in soup.select(".tag-links a, .entry-tags a, a[rel='tag']"):
            tag = self.clean_text(tag_el.get_text())
            if tag and tag not in tags:
                tags.append(tag)

        # 图片
        images = []
        # Elementor 图片
        for img in soup.select(".elementor-widget-image img, .entry-content img, article img"):
            src = img.get("src") or img.get("data-src") or img.get("data-lazy-src")
            if src and not src.endswith(".svg"):
                full_src = self.absolute_url(src)
                if full_src not in images:
                    images.append(full_src)

        # 检测城市和国家
        country, city = self._detect_city_and_country(title, url)

        return Article(
            url=url,
            title=title,
            content=content,
            author=author or "Le Petit Chef",
            publish_date=publish_date,
            category=category,
            tags=tags,
            images=images[:10],
            language=language,
            country=country,
            city=city,
        )
