# Global Article Scraper

一个高效的多网站文章爬虫系统，专注于东南亚及亚太地区的生活方式、旅游、美食内容抓取。

## 特性

- **64 个爬虫**：覆盖 9 个国家/地区的主流生活方式媒体（53 Sitemap + 10 Pagination + 1 Playwright）
- **智能反爬绕过**：使用 curl_cffi TLS 指纹伪装，可绕过大部分 Cloudflare 保护
- **多模式爬取**：支持 Sitemap、Google News Sitemap、CDATA Sitemap、分页列表、Playwright 等
- **多城市/多区域参数化**：部分爬虫支持城市/区域参数，如 `honeycombers:singapore`、`travel_leisure_asia:sg`
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
python main.py -s eatbook -l 100 -v

# 多城市爬虫
python main.py -s honeycombers:singapore -l 50

# 多区域爬虫
python main.py -s travel_leisure_asia:sg -l 50

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

### 按地区分布

| 地区 | 爬虫数量 | 覆盖网站 |
|------|---------|---------|
| 🇮🇩 Indonesia | 24 | Manual Jakarta, Detik Food, Kompas Food, Aperitif 等 |
| 🇸🇬 Singapore | 8 | Eatbook, Seth Lui, HungryGoWhere, Miss Tam Chiak 等 |
| 🇹🇭 Thailand | 3 | BKK Foodie, Bangkok Foodies, Clever Thai |
| 🇲🇾 Malaysia | 2 | KL Foodie, Malaysian Foodie |
| 🇵🇭 Philippines | 2 | Booky PH, Guide to PH |
| 🇻🇳 Vietnam | 1 | Vietnam Insiders |
| 🇹🇼 Taiwan | 2 | Eating in Taipei, OpenRice TW |
| 🇭🇰 Hong Kong | 1 | OpenRice HK |
| 🌏 Worldwide | 21 | Michelin Guide, Eater, CNN Travel, Travel+Leisure Asia 等 |

### 参数化爬虫

| 爬虫 | 网站 | 参数类型 | 支持的值 |
|------|------|----------|---------|
| honeycombers | thehoneycombers.com | city | singapore, bali, hong-kong |
| chope | chope.co | city | jakarta, bali, singapore, bangkok |
| timeout | timeout.com | city | jakarta, singapore, hong-kong |
| culture_trip | theculturetrip.com | city | jakarta, tokyo, seoul, bali |
| travel_leisure_asia | travelandleisureasia.com | region | sea, sg, hk, th, my |
| lonely_planet | lonelyplanet.com | continent | asia, europe, africa |
| whats_new_indonesia | whatsnewindonesia.com | city | jakarta, bali |
| idntimes | idntimes.com | city | bali, jabar |

完整列表请运行 `python main.py --list`

## 配置

编辑 `config.py` 配置以下内容：

```python
# BigQuery 配置
STORAGE_CONFIG = {
    "bigquery": {
        "project_id": "your-gcp-project",
        "dataset": "your-dataset",
        "table": "articles",
    },
}

# 代理配置
PROXY_CONFIG = {
    "proxies": ["http://proxy1:port", "http://proxy2:port"],
}
```

## 项目结构

```
global-article-scraper/
├── main.py                 # CLI 入口
├── base_scraper.py         # 爬虫基类 (BaseScraper / PlaywrightScraper)
├── config.py               # 站点配置、存储配置、代理配置
├── scrapers/
│   ├── __init__.py         # 爬虫注册表 (SCRAPER_REGISTRY / COUNTRY_SCRAPERS)
│   ├── indonesia/          # 印尼爬虫 (24个)
│   ├── singapore/          # 新加坡爬虫 (8个)
│   ├── thailand/           # 泰国爬虫 (3个)
│   ├── malaysia/           # 马来西亚爬虫 (2个)
│   ├── philippines/        # 菲律宾爬虫 (2个)
│   ├── vietnam/            # 越南爬虫 (1个)
│   ├── taiwan/             # 台湾爬虫 (2个)
│   ├── hongkong/           # 香港爬虫 (1个)
│   └── worldwide/          # 跨国/全球爬虫 (21个)
├── utils/
│   ├── bq_writer.py        # BigQuery 写入模块
│   └── locations.py        # 城市/国家识别
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

#### 3. `/scraper health [name]` - 健康检查

检测网站是否改版，爬虫是否还能正常工作。

#### 4. `/scraper status` - BigQuery 数据状态

查询 BigQuery 中各爬虫的数据现状，按优先级排序。

---

## 技术栈

- **HTTP 请求**：curl_cffi（TLS 指纹伪装）
- **浏览器自动化**：Playwright（仅用于需要 JS 渲染的网站）
- **HTML 解析**：BeautifulSoup4
- **数据存储**：BigQuery / JSON
- **AI 辅助**：Claude Code Skill

## License

MIT
