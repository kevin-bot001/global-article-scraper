# Global Article Scraper

多网站文章爬虫系统，22 个爬虫（20 Sitemap + 1 Pagination + 1 Playwright）

## Skill 命令

```bash
/scraper:build <url>      # 构建新爬虫
/scraper:run [name]       # 运行爬虫
/scraper:health [name]    # 健康检查
/scraper:status           # 查询 BigQuery 数据状态
```

**数据优先级**：🔴 从未爬取 > 🟡 超60天未更新 > 🟢 正常

## 架构

```
BaseScraper (curl_cffi impersonate="chrome") > PlaywrightScraper
```

| 文件 | 说明 |
|------|------|
| `base_scraper.py` | BaseScraper / PlaywrightScraper 基类 |
| `config.py` | SITE_CONFIGS / STORAGE_CONFIG / PROXY_CONFIG |
| `scrapers/__init__.py` | SCRAPER_REGISTRY / PARAMETERIZED_SCRAPERS |

**爬虫必须实现**：
- `fetch_urls_from_sitemap()` - 获取 URL 列表
- `is_valid_article_url(url)` - 过滤有效文章
- `extract_content(html)` - 提取正文
- `parse_article(html, url)` - 解析文章

## 爬虫列表

### Sitemap 模式 (20个)
| 爬虫 | 网站 | 备注 |
|------|------|------|
| manual_jakarta | manual.co.id | |
| now_jakarta | nowjakarta.co.id | |
| timeout | timeout.com | :city |
| whats_new_indonesia | whatsnewindonesia.com | :city |
| flokq_blog | flokq.com/blog | 印尼语 |
| thesmartlocal | thesmartlocal.id | |
| culture_trip | theculturetrip.com | :city |
| chope | chope.co | :city |
| feastin | feastin.id | Squarespace |
| exquisite_taste | exquisite-taste-magazine.com | |
| the_asia_collective | theasiacollective.com | Yoast |
| wandernesia | wandernesia.com | |
| lepetitchef | lepetitchef.co.id | |
| tourteller | tourteller.com | Yoast |
| ekaputrawisata | ekaputrawisata.com | Rank Math |
| renaesworld | renaesworld.com.au | CDATA |
| urbanicon | magazine.urbanicon.co.id | |
| hotelier | hotelier.id | |
| kompas_food | kompas.com/food | News sitemap |
| honeycombers | thehoneycombers.com | :city |
| indoindians | indoindians.com | Yoast |

### Pagination 模式 (1个)
| 爬虫 | 网站 | 备注 |
|------|------|------|
| alinear | alinear.id | F&B 分类分页，仅英语 |

### Playwright 模式 (1个)
| 爬虫 | 网站 |
|------|------|
| tripcanvas | indonesia.tripcanvas.co |

### 参数化爬虫
```
chope:jakarta, chope:bali, chope:singapore
timeout:jakarta, timeout:singapore, timeout:hong-kong
culture_trip:jakarta, culture_trip:tokyo, culture_trip:seoul
whats_new_indonesia:jakarta, whats_new_indonesia:bali
honeycombers:singapore, honeycombers:bali, honeycombers:hong-kong
```

## CLI

```bash
python main.py --list
python main.py -s <scraper> [-l <limit>] [-v] [--bq] [--since <date>] [--proxy]
```

## 配置

### 多城市
```python
"cities": {
    "jakarta": "Indonesia",
    "singapore": "Singapore",
}
```

### BigQuery
```python
# 位于 STORAGE_CONFIG["bigquery"]
STORAGE_CONFIG = {
    "bigquery": {
        "project_id": "oppo-gcp-prod-digfood-129869",
        "dataset": "maomao_poi_external_data",
        "table": "global_articles",  # 字段: url, source, create_time, publish_date...
    },
}
```

### 代理
```python
PROXY_CONFIG = {
    "enabled": True,  # 布尔值
    "proxy_pool_url": "http://xxx",
}
```

## Skill 文件

```
.claude/skills/
├── scraper/                  # 主入口 + 引用
│   ├── SKILL.md
│   └── references/
│       ├── build-flow.md
│       ├── selectors.md
│       └── templates/
├── scraper:build/            # 构建新爬虫
│   └── SKILL.md
├── scraper:run/              # 运行爬虫
│   └── SKILL.md
├── scraper:health/           # 健康检查
│   └── SKILL.md
└── scraper:status/           # BigQuery 数据状态
    └── SKILL.md
```
