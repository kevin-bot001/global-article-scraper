# HTML Selectors Reference - 常见选择器参考

## Title Selectors - 标题

按优先级排序：

```python
TITLE_SELECTORS = [
    "h1.entry-title",        # WordPress 默认
    "h1.post-title",         # 常见博客
    "h1.article-title",      # 新闻网站
    "h1.page-title",         # 页面标题
    ".article-header h1",    # 嵌套结构
    "article h1",            # 语义化 HTML
    "h1",                    # 最后兜底
]
```

**备选方案**（如果 H1 不可用）：
```python
# Meta 标签
soup.select_one("meta[property='og:title']").get("content")
soup.select_one("meta[name='title']").get("content")

# JSON-LD
json_ld.get("headline")
```

---

## Content Selectors - 正文内容

按优先级排序：

```python
CONTENT_SELECTORS = [
    ".entry-content",        # WordPress 默认
    ".post-content",         # 常见博客
    ".article-content",      # 新闻网站
    ".article-body",         # 新闻网站变体
    ".content-area",         # 内容区域
    ".single-content",       # 单篇文章
    "article .content",      # 嵌套结构
    "article",               # 语义化 HTML（最后兜底）
]
```

**需要移除的元素**：
```python
REMOVE_TAGS = [
    "script", "style", "nav", "aside", "iframe",
    "noscript", "button", "form", "header", "footer"
]

REMOVE_SELECTORS = [
    ".share", ".social", ".ad", ".advertisement",
    ".related", ".related-posts", ".newsletter",
    ".comments", ".comment-form", ".author-box",
    ".sidebar", ".widget", ".navigation",
    ".breadcrumb", ".pagination", ".tags-links"
]
```

---

## Author Selectors - 作者

```python
AUTHOR_SELECTORS = [
    ".author-name",          # 常见类名
    ".byline a",             # WordPress
    "a[rel='author']",       # HTML5 语义化
    ".post-author",          # 博客
    ".article-author",       # 新闻网站
    ".meta-author",          # 元数据区
    ".author a",             # 嵌套结构
    "[itemprop='author']",   # Schema.org
]
```

**JSON-LD 提取**：
```python
# 直接在 item 中
author = item.get("author", {}).get("name", "")

# @graph 格式
for graph_item in data["@graph"]:
    if graph_item.get("@type") == "Person":
        author = graph_item.get("name", "")
```

---

## Date Selectors - 发布日期

```python
DATE_SELECTORS = [
    "time[datetime]",        # HTML5 time 元素（最可靠）
    ".entry-date",           # WordPress
    ".post-date",            # 博客
    ".publish-date",         # 新闻网站
    ".article-date",         # 新闻网站
    ".meta-date",            # 元数据区
    "[itemprop='datePublished']",  # Schema.org
]
```

**提取逻辑**：
```python
date_el = soup.select_one("time[datetime]")
if date_el:
    # 优先取 datetime 属性
    publish_date = date_el.get("datetime") or date_el.get_text().strip()
```

**Meta 标签备选**：
```python
# Open Graph
soup.select_one("meta[property='article:published_time']").get("content")

# Schema.org
soup.select_one("meta[itemprop='datePublished']").get("content")
```

**JSON-LD 提取**：
```python
publish_date = item.get("datePublished", "")
# 或
publish_date = item.get("dateCreated", "")
```

---

## Category Selectors - 分类

```python
CATEGORY_SELECTORS = [
    ".cat-links a",          # WordPress
    ".entry-category a",     # WordPress 变体
    "a[rel='category tag']", # WordPress
    ".post-category a",      # 博客
    ".article-category",     # 新闻网站
    ".category a",           # 通用
    "[itemprop='articleSection']",  # Schema.org
]
```

---

## Tag Selectors - 标签

```python
TAG_SELECTORS = [
    ".tag-links a",          # WordPress
    ".tags a",               # 通用
    "a[rel='tag']",          # HTML5
    ".post-tags a",          # 博客
    ".article-tags a",       # 新闻网站
    ".hashtag",              # 社交媒体风格
]
```

**处理逻辑**：
```python
tags = []
for tag_el in soup.select(".tag-links a, a[rel='tag']"):
    tag = tag_el.get_text().strip()
    # 移除 # 前缀
    tag = tag.lstrip("#")
    if tag and tag not in tags:
        tags.append(tag)
```

---

## Image Selectors - 图片

