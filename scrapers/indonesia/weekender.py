# -*- coding: utf-8 -*-
"""
Weekender 爬虫 (分类分页模式)
https://weekender.thejakartapost.com/
Jakarta Post 周末刊，专注餐厅推荐、美食评论和生活方式内容
"""
import json
import re
from typing import List, Optional, Generator
from concurrent.futures import ThreadPoolExecutor, as_completed

from base_scraper import BaseScraper, Article, normalize_date
from config import SITE_CONFIGS, CONCURRENCY_CONFIG


class WeekenderScraper(BaseScraper):
    """
    Weekender 爬虫

    从分类页面获取文章列表（按时间倒序）
    主要关注 life/table-setting 子分类（餐厅推荐）

    特性:
    - 无 sitemap，使用分类分页模式
    - JSON-LD NewsArticle 元数据
    - 分类页面 ?page=N 分页
    - 文章 URL: /{category}/{year}/{month}/{day}/{slug}.html
    """

    CONFIG_KEY = "weekender"

    # 分类 URL 模板 (子分类更精准，主要爬餐厅相关)
    CATEGORY_URLS = [
        # 餐厅推荐、美食评论 (主要)
        "https://weekender.thejakartapost.com/life/table-setting?page={page}",
        # 生活方式 (次要)
        "https://weekender.thejakartapost.com/life/weekend-five?page={page}",
    ]

    def __init__(self, use_proxy: bool = False):
        config = SITE_CONFIGS.get(self.CONFIG_KEY, {})

        super().__init__(
            name=config.get("name", "Weekender"),
            base_url=config.get("base_url", "https://weekender.thejakartapost.com"),
            delay=config.get("delay", 0.5),
            use_proxy=use_proxy,
            country=config.get("country", "Indonesia"),
            city=config.get("city", "Jakarta"),
        )

    def get_article_list_urls(self) -> Generator[str, None, None]:
        """不使用默认分页模式"""
        yield "category://"

    def parse_article_list(self, html: str, list_url: str) -> List[str]:
        """不使用默认分页模式"""
        return []

    def fetch_urls_from_sitemap(self) -> List[tuple]:
        """不使用 sitemap 模式，返回空让 scrape_all 走自定义逻辑"""
        return []

    def _fetch_page_urls(self, category_url_template: str, page: int) -> List[str]:
        """从分类分页获取文章 URL 列表"""
        url = category_url_template.format(page=page)
        response = self.fetch(url)
        if not response:
            return []

        soup = self.parse_html(response.text)
        urls = []

        # 文章链接在 a.twndr-article (href 可能包含 UTM 参数)
        for link in soup.select("a.twndr-article"):
            href = link.get("href", "")
            if href and self.is_valid_article_url(href):
                full_url = self.absolute_url(href)
                # 去掉 utm 参数
                if "?" in full_url:
                    full_url = full_url.split("?")[0]
                if full_url not in urls:
                    urls.append(full_url)

        return urls

    def _get_max_pages(self, category_url_template: str) -> int:
        """获取分类的最大页数"""
        url = category_url_template.format(page=1)
        response = self.fetch(url)
        if not response:
            return 1

        soup = self.parse_html(response.text)
        # 查找分页: <label class="twndr-pagination__form-label">of <span>3</span></label>
        pagination_label = soup.select_one(".twndr-pagination__form-label span")
        if pagination_label:
            try:
                return int(pagination_label.get_text().strip())
            except ValueError:
                pass
        return 1

    def scrape_all(self, limit: int = 0, since: str = None, exclude_urls: set = None) -> List[Article]:
        """
        从分类分页爬取文章

        Args:
            limit: 限制文章数量，0 表示不限制
            since: 只爬取该日期之后的文章，格式如 "2025-01-01"
            exclude_urls: 要排除的 URL 集合

        Returns:
            文章列表
        """
        self.logger.info(f"开始爬取 {self.name} (分类分页模式)...")
        if since:
            self.logger.info(f"启用时间过滤: since={since}")

        exclude_urls = exclude_urls or set()
        all_articles = []
        all_urls = set()
        max_workers = CONCURRENCY_CONFIG.get("max_workers", 5)

        # 遍历所有分类
        for category_url_template in self.CATEGORY_URLS:
            category_name = category_url_template.split("/")[-1].split("?")[0]
            max_pages = self._get_max_pages(category_url_template)
            self.logger.info(f"分类 {category_name}: 共 {max_pages} 页")

            consecutive_old_pages = 0
            max_consecutive_old = 2

            for page in range(1, max_pages + 1):
                self.logger.info(f"正在获取 {category_name} 第 {page}/{max_pages} 页...")
                page_urls = self._fetch_page_urls(category_url_template, page)

                if not page_urls:
                    self.logger.info(f"{category_name} 第 {page} 页无文章")
                    break

                # 排除已爬取和重复的 URL
                page_urls = [url for url in page_urls if url not in exclude_urls and url not in all_urls]
                if not page_urls:
                    continue

                # 添加到已知 URL 集合
                all_urls.update(page_urls)

                self.logger.info(f"{category_name} 第 {page} 页获取到 {len(page_urls)} 篇文章")

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

                                # since 过滤
                                if since and pub_date and pub_date < since:
                                    self.logger.debug(f"since 过滤跳过: {article.title} ({pub_date})")
                                    continue

                                page_articles.append(article)
                        except Exception as e:
                            self.logger.error(f"爬取失败 {url}: {e}")

                self.logger.info(f"{category_name} 第 {page} 页爬取到 {len(page_articles)} 篇有效文章")
                all_articles.extend(page_articles)

                # 检查是否达到 limit
                if limit and len(all_articles) >= limit:
                    self.logger.info(f"已达到限制 {limit} 篇，停止爬取")
                    all_articles = all_articles[:limit]
                    return all_articles

                # 提前终止判断
                if since and oldest_date_in_page and oldest_date_in_page < since:
                    consecutive_old_pages += 1
                    if consecutive_old_pages >= max_consecutive_old:
                        self.logger.info(f"连续 {max_consecutive_old} 页都是老文章，跳到下一个分类")
                        break
                else:
                    consecutive_old_pages = 0

        self.logger.info(f"爬取完成，共获取 {len(all_articles)} 篇文章")
        return all_articles

    def is_valid_article_url(self, url: str) -> bool:
        """验证是否是有效的文章 URL"""
        if not url:
            return False

        # 去掉查询参数
        clean_url = url.split("?")[0]

        # 支持相对和绝对 URL
        url_path = clean_url
        if "weekender.thejakartapost.com" in clean_url:
            url_path = "/" + clean_url.split("weekender.thejakartapost.com")[-1].lstrip("/")

        # 必须是 .html 结尾的文章页
        if not url_path.endswith(".html"):
            return False

        # 必须包含日期模式 /{year}/{month}/{day}/
        if not re.search(r"/\d{4}/\d{2}/\d{2}/", url_path):
            return False

        # 排除非文章页
        exclude_patterns = [
            "/tag/", "/category/", "/author/",
            "/about", "/contact", "/privacy",
            "/search", "/subscribe",
        ]
        url_lower = url.lower()
        if any(p in url_lower for p in exclude_patterns):
            return False

        return True

    def extract_content(self, html: str) -> str:
        """提取文章正文"""
        soup = self.parse_html(html)

        # Weekender 正文在 .twndr-single__content 内的 <p> 标签
        content_el = soup.select_one(".twndr-single__content")
        if content_el:
            # 移除广告和无关元素
            for tag in content_el.find_all(["script", "style", "nav", "aside", "iframe"]):
                tag.decompose()
            for css_sel in [".twndr-newsletter", ".twndr-share", ".ad", ".twndr-single__content-more"]:
                for el in content_el.select(css_sel):
                    el.decompose()

            # 提取所有 <p> 标签内容
            paragraphs = []
            for p in content_el.find_all("p"):
                text = p.get_text(strip=True)
                # 排除图片说明 (通常很短)
                if text and len(text) > 20:
                    paragraphs.append(f"<p>{text}</p>")

            if paragraphs:
                return "\n".join(paragraphs)

            # 备用：返回整个内容
            content = content_el.decode_contents()
            if len(content) > 200:
                return content

        return ""

    def parse_article(self, html: str, url: str) -> Optional[Article]:
        """解析文章页面"""
        soup = self.parse_html(html)

        # 尝试从 JSON-LD 获取元数据
        json_ld_data = self._extract_json_ld(soup)

        # 标题
        title = ""
        if json_ld_data:
            title = json_ld_data.get("headline", "")
        if not title:
            title_el = soup.select_one("h1.twndr-title, h1")
            if title_el:
                title = self.clean_text(title_el.get_text())
        if not title:
            og_title = soup.select_one("meta[property='og:title']")
            if og_title:
                title = og_title.get("content", "")

        if not title:
            return None

        content = self.extract_content(html)

        # 发布日期
        publish_date = ""
        if json_ld_data:
            publish_date = json_ld_data.get("datePublished", "")
        if not publish_date:
            meta_date = soup.select_one("meta[property='article:published_time']")
            if meta_date:
                publish_date = meta_date.get("content", "")

        # 作者
        author = ""
        if json_ld_data and "author" in json_ld_data:
            authors = json_ld_data.get("author", [])
            if isinstance(authors, list) and authors:
                author = authors[0].get("name", "") if isinstance(authors[0], dict) else str(authors[0])
            elif isinstance(authors, dict):
                author = authors.get("name", "")
        if not author:
            author_meta = soup.select_one("meta[name='twitter:creator']")
            if author_meta:
                author = author_meta.get("content", "")

        # 分类 - 从 URL 提取主分类
        category = ""
        url_path = url.replace(self.base_url, "").strip("/")
        if url_path:
            parts = url_path.split("/")
            if parts:
                # 第一部分是主分类，如 life, the-weekend-digest 等
                main_category = parts[0].replace("-", " ").title()
                # 如果有子分类（非日期），也提取
                if len(parts) > 1 and not parts[1].isdigit():
                    sub_category = parts[1].replace("-", " ").title()
                    category = f"{main_category} - {sub_category}"
                else:
                    category = main_category

        # 也尝试从页面获取分类标签
        if not category:
            channel_el = soup.select_one(".twndr-channel")
            if channel_el:
                category = self.clean_text(channel_el.get_text())

        # 标签 - 从 keywords meta 获取
        tags = []
        keywords_meta = soup.select_one("meta[name='keywords']")
        if keywords_meta:
            keywords = keywords_meta.get("content", "")
            if keywords:
                tags = [t.strip() for t in keywords.split(",") if t.strip()]

        # 图片
        images = []
        # 从 JSON-LD 获取主图
        if json_ld_data and "image" in json_ld_data:
            img_data = json_ld_data.get("image", {})
            if isinstance(img_data, dict):
                img_url = img_data.get("url", "")
                if img_url:
                    images.append(img_url)
            elif isinstance(img_data, str):
                images.append(img_data)

        # 从 og:image 获取
        if not images:
            og_image = soup.select_one("meta[property='og:image']")
            if og_image:
                images.append(og_image.get("content", ""))

        # 从正文获取图片
        for img in soup.select(".twndr-single__content img, .twndr-image img"):
            src = img.get("data-src") or img.get("src")
            if src and not src.endswith(".svg") and "placeholder" not in src:
                full_src = self.absolute_url(src)
                if full_src not in images:
                    images.append(full_src)

        return Article(
            url=url,
            title=title,
            content=content,
            author=author or "Weekender",
            publish_date=publish_date,
            category=category or "Life",
            tags=tags[:10],
            images=images[:10],
            language="en",
            country="Indonesia",
            city="Jakarta",
        )

    def _extract_json_ld(self, soup) -> dict:
        """从页面提取 JSON-LD 数据"""
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string)
                # 查找 NewsArticle 类型
                if isinstance(data, dict):
                    if data.get("@type") == "NewsArticle":
                        return data
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and item.get("@type") == "NewsArticle":
                            return item
            except (json.JSONDecodeError, TypeError):
                continue
        return {}
