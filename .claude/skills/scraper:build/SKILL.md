---
name: scraper:build
description: 构建新爬虫。分析网站结构，自动生成爬虫代码。触发词："新增爬虫", "添加网站", "build scraper"，或者用户提供一个网站 URL 要求爬取。
version: 1.0.0
---

# Scraper Build Skill

构建新爬虫，分析网站结构并自动生成代码。

## Usage

```bash
/scraper:build <url>      # 构建新爬虫
```

---

## Workflow

```
1. EXPLORE - 探索目标网站
   ├── 检查 robots.txt
   ├── 检查 sitemap.xml / sitemap_index.xml
   ├── 识别 sitemap 格式（标准/Yoast/News/CDATA）
   ├── 如果无 sitemap，检测分页 URL 模式
   └── 测试 curl_cffi 能否绕过反爬（403 检测）

2. VALIDATE - 验证网站质量 ⚠️ 前置条件（双重验证）
   │
   ├── 2a. 活跃度验证
   │   ├── 从 sitemap 或首页获取最新文章日期
   │   │   └── 检查 <lastmod>、URL 中的日期、或文章页面的发布日期
   │   ├── 判断最新文章是否在 2025 年或之后
   │   │   ├── ✅ 2025+ → 继续
   │   │   └── ⚠️ 2024 或更早 → 需要用户确认
   │   └── 如果需要确认，使用 AskUserQuestion:
   │       "该网站最新文章发布于 {日期}，可能已停止更新。是否继续创建爬虫？"
   │       - 选项1: 继续创建（网站仍有价值）
   │       - 选项2: 取消（不值得维护）
   │
   └── 2b. POI 内容验证 ⚠️ 关键检查（三级判断，由粗到细）
       │
       ├── Level 1: URL 模式批量扫描（快速，不需要请求文章）
       │   ├── 从 sitemap 获取全部 URL，分析路径模式
       │   ├── ❌ 食谱站特征 URL: /recipe/, /resep/, /cara-membuat/, /resepi/
       │   ├── ✅ POI 站特征 URL: /restaurant/, /review/, /cafe/, /hotel/,
       │   │   /best-/, /top-/, /guide/, /where-to-/
       │   └── 如果 URL 模式就能明确判断 → 跳过 Level 2/3
       │
       ├── Level 2: JSON-LD Schema 类型检测（ANALYZE 阶段顺带做）
       │   ├── ❌ @type: "Recipe" → 食谱站，直接拒绝
       │   ├── ✅ @type: "Article"/"BlogPosting"/"Restaurant"/"LocalBusiness" → POI 站
       │   └── 无 JSON-LD → 进入 Level 3
       │
       └── Level 3: 最新文章内容抽检（仅在 Level 1/2 无法判断时）
           ├── 取 sitemap 中 lastmod 最新的 2 篇文章
           ├── 语言无关的 POI 信号检测：
           │   ├── 地址模式: 含街道号码、邮编、Google Maps 链接/嵌入
           │   ├── 联系信息: 电话号码模式（+62/+65/+66 等）、营业时间格式
           │   ├── 具体店名: 文章标题或 H2/H3 中出现专有名词（大写开头）
           │   └── 榜单格式: 编号列表 (1. xxx, 2. xxx) + 配图
           └── 结果处理：
               ├── ✅ 有 POI 信号 → 继续构建
               ├── ⚠️ 不确定 → AskUserQuestion 确认
               └── ❌ 无 POI 信号 → 拒绝并说明原因

3. ANALYZE - 分析网站结构
   ├── 识别多城市/多语言支持
   ├── 从 sitemap 提取 URL 模式和 categories
   ├── 随机抽取 3 篇文章分析 HTML 结构
   ├── 检查 JSON-LD 结构化数据（@graph 格式）
   └── 确定语言和国家/地区

4. GENERATE - 生成代码
   ├── 根据分析结果选择模板（见 references/templates/）
   ├── 自动填充 sitemap URL
   ├── 自动填充 URL 过滤规则
   ├── 自动填充内容选择器
   ├── 自动填充 JSON-LD 解析逻辑
   └── 生成 config.py 配置片段

5. REGISTER - 注册爬虫
   ├── 创建爬虫文件到 scrapers/sitemap/ 或 scrapers/playwright/
   ├── 更新 scrapers/sitemap/__init__.py
   ├── 更新 scrapers/__init__.py (SCRAPER_REGISTRY, SITEMAP_SCRAPERS)
   └── 更新 config.py (SITE_CONFIGS)

6. TEST - 测试验证
   └── 运行 python main.py -s <name> -l 2 -v
```

## Template Selection

| Sitemap 格式 | 模板文件 | 特征 |
|--------------|----------|------|
| 标准 XML | `sitemap_standard.py.tpl` | `<urlset>` 根元素 |
| Yoast SEO | `sitemap_yoast.py.tpl` | `post-sitemap.xml`，JSON-LD @graph |
| Google News | `sitemap_news.py.tpl` | `<news:news>` 命名空间 |
| CDATA 包装 | `sitemap_cdata.py.tpl` | `<![CDATA[...]]>` 包裹 |
| 无 Sitemap | `pagination.py.tpl` | 分页 URL 模式 `/page/2/` |
| 多城市 | `multi_city.py.tpl` | 需要 city 参数 |

## Key References

- [Build Flow](../scraper/references/build-flow.md) - 详细构建流程
- [Selectors](../scraper/references/selectors.md) - 常见 HTML 选择器
- [Templates](../scraper/references/templates/) - 代码模板

## Important Notes

### curl_cffi TLS Fingerprint

**CRITICAL**: `base_scraper.py` 使用 `curl_cffi` 的 `impersonate="chrome"` 模式。
- **不要**手动设置 User-Agent，会破坏 TLS 指纹匹配
- 大部分 Cloudflare 保护的网站都可以用 curl_cffi 绕过
- 只有真正需要 JS 渲染的网站才用 PlaywrightScraper

### Request Priority

```
BaseScraper (curl_cffi) > PlaywrightScraper
```

### File Locations

```
scrapers/
├── __init__.py           # SCRAPER_REGISTRY, PARAMETERIZED_SCRAPERS
├── sitemap/              # BaseScraper 爬虫
│   ├── __init__.py
│   └── *.py
└── playwright/           # PlaywrightScraper 爬虫
    ├── __init__.py
    └── *.py

config.py                 # SITE_CONFIGS, BQ_CONFIG, PROXY_CONFIG
```
