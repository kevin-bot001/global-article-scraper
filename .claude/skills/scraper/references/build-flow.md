# Scraper Build Flow - 爬虫构建详细流程

## Phase 1: EXPLORE - 探索目标网站

### 1.1 检查 robots.txt

```bash
curl -s https://example.com/robots.txt | head -50
```

查找：
- `Sitemap:` 指令（sitemap 位置）
- `Disallow:` 规则（需要避开的路径）

### 1.2 检查 Sitemap

```bash
# 常见 sitemap 位置
curl -s https://example.com/sitemap.xml | head -100
curl -s https://example.com/sitemap_index.xml | head -100
curl -s https://example.com/post-sitemap.xml | head -100
```

### 1.3 识别 Sitemap 格式

| 格式 | 特征 | 示例 |
|------|------|------|
| **标准 XML** | `<urlset>` 根元素 | 简单的 `<url><loc>` 结构 |
| **Sitemap Index** | `<sitemapindex>` 根元素 | 包含多个 `<sitemap>` 子节点 |
| **Yoast SEO** | `post-sitemap.xml` 命名 | WordPress 常见，有 JSON-LD |
| **Google News** | `<news:news>` 命名空间 | 新闻网站，有 `<news:publication_date>` |
| **CDATA 包装** | `<![CDATA[...]]>` | All in One SEO 常见 |

### 1.4 测试反爬

```python
from curl_cffi import requests

url = "https://example.com/sitemap.xml"
response = requests.get(url, impersonate="chrome")
print(f"Status: {response.status_code}")
print(f"Content length: {len(response.text)}")
```

- **200**: curl_cffi 可以绕过，使用 BaseScraper
- **403**: 可能需要 PlaywrightScraper

### 1.5 无 Sitemap 时检测分页

```bash
# 检查常见分页模式
curl -s https://example.com/blog/ | grep -oE 'href="[^"]*page[^"]*"' | head -10
curl -s https://example.com/articles/ | grep -oE 'href="[^"]*page[^"]*"' | head -10
```

常见分页 URL 模式：
- `/blog/page/2/`
- `/articles?page=2`
- `/news/2`

---

## Phase 1.5: VALIDATE - 验证网站质量（双重验证）

### 1.5a 活跃度验证

从 sitemap `<lastmod>` 或文章页面获取最新发布日期：
- ✅ 2025+ → 继续
- ⚠️ 2024 或更早 → AskUserQuestion 确认

### 1.5b POI 内容验证 ⚠️ 关键检查（三级判断，由粗到细）

#### Level 1: URL 模式批量扫描（最快，零额外请求）

从 sitemap 已获取的 URL 列表中批量分析路径模式，无需额外请求：

```python
from collections import Counter

urls = [...]  # sitemap 中的所有 URL

# 统计 URL 路径中的关键词
path_keywords = []
for url in urls:
    path = urlparse(url).path.lower()
    path_keywords.extend(re.findall(r'/([a-z-]+)/', path))

keyword_counts = Counter(path_keywords).most_common(20)

# ❌ 食谱站 URL 特征（多语言）
recipe_patterns = [
    '/recipe/', '/recipes/', '/resep/', '/resepi/',       # EN/ID/MY
    '/cara-membuat/', '/cara-masak/',                      # ID
    '/สูตร/', '/วิธีทำ/',                                    # TH
    '/cong-thuc/', '/mon-an/',                              # VN
]

# ✅ POI 站 URL 特征（多语言）
poi_patterns = [
    '/restaurant/', '/review/', '/cafe/', '/hotel/',        # EN
    '/best-/', '/top-/', '/guide/', '/where-to-/',          # EN
    '/restoran/', '/kuliner/', '/tempat-makan/',            # ID
    '/ร้านอาหาร/', '/รีวิว/',                                  # TH
    '/nha-hang/', '/quan-an/', '/dia-diem/',                # VN
]
```

如果 URL 模式就能明确判断网站类型 → **跳过 Level 2/3**。

#### Level 2: JSON-LD Schema 类型检测（ANALYZE 阶段顺带做）

在 Phase 2 分析文章 HTML 时顺便检查 JSON-LD `@type`：

```python
# 在分析 JSON-LD 时检查 schema 类型
for script in soup.select('script[type="application/ld+json"]'):
    data = json.loads(script.string or "")
    types = []

    if "@graph" in data:
        types = [item.get("@type") for item in data["@graph"]]
    elif "@type" in data:
        types = [data["@type"]]

    # ❌ 食谱站
    if "Recipe" in types:
        # → 直接拒绝，不构建

    # ✅ POI 站
    if any(t in types for t in ["Restaurant", "LocalBusiness",
                                 "Article", "BlogPosting"]):
        # → 继续构建
```