### 特色图片（Featured Image）

```python
FEATURED_IMAGE_SELECTORS = [
    ".post-thumbnail img",   # WordPress
    ".featured-image img",   # 通用
    ".hero-image img",       # 首图
    ".article-image img",    # 新闻网站
    "article img:first-of-type",  # 文章第一张图
]
```

### 内容图片

```python
CONTENT_IMAGE_SELECTORS = [
    ".entry-content img",    # WordPress
    ".post-content img",     # 博客
    ".article-content img",  # 新闻网站
    "article img",           # 语义化
]
```

### 图片 URL 提取

```python
def get_image_url(img_el):
    # 按优先级尝试不同属性
    return (
        img_el.get("src") or
        img_el.get("data-src") or           # 懒加载
        img_el.get("data-lazy-src") or      # 懒加载变体
        img_el.get("data-original") or      # 另一种懒加载
        img_el.get("srcset", "").split(",")[0].split(" ")[0]  # srcset 第一个
    )
```

### 过滤规则

```python
def is_valid_image(src):
    if not src:
        return False
    # 排除小图标和占位符
    exclude = [".svg", "placeholder", "loading", "spinner", "icon", "logo"]
    return not any(x in src.lower() for x in exclude)
```

---

## Platform-Specific Selectors - 平台特定选择器

### WordPress (Classic)

```python
WORDPRESS_SELECTORS = {
    "title": "h1.entry-title",
    "content": ".entry-content",
    "author": ".author-name, .byline a",
    "date": "time.entry-date[datetime]",
    "category": ".cat-links a",
    "tags": ".tag-links a",
    "featured_image": ".post-thumbnail img",
}
```

### WordPress (Yoast SEO)

优先使用 JSON-LD：
```python
def parse_yoast_json_ld(soup):
    for script in soup.select('script[type="application/ld+json"]'):
        data = json.loads(script.string)
        if "@graph" in data:
            for item in data["@graph"]:
                if item.get("@type") in ["Article", "BlogPosting"]:
                    return {
                        "title": item.get("headline"),
                        "date": item.get("datePublished"),
                        "modified": item.get("dateModified"),
                    }
                if item.get("@type") == "Person":
                    return {"author": item.get("name")}
    return {}
```

### Squarespace

```python
SQUARESPACE_SELECTORS = {
    "title": "h1.entry-title, .blog-item-title",
    "content": ".entry-content, .blog-item-content",
    "author": ".author-name",
    "date": "time.published[datetime]",
}
```

### Ghost

```python
GHOST_SELECTORS = {
    "title": "h1.article-title, h1.post-title",
    "content": ".article-content, .post-content",
    "author": ".author-name, .post-author-name",
    "date": "time.article-date[datetime]",
}
```

---

## JSON-LD Patterns - JSON-LD 模式

### Standard Article

```json
{
    "@type": "Article",
    "headline": "Article Title",
    "datePublished": "2025-01-01T00:00:00+00:00",
    "author": {
        "@type": "Person",
        "name": "Author Name"
    }
}
```

### Yoast SEO @graph

```json
{
    "@context": "https://schema.org",
    "@graph": [
        {
            "@type": "Article",
            "headline": "Article Title",
            "datePublished": "2025-01-01T00:00:00+00:00"
        },
        {
            "@type": "Person",
            "name": "Author Name"
        }
    ]
}
```

### Parsing Logic

```python
def parse_json_ld(soup):
    result = {}
    for script in soup.select('script[type="application/ld+json"]'):
        try:
            data = json.loads(script.string or "")
            items = data if isinstance(data, list) else [data]

            for item in items:
                # 直接格式
                if item.get("@type") in ["Article", "BlogPosting", "NewsArticle"]:
                    result["title"] = item.get("headline", "")
                    result["date"] = item.get("datePublished", "")
                    if isinstance(item.get("author"), dict):
                        result["author"] = item["author"].get("name", "")

                # @graph 格式
                if "@graph" in item:
                    for graph_item in item["@graph"]:
                        if graph_item.get("@type") in ["Article", "BlogPosting"]:
                            result["title"] = graph_item.get("headline", "")
                            result["date"] = graph_item.get("datePublished", "")
                        if graph_item.get("@type") == "Person":
                            result["author"] = graph_item.get("name", "")

        except (json.JSONDecodeError, TypeError, KeyError):
            continue
    return result
```
