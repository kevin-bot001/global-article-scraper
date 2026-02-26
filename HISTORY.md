# 项目历史改动记录

## 2026-02-02: 城市识别逻辑优化

**问题**：wandernesia 配置 city=Bali，但爬到 Jakarta 文章时 city 字段错误

**改动**：
1. `default_city` → `city`（语义更清晰）
2. 城市识别优先级改为：**标题/URL识别 > 配置默认值**
3. `detect_location_from_title()` 方法增加 URL 参数，同时从标题和 URL 提取地名

**效果**：同一爬虫可正确识别不同城市的文章
- Jakarta 文章 → city=Jakarta
- Bali 文章 → city=Bali
- 无法识别时 → 使用配置的默认值

---

## 2026-02-02: curl_cffi User-Agent 问题修复

**问题**：renaesworld 等网站返回 403，curl_cffi 无法绕过

**原因**：`base_scraper.py` 的 `fetch()` 方法手动设置了 User-Agent，破坏了 curl_cffi `impersonate="chrome"` 的 TLS 指纹与 UA 匹配

**修复**：删除 `fetch()` 中的 `headers["User-Agent"] = self._get_random_user_agent()` 行

**教训**：使用 curl_cffi impersonate 模式时，不要手动设置任何会影响 TLS 指纹识别的 header

---

## 2026-02-02: tourteller/ekaputrawisata 从 Playwright 改为 BaseScraper

**原因**：发现 curl_cffi 可以绕过这两个网站的 Cloudflare 保护

**改动**：
- 文件从 `scrapers/playwright/` 移到 `scrapers/sitemap/`
- 基类从 `PlaywrightScraper` 改为 `BaseScraper`
- 更新 `scrapers/__init__.py` 的 `PLAYWRIGHT_SCRAPERS` 集合

---

## 2026-01-xx: 多城市配置简化

**原因**：原来的 cities 配置太复杂，包含多层嵌套

**改动**：
- `cities` 改为简单的 `{city: country}` 映射
- 废弃 `default_city`，必须通过参数指定城市
- 爬虫初始化时直接从 `cities[city]` 获取 country

**之前**：
```python
"cities": {
    "jakarta": {"country": "Indonesia", "region": "Java"},
    "singapore": {"country": "Singapore", "region": ""},
}
```

**之后**：
```python
"cities": {
    "jakarta": "Indonesia",
    "singapore": "Singapore",
}
```

---

## 2026-01-xx: 代理配置类型问题

**问题**：代理不生效

**原因**：`PROXY_CONFIG["enabled"]` 是字符串 `"true"` 而不是布尔值 `True`

**修复**：确保配置值是布尔类型

---

## 2026-02-24: 按国家/地区重新组织目录结构

**改动**：
- 原来的 `scrapers/sitemap/`, `scrapers/pagination/`, `scrapers/playwright/` 按爬取模式分目录
- 改为按国家/地区分目录: `scrapers/indonesia/`, `scrapers/singapore/`, `scrapers/worldwide/` 等
- 所有爬虫移到对应国家目录，同一目录下混合 sitemap/pagination/playwright 类型

**效果**：目录结构更清晰，按地区管理爬虫

---

## 新增爬虫记录

### 2026-02-24 批次 (8个新爬虫)
- hungrygowhere (新加坡餐厅搜索，Next.js SSR，sitemap)
- destinasian (亚洲高端旅行杂志，Next.js Apollo 状态解析，sitemap)
- guide_to_ph (菲律宾旅游指南，Next.js SSR + JSON-LD，sitemap，~465 articles)
- travel_leisure_asia (亚洲旅行杂志，参数化 :region，5 个区域，sitemap，20k+ articles)
- girl_on_a_zebra (亚太旅行博客，Rank Math，sitemap，~403 articles)
- hey_roseanne (韩国旅行博客，Rank Math，sitemap，~159 articles)
- aperitif (巴厘岛精品餐饮博客，Yoast + Gutenberg，sitemap，~128 articles)
- detik_food (印尼美食门户，CDATA sitemap，JSON-LD NewsArticle，~200 articles)

### 2026-02-02 批次
- renaesworld (澳洲旅游博客，CDATA sitemap)
- migrationology (Mark Wiens 美食旅游)
- urbanicon (印尼生活方式杂志)
- hotelier (印尼酒店行业新闻)
- kompas_travel (印尼新闻门户，Google News sitemap)
- honeycombers (亚洲生活方式，多城市支持)
- alinear (印尼设计杂志，仅英语)

### 2026-01-xx 批次
- wandernesia
- lepetitchef
- tourteller
- ekaputrawisata