#### Level 3: 最新文章内容抽检（仅在 Level 1/2 无法判断时）

取 sitemap 中 **lastmod 最新的 2 篇文章**，使用语言无关的信号检测：

```python
import re

def has_poi_signals(html):
    """语言无关的 POI 信号检测"""
    signals = 0

    # 1. 地址模式: 街道号码、邮编
    if re.search(r'(?:Jl\.|Jalan|Street|Road|Ave|Blvd|Soi)\s', html):
        signals += 1

    # 2. Google Maps 链接或嵌入
    if 'google.com/maps' in html or 'maps.googleapis.com' in html:
        signals += 1

    # 3. 电话号码模式 (国际格式)
    if re.search(r'\+\d{2,3}[\s-]?\d', html):
        signals += 1

    # 4. 营业时间格式 (数字:数字 模式)
    if re.search(r'\d{1,2}[:.]\d{2}\s*[-–]\s*\d{1,2}[:.]\d{2}', html):
        signals += 1

    # 5. 榜单格式: H2/H3 编号标题
    numbered_headings = re.findall(r'<h[23][^>]*>\s*\d+[\.\)]\s', html)
    if len(numbered_headings) >= 3:
        signals += 1

    return signals >= 2

```

**判定规则**：
- ✅ 有 POI 信号 → 继续构建
- ⚠️ 不确定 → AskUserQuestion 让用户确认
- ❌ 无 POI 信号 → 拒绝并说明原因

**直接拒绝的类型**：
- 食谱/烹饪教程网站（URL 含 /recipe/ 或 JSON-LD 含 Recipe）
- 个人生活博客（无地址、无店铺名、无联系方式）
- 纯新闻评论站（无具体 POI 信息）
- 产品评测站（非吃喝玩乐类目）

---

## Phase 2: ANALYZE - 分析网站结构

### 2.1 多城市/多语言检测

检查 URL 结构：
```
多城市: https://example.com/singapore/articles/...
        https://example.com/jakarta/articles/...

多语言: https://example.com/en/articles/...
        https://example.com/id/articles/...
```

检查 sitemap 是否按城市/语言分组。

### 2.2 从 Sitemap 提取 Categories

```python
import re
from collections import Counter

# 从 URL 中提取 category 模式
urls = [...]  # sitemap 中的所有 URL
categories = []

for url in urls:
    # 常见模式: /category/food/, /travel/, /lifestyle/
    match = re.search(r'/([a-z-]+)/', url)
    if match:
        categories.append(match.group(1))

print(Counter(categories).most_common(20))
```

### 2.3 分析文章页 HTML 结构

随机抽取 3 篇文章，检查：

```python
from bs4 import BeautifulSoup

soup = BeautifulSoup(html, "html.parser")

# 标题选择器
for sel in ["h1.entry-title", "h1.post-title", "h1.article-title", "h1"]:
    el = soup.select_one(sel)
    if el:
        print(f"Title selector: {sel} -> {el.get_text()[:50]}")
        break

# 内容选择器
for sel in [".entry-content", ".post-content", ".article-content", "article"]:
    el = soup.select_one(sel)
    if el:
        print(f"Content selector: {sel} -> {len(el.get_text())} chars")
        break

# 作者选择器
for sel in [".author-name", ".byline a", "a[rel='author']", ".post-author"]:
    el = soup.select_one(sel)
    if el:
        print(f"Author selector: {sel} -> {el.get_text()}")
        break

# 日期选择器
for sel in ["time[datetime]", ".entry-date", ".post-date", ".publish-date"]:
    el = soup.select_one(sel)
    if el:
        print(f"Date selector: {sel} -> {el.get('datetime') or el.get_text()}")
        break
```

### 2.4 检查 JSON-LD 结构化数据

```python
import json

for script in soup.select('script[type="application/ld+json"]'):
    try:
        data = json.loads(script.string or "")
        print(json.dumps(data, indent=2)[:500])

        # 检查 @graph 格式 (Yoast SEO)
        if "@graph" in data:
            for item in data["@graph"]:
                if item.get("@type") in ["Article", "BlogPosting"]:
                    print(f"Found Article in @graph")
                    print(f"  headline: {item.get('headline')}")
                    print(f"  datePublished: {item.get('datePublished')}")
    except json.JSONDecodeError:
        pass
```

### 2.5 确定语言和地区

