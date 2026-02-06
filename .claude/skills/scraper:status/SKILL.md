---
name: scraper:status
description: 查询 BigQuery 数据状态，显示各爬虫数据现状和优先级。触发词："查看数据", "哪些需要更新", "数据状态", "scraper status"。
version: 1.0.0
---

# Scraper Status Skill

查询 BigQuery 数据状态，显示各爬虫数据现状和优先级。

## Usage

```bash
/scraper:status           # 查询 BigQuery 数据状态
```

---

## Query Logic

```python
# 1. 获取已注册爬虫列表
from scrapers import SCRAPER_REGISTRY
registered_scrapers = list(SCRAPER_REGISTRY.keys())

# 2. 查询 BigQuery
# 注意: 实际字段是 create_time，不是 scraped_at
SELECT
  source,
  COUNT(*) as total_articles,
  MAX(publish_date) as latest_publish_date,
  MAX(create_time) as last_scraped_at,
  COUNT(DISTINCT category) as categories
FROM `{project}.{dataset}.{table}`
GROUP BY source
ORDER BY last_scraped_at DESC

# 3. 对比生成优先级列表
# 注意: BQ 中的 source 是显示名称（如 "Urban Icon Magazine"）
# 需要与 SITE_CONFIGS 中的 name 字段映射到 SCRAPER_REGISTRY 的 key（如 "urbanicon"）
```

## BigQuery Table Schema

```
字段名         | 类型       | 说明
--------------|-----------|------------------
url           | STRING    | 文章 URL (REQUIRED)
source        | STRING    | 来源名称，对应 SITE_CONFIGS 的 name 字段 (REQUIRED)
country       | STRING    | 国家
city          | STRING    | 城市
title         | STRING    | 标题
content       | STRING    | 正文
content_md    | STRING    | Markdown 格式正文
author        | STRING    | 作者
publish_date  | DATE      | 发布日期（分区字段）
category      | STRING    | 分类
tags          | STRING[]  | 标签
images        | STRING[]  | 图片 URL 列表
language      | STRING    | 语言
create_time   | TIMESTAMP | 爬取时间（用于判断上次更新）
raw_html      | STRING    | 原始 HTML
```

## Priority Levels

| 优先级 | 状态 | 条件 | 建议操作 |
|--------|------|------|----------|
| 🔴 最高 | 从未爬取 | BQ 中无数据 | 全量爬取（无 --since） |
| 🟡 高 | 超过60天未更新 | last_scraped_at < now - 60d | 增量爬取（--since = last_scraped_at） |
| 🟢 正常 | 近期已更新 | last_scraped_at >= now - 60d | 可选更新 |

## Output Format

```
爬虫数据状态 (BigQuery: project.dataset.table)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
状态  爬虫              文章数    最新发布      上次爬取      分类
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔴   alinear           -         -            从未爬取      -
🔴   urbanicon         -         -            从未爬取      -
🟡   renaesworld       500       2025-11-01   2025-12-01    15
🟡   hotelier          2,000     2025-10-15   2025-11-20    8
🟢   honeycombers      3,917     2026-02-01   2026-02-02    12
🟢   migrationology    971       2026-01-28   2026-02-01    8
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

建议操作:
- 🔴 从未爬取 (2个): alinear, urbanicon
- 🟡 超过60天 (2个): renaesworld, hotelier
```

## User Actions (AskUserQuestion)

```
选择操作:
1. 快速模式 - 爬取所有 🔴 + 🟡 (4个爬虫)
2. 选择模式 - 手动选择要爬取的爬虫
3. 仅查看 - 不执行任何操作
```

## BigQuery Config

从 `config.py` 的 `STORAGE_CONFIG["bigquery"]` 读取配置：
```python
STORAGE_CONFIG = {
    "bigquery": {
        "project_id": "oppo-gcp-prod-digfood-129869",
        "dataset": "maomao_poi_external_data",
        "table": "global_articles",
    },
}
```

**bq 命令示例**：
```bash
bq query --use_legacy_sql=false --format=prettyjson '
SELECT source, COUNT(*) as total_articles, ...
FROM `oppo-gcp-prod-digfood-129869.maomao_poi_external_data.global_articles`
GROUP BY source
'
```
