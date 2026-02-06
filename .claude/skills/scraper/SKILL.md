---
name: scraper
description: Use when user wants to build new scrapers, run existing scrapers, check scraper health, or view BigQuery data status. Triggers on phrases like "新增爬虫", "添加网站", "运行爬虫", "爬取数据", "检查爬虫", "爬虫状态", "查看数据", "哪些需要更新", "增量爬取", or when user provides a website URL for scraping.
version: 2.0.0
---

# Scraper Management Skill

多网站文章爬虫管理系统。

## 子命令

| 命令 | 说明 | 触发词 |
|------|------|--------|
| `/scraper:build <url>` | 构建新爬虫 | "新增爬虫", "添加网站", 或提供 URL |
| `/scraper:run [name]` | 运行爬虫 | "运行爬虫", "爬取数据" |
| `/scraper:health [name]` | 健康检查 | "检查爬虫", "爬虫状态" |
| `/scraper:status` | BigQuery 数据状态 | "查看数据", "哪些需要更新" |

## 自动路由

根据用户输入自动选择子命令：

| 用户输入 | 路由到 |
|----------|--------|
| 提供网站 URL 要求爬取 | `/scraper:build` |
| "运行爬虫"、"爬取数据" | `/scraper:run` |
| "检查爬虫"、"爬虫状态" | `/scraper:health` |
| "查看数据"、"哪些需要更新" | `/scraper:status` |

## 数据优先级

- 🔴 从未爬取 - 全量爬取
- 🟡 超60天未更新 - 增量爬取
- 🟢 正常 - 可选更新

## References

- [Build Flow](references/build-flow.md) - 构建流程
- [Selectors](references/selectors.md) - 常见选择器
- [Templates](references/templates/) - 代码模板