```python
# 从 HTML lang 属性
html_tag = soup.select_one("html")
lang = html_tag.get("lang", "") if html_tag else ""
print(f"HTML lang: {lang}")

# 从 meta 标签
og_locale = soup.select_one("meta[property='og:locale']")
if og_locale:
    print(f"OG locale: {og_locale.get('content')}")

# 从内容判断
# - 印尼语常见词: yang, dan, di, untuk, dengan
# - 英语: the, and, of, to, in
```

---

## Phase 3: GENERATE - 生成代码

### 3.1 选择模板

根据分析结果选择模板：

| 条件 | 模板 |
|------|------|
| 标准 sitemap + 单语言 | `sitemap_standard.py.tpl` |
| Yoast SEO + JSON-LD | `sitemap_yoast.py.tpl` |
| Google News sitemap | `sitemap_news.py.tpl` |
| CDATA 包装的 sitemap | `sitemap_cdata.py.tpl` |
| 无 sitemap，需分页 | `pagination.py.tpl` |
| 多城市支持 | `multi_city.py.tpl` |
| 需要 JS 渲染 | 使用 PlaywrightScraper |

### 3.2 填充模板变量

```python
template_vars = {
    "class_name": "ExampleScraper",
    "config_key": "example",
    "site_name": "Example Site",
    "base_url": "https://example.com",
    "sitemap_urls": ["sitemap.xml", "post-sitemap.xml"],
    "url_pattern": r"/article/",
    "exclude_patterns": ["/category/", "/tag/", "/author/"],
    "content_selectors": [".entry-content", ".post-content"],
    "title_selector": "h1.entry-title",
    "author_selector": ".author-name",
    "date_selector": "time[datetime]",
    "has_json_ld": True,
    "language": "en",
    "country": "Indonesia",
    "default_city": "Jakarta",
}
```

### 3.3 生成 config.py 配置

```python
SITE_CONFIGS["example"] = {
    "name": "Example Site",
    "base_url": "https://example.com",
    "delay": 0.5,
    "country": "Indonesia",
    "default_city": "Jakarta",
    "categories": [],  # 空表示爬取全部
}
```

---

## Phase 4: REGISTER - 注册爬虫

### 4.1 创建爬虫文件

位置：`scrapers/sitemap/example.py`

### 4.2 更新 scrapers/sitemap/__init__.py

```python
from .example import ExampleScraper

__all__ = [
    # ... existing exports
    "ExampleScraper",
]
```

### 4.3 更新 scrapers/__init__.py

```python
# 导入
from .sitemap import (
    # ... existing imports
    ExampleScraper,
)

# __all__
__all__ = [
    # ... existing
    "ExampleScraper",
]

# SCRAPER_REGISTRY
SCRAPER_REGISTRY = {
    # ... existing
    "example": ExampleScraper,
}

# SITEMAP_SCRAPERS
SITEMAP_SCRAPERS = {
    # ... existing
    "example",
}

# 如果是参数化爬虫
PARAMETERIZED_SCRAPERS = {
    # ... existing
    "example": "city",  # example:jakarta, example:singapore
}
```

### 4.4 更新 config.py

```python
SITE_CONFIGS = {
    # ... existing
    "example": {
        "name": "Example Site",
        "base_url": "https://example.com",
        "delay": 0.5,
        "country": "Indonesia",
        "default_city": "",
        "categories": [],
        # 多城市配置（可选）
        "cities": {
            "jakarta": "Indonesia",
            "singapore": "Singapore",
        },
    },
}
```

---

## Phase 5: TEST - 测试验证

### 5.1 基础测试

```bash
# 测试 2 篇文章，详细日志
python main.py -s example -l 2 -v
```

### 5.2 验证项

- [ ] Sitemap 能正确获取 URL 列表
- [ ] URL 过滤规则正确（排除非文章页）
- [ ] 文章标题提取正确
- [ ] 文章内容提取正确（>200 字符）
- [ ] 作者提取正确（或有默认值）
- [ ] 日期提取正确
- [ ] 图片提取正确
- [ ] 分类/标签提取正确

### 5.3 常见问题排查

| 问题 | 可能原因 | 解决方案 |
|------|----------|----------|
| 403 错误 | 网站有反爬 | 检查 curl_cffi 是否正常，或换用 Playwright |
| 0 篇文章 | URL 过滤规则太严格 | 放宽 `is_valid_article_url()` |
| 内容为空 | 选择器不对 | 更新 `extract_content()` 选择器 |
| 日期为空 | JSON-LD 或选择器不对 | 检查 `_parse_json_ld()` 或日期选择器 |
