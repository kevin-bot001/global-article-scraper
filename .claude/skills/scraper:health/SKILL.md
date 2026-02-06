---
name: scraper:health
description: 爬虫健康检查。检测网站是否改版、爬虫是否正常工作。触发词："检查爬虫", "爬虫状态", "health check"。
version: 1.0.0
---

# Scraper Health Skill

检测网站是否改版、爬虫是否正常工作。

## Usage

```bash
/scraper:health [name]    # 健康检查（可选指定名称，不指定则检查全部）
```

---

## Check Items

```
1. SITEMAP CHECK - Sitemap 可访问性
   ├── HTTP 状态码（200/403/404/500）
   ├── 响应时间
   └── 文章数量（对比上次记录）

2. SAMPLE CHECK - 随机抽样 3 篇文章
   ├── 页面可访问性（HTTP 状态码）
   ├── 内容选择器是否匹配
   ├── 提取内容长度是否合理（>200 字符）
   └── JSON-LD 结构是否变化

3. REPORT - 输出健康报告
   ├── ✅ 健康: 一切正常
   ├── ⚠️ 警告: 部分异常（文章数骤降、响应慢）
   └── ❌ 故障: 爬虫无法工作（403、选择器失效）

4. SUGGEST - 建议操作
   ├── 健康: 可以正常爬取
   ├── 警告: 建议人工检查网站
   └── 故障: 需要更新爬虫代码（重新 build）
```

## Health Status Storage

```
.scraper-health/
├── last_check.json       # 上次检查结果
└── sitemap_counts.json   # 各爬虫 sitemap 文章数历史
```

## Health Status Levels

| 状态 | 符号 | 条件 | 建议操作 |
|------|------|------|----------|
| 健康 | ✅ | 一切正常 | 可以正常爬取 |
| 警告 | ⚠️ | 部分异常（文章数骤降、响应慢） | 建议人工检查网站 |
| 故障 | ❌ | 爬虫无法工作（403、选择器失效） | 需要重新 build |
