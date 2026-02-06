# Global Article Scraper

一个高效的多网站文章爬虫系统，专注于东南亚地区的生活方式、旅游、美食内容抓取。

## 特性

- **23+ 网站支持**：覆盖印尼、新加坡、香港、泰国等地区的主流生活方式媒体
- **智能反爬绕过**：使用 curl_cffi TLS 指纹伪装，可绕过大部分 Cloudflare 保护
- **多模式爬取**：支持 Sitemap、Google News Sitemap、分页列表等多种模式
- **多城市参数化**：部分爬虫支持城市参数，如 `honeycombers:singapore`
- **BigQuery 集成**：支持直接写入 BigQuery，MERGE 策略自动去重
- **增量爬取**：支持 `--since` 参数，只爬取指定日期之后的文章
- **AI 辅助开发**：内置 Claude Code Skill，自然语言构建新爬虫

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 运行爬虫

```bash
# 查看所有可用爬虫
python main.py --list

# 运行单个爬虫
python main.py -s migrationology -l 100 -v

# 多城市爬虫
python main.py -s honeycombers:singapore -l 50

# 写入 BigQuery
python main.py -s hotelier --bq

# 增量爬取
python main.py -s renaesworld --since 2025-01-01 --bq
```

### 命令行参数

| 参数 | 说明 |
|------|------|
| `-s <name>` | 爬虫名称（必需） |
| `-l <num>` | 限制文章数量 |
| `-v` | 详细日志输出 |
| `--bq` | 写入 BigQuery |
| `--since <date>` | 增量爬取，格式 YYYY-MM-DD |
| `--proxy` | 启用代理 |
| `--list` | 列出所有爬虫 |

## 支持的网站

### 多城市爬虫

| 爬虫 | 网站 | 支持城市 |
|------|------|----------|
| honeycombers | thehoneycombers.com | singapore, bali, hong-kong |
| chope | chope.co | jakarta, bali, singapore, bangkok |
| timeout | timeout.com | jakarta, singapore, hong-kong |
| coconuts | coconuts.co | jakarta, singapore, bangkok |
| culture_trip | theculturetrip.com | jakarta, tokyo, seoul, bali |

### 单一网站爬虫

| 爬虫 | 网站 | 地区 |
|------|------|------|
| migrationology | migrationology.com | 全球 |
| renaesworld | renaesworld.com.au | 澳洲/全球 |
| manual_jakarta | manual.co.id | 雅加达 |
| hotelier | hotelier.id | 印尼 |
| kompas_travel | travel.kompas.com | 印尼 |
| alinear | alinear.id | 印尼（英语） |
| ... | ... | ... |

完整列表请运行 `python main.py --list`

## 配置

编辑 `config.py` 配置以下内容：

```python
# BigQuery 配置
BQ_CONFIG = {
    "project": "your-gcp-project",
    "dataset": "your-dataset",
    "table": "articles",
}

# 代理配置
PROXY_CONFIG = {
    "enabled": True,
    "proxy_pool_url": "http://your-proxy-pool",
}
```

## 项目结构

```
global-article-scraper/
├── main.py                 # CLI 入口
├── base_scraper.py         # 爬虫基类
├── config.py               # 配置文件
├── scrapers/
│   ├── __init__.py         # 爬虫注册表
│   ├── sitemap/            # Sitemap 模式爬虫 (22个)
│   └── playwright/         # Playwright 模式爬虫 (1个)
├── utils/
│   └── bq_writer.py        # BigQuery 写入模块
├── .claude/
│   └── skills/scraper/     # Claude Code Skill
├── output/                 # 输出目录
└── requirements.txt
```

---

## Claude Code Skill 使用指引

本项目内置了 `/scraper` Skill，可以通过自然语言与 Claude Code 交互来管理爬虫。

### 前置条件

- 安装 [Claude Code](https://claude.ai/claude-code)
- 在项目目录下启动 Claude Code

### 可用命令

#### 1. `/scraper build <url>` - 构建新爬虫

提供目标网站 URL，自动分析网站结构并生成爬虫代码。

**触发方式**：
```
"帮我新增一个爬虫 https://example.com"
"添加这个网站 https://newsite.com/sitemap.xml"
"/scraper build https://example.com"
```

**自动执行流程**：
1. 探索网站 sitemap 结构
2. 检测多城市/多语言支持
3. 分析文章页 HTML 结构
4. 选择合适的代码模板
5. 生成爬虫代码和配置
6. 注册到 SCRAPER_REGISTRY
7. 运行测试验证

#### 2. `/scraper run [name]` - 运行爬虫

交互式选择爬虫和参数，执行爬取任务。

**触发方式**：
```
"运行 honeycombers 爬虫"
"爬取 migrationology 的最新文章"
"/scraper run"
```

**交互流程**：
1. 显示爬虫列表
2. 选择爬虫（参数化爬虫会追问城市）
3. 配置参数（数量、BigQuery、增量等）
4. 确认并执行

#### 3. `/scraper health [name]` - 健康检查

检测网站是否改版，爬虫是否还能正常工作。

**触发方式**：
```
"检查一下爬虫状态"
"honeycombers 爬虫是否正常"
"/scraper health"
```

**检查项**：
- Sitemap 可访问性
- 文章数量变化
- 内容选择器是否失效
- 随机抽样验证

#### 4. `/scraper status` - BigQuery 数据状态

查询 BigQuery 中各爬虫的数据现状，按优先级排序。

**触发方式**：
```
"查看数据状态"
"哪些爬虫需要更新"
"需要增量爬取哪些"
"/scraper status"
```

**输出示例**：
```
爬虫数据状态
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
状态  爬虫              文章数    上次爬取
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔴   alinear           -         从未爬取
🔴   urbanicon         -         从未爬取
🟡   renaesworld       500       2025-12-01
🟢   honeycombers      3,917     2026-02-02
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

优先级: 🔴 从未爬取 > 🟡 超60天未更新 > 🟢 正常
```

### Skill 文件结构

```
.claude/skills/scraper/
├── SKILL.md                    # 主入口
└── references/
    ├── build-flow.md           # 构建流程详细说明
    ├── selectors.md            # HTML 选择器参考
    └── templates/              # 代码模板
        ├── sitemap_standard.py.tpl
        ├── sitemap_yoast.py.tpl
        ├── sitemap_news.py.tpl
        ├── sitemap_cdata.py.tpl
        ├── pagination.py.tpl
        └── multi_city.py.tpl
```

---

## 技术栈

- **HTTP 请求**：curl_cffi（TLS 指纹伪装）
- **浏览器自动化**：Playwright（仅用于需要 JS 渲染的网站）
- **HTML 解析**：BeautifulSoup4
- **数据存储**：BigQuery / JSON
- **AI 辅助**：Claude Code Skill

## License

MIT
