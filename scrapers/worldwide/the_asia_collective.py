# -*- coding: utf-8 -*-
"""
The Asia Collective 爬虫 (Sitemap 模式)
https://theasiacollective.com/
亚洲旅游、酒店、餐厅指南网站

使用 Sitemap 获取文章列表
Sitemap Index: https://theasiacollective.com/sitemap_index.xml
文章 Sitemap: /post-sitemap.xml (Yoast SEO)

分类过滤：通过 WordPress REST API 预建 URL→分类 映射，在 sitemap 阶段直接过滤
"""
import json
from typing import List, Optional, Generator, Tuple, Dict, Set
from xml.etree import ElementTree

from base_scraper import BaseScraper, Article
from config import SITE_CONFIGS


class TheAsiaCollectiveScraper(BaseScraper):
    """
    The Asia Collective 爬虫 (Sitemap 模式)

    WordPress + Yoast SEO 网站
    - 有完整的 JSON-LD 结构化数据
    - 文章 URL 格式: /[article-slug]/
    - 使用 REST API 预建分类映射，高效过滤

    URL模式:
    - Sitemap Index: /sitemap_index.xml
    - 文章 Sitemap: /post-sitemap.xml
    - REST API: /wp-json/wp/v2/posts, /wp-json/wp/v2/categories
    """

    CONFIG_KEY = "the_asia_collective"

    def __init__(self, use_proxy: bool = False):
        config = SITE_CONFIGS.get(self.CONFIG_KEY, {})
        super().__init__(
            name=config.get("name", "The Asia Collective"),
            base_url=config.get("base_url", "https://theasiacollective.com"),
            delay=config.get("delay", 0.5),
            use_proxy=use_proxy,
            country=config.get("country", ""),
            city=config.get("city", ""),
        )
        self.sitemap_url = f"{self.base_url}/post-sitemap.xml"
        self._article_urls_cache = None
        # 分类过滤配置
        self.categories = config.get("categories", [])
        # URL → 分类映射（通过 REST API 预建）
        self._url_categories_map: Optional[Dict[str, Set[str]]] = None
        self._category_id_to_slug: Optional[Dict[int, str]] = None

    def _build_category_mapping(self) -> None:
        """
        通过 WordPress REST API 预建 URL → 分类映射

        只在配置了分类过滤时调用，避免无谓的 API 请求
        """
        if self._url_categories_map is not None:
            return  # 已经建立过映射

        self._url_categories_map = {}
        self._category_id_to_slug = {}

        try:
            proxies = self._get_proxy()

            # 1. 获取分类 ID → slug 映射
            page = 1
            while True:
                cat_url = f"{self.base_url}/wp-json/wp/v2/categories?per_page=100&page={page}&_fields=id,slug"
                resp = self.session.get(cat_url, timeout=30, proxies=proxies)
                if resp.status_code != 200:
                    break
                cats = resp.json()
                if not cats:
                    break
                for cat in cats:
                    self._category_id_to_slug[cat["id"]] = cat["slug"]
                page += 1
                if len(cats) < 100:
                    break

            self.logger.info(f"REST API: 获取 {len(self._category_id_to_slug)} 个分类")

            # 2. 获取所有文章的 URL 和分类 ID
            page = 1
            total_posts = 0
            while True:
                posts_url = f"{self.base_url}/wp-json/wp/v2/posts?per_page=100&page={page}&_fields=link,categories"
                resp = self.session.get(posts_url, timeout=30, proxies=proxies)
                if resp.status_code != 200:
                    break
                posts = resp.json()
                if not posts:
                    break
                for post in posts:
                    url = post.get("link", "").rstrip("/") + "/"
                    cat_ids = post.get("categories", [])
                    # 将分类 ID 转换为 slug
                    cat_slugs = {
                        self._category_id_to_slug.get(cid, "")
                        for cid in cat_ids
                        if cid in self._category_id_to_slug
                    }
                    cat_slugs.discard("")
                    if url and cat_slugs:
                        self._url_categories_map[url] = cat_slugs
                total_posts += len(posts)
                page += 1
                if len(posts) < 100:
                    break

            self.logger.info(f"REST API: 建立 {len(self._url_categories_map)} 篇文章的分类映射")

        except Exception as e:
            self.logger.warning(f"REST API 分类映射失败: {e}，将回退到页面解析")
            self._url_categories_map = {}

    def _url_matches_categories(self, url: str) -> bool:
        """
        检查 URL 是否匹配配置的分类

        Returns:
            True 如果匹配或无法确定（回退到页面解析）
        """
        if not self.categories:
            return True  # 没有配置分类过滤

        # 确保映射已建立
        if self._url_categories_map is None:
            self._build_category_mapping()

        # 标准化 URL
        url_normalized = url.rstrip("/") + "/"

        # 如果映射中没有这个 URL，让它通过（可能是新文章）
        if url_normalized not in self._url_categories_map:
            return True

        # 检查是否匹配任意配置的分类
        url_cats = self._url_categories_map[url_normalized]
        config_cats = {c.lower().replace("-", " ").replace("_", " ") for c in self.categories}
        url_cats_normalized = {c.lower().replace("-", " ").replace("_", " ") for c in url_cats}

        return bool(config_cats & url_cats_normalized)

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
        yield "sitemap://the-asia-collective"

    def is_valid_article_url(self, url: str) -> bool:
        """检查是否为有效的文章URL（含分类过滤）"""
        if not url or "theasiacollective.com" not in url:
            return False

        # 排除非文章页
        exclude_patterns = [
            "/wp-admin/", "/wp-content/", "/wp-includes/",
            "/tag/", "/category/", "/author/", "/page/",
            "/search/", "/attachment/", "/feed/",
            "/about", "/contact", "/privacy", "/terms",
            "/shop/", "/product/", "/cart/", "/checkout/",
            "/my-account/", "/wishlist/",
            "/venues/", "/reviews/", "/testimonials/",
            "/blog/",  # 博客列表页
        ]
        url_lower = url.lower()
        if any(p in url_lower for p in exclude_patterns):
            return False

        # 排除首页
        path = url.replace(self.base_url, "").strip("/")
        if not path:
            return False

        # 分类过滤（通过 REST API 预建映射）
        if not self._url_matches_categories(url):
            return False

        return True

    def parse_article_list(self, html: str, list_url: str) -> List[str]:
        """解析文章列表页 - sitemap 模式不使用"""
        return []

    def extract_content(self, html: str) -> str:
        """
        从原始 HTML 提取正文内容

        The Asia Collective 用 .gst-post-body 作为主内容区域
        """
        soup = self.parse_html(html)

        content_selectors = [
            ".gst-post-body",  # The Asia Collective 专用
            ".entry-content",
            "article",
        ]
        for selector in content_selectors:
            content_el = soup.select_one(selector)
            if content_el:
                # 移除不需要的标签元素
                for tag in content_el.find_all([
                    "script", "style", "nav", "aside", "iframe",
                    "button", "form", "noscript"
                ]):
                    tag.decompose()
                # 移除 WordPress 插件相关元素
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
            包含 datePublished, dateModified, author 等的字典
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
                            if graph_item.get("@type") == "Person" and graph_item.get("name"):
                                result["author"] = graph_item["name"]

            except (json.JSONDecodeError, TypeError, KeyError):
                continue

        return result

    def parse_article(self, html: str, url: str) -> Optional[Article]:
        """解析文章详情页"""
        soup = self.parse_html(html)

        # 从 JSON-LD 提取结构化数据
        json_ld = self._parse_json_ld(soup)

        # 标题
        title = ""
        title_selectors = [
            "h1.entry-title",
            "h1.post-title",
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

        # 作者 - 优先 JSON-LD，其次页面元素
        author = json_ld.get("author", "")
        if not author:
            author_selectors = [
                ".author-name",
                ".entry-author a",
                "a[rel='author']",
                ".byline a",
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

        # 分类（仅用于填充 Article，过滤已在 sitemap 阶段通过 REST API 完成）
        category = ""
        cat_selectors = [
            ".cat-links a",
            ".entry-categories a",
            "a[rel='category tag']",
            "a[href*='/category/']",
        ]
        for selector in cat_selectors:
            cat_el = soup.select_one(selector)
            if cat_el:
                category = self.clean_text(cat_el.get_text())
                if category:
                    break

        # 标签
        tags = []
        for tag_el in soup.select(".tag-links a, .entry-tags a, a[rel='tag']"):
            tag = self.clean_text(tag_el.get_text())
            if tag and tag not in tags:
                tags.append(tag)

        # 图片
        images = []
        # 特色图
        featured = soup.select_one(".post-thumbnail img, .entry-thumbnail img, .featured-image img, #primary-image")
        if featured:
            src = featured.get("src") or featured.get("data-src")
            if src:
                images.append(self.absolute_url(src))

        # 内容图片
        for img in soup.select(".entry-content img, article img"):
            src = img.get("src") or img.get("data-src") or img.get("data-lazy-src")
            if src and not src.endswith(".svg"):
                full_src = self.absolute_url(src)
                if full_src not in images:
                    images.append(full_src)

        return Article(
            url=url,
            title=title,
            content=content,
            author=author or "The Asia Collective",
            publish_date=publish_date,
            category=category,
            tags=tags,
            images=images[:10],
            language="en",
        )
