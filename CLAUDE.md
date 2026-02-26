# Global Article Scraper

多网站文章爬虫系统，64 个爬虫（53 Sitemap + 10 Pagination + 1 Playwright），按国家/地区分目录

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
| `scrapers/__init__.py` | SCRAPER_REGISTRY / COUNTRY_SCRAPERS / PARAMETERIZED_SCRAPERS |

**爬虫必须实现**：
- `fetch_urls_from_sitemap()` - 获取 URL 列表
- `is_valid_article_url(url)` - 过滤有效文章
- `extract_content(html)` - 提取正文
- `parse_article(html, url)` - 解析文章

## 目录结构

```
scrapers/
├── __init__.py              # 中央注册表
├── indonesia/   (24个)      # 印尼 + 巴厘岛
├── singapore/   (8个)
├── thailand/    (3个)
├── malaysia/    (2个)
├── philippines/ (2个)
├── vietnam/     (1个)
├── taiwan/      (2个)
├── hongkong/    (1个)
└── worldwide/   (21个)      # 跨国/全球站点
```

## 爬虫列表

### Indonesia (24个)
| 爬虫 | 网站 | 类型 | 备注 |
|------|------|------|------|
| manual_jakarta | manual.co.id | sitemap | |
| now_jakarta | nowjakarta.co.id | sitemap | |
| flokq_blog | flokq.com/blog | sitemap | 印尼语 |
| feastin | feastin.id | sitemap | Squarespace |
| exquisite_taste | exquisite-taste-magazine.com | sitemap | |
| wandernesia | wandernesia.com | sitemap | |
| bali_food_travel | balifoodandtravel.com | sitemap | Rank Math |
| ekaputrawisata | ekaputrawisata.com | sitemap | Rank Math |
| hotelier | hotelier.id | sitemap | |
| kompas_food | kompas.com/food | sitemap | News sitemap |
| indoindians | indoindians.com | sitemap | Yoast |
| indonesia_expat | indonesiaexpat.id | sitemap | |
| idntimes | idntimes.com | sitemap | :city |
| whats_new_indonesia | whatsnewindonesia.com | sitemap | :city |
| makanmana | makanmana.net | sitemap | |
| jakarta_post_food | thejakartapost.com | sitemap | |
| onbali | onbali.com | sitemap | |
| urbanicon | magazine.urbanicon.co.id | sitemap | |
| aperitif | aperitif.com | sitemap | Yoast, Bali fine dining |
| detik_food | food.detik.com | sitemap | CDATA, 印尼语 |
| alinear | alinear.id | pagination | |
| nibble | nibble.id | pagination | |
| weekender | weekender.co.id | pagination | |
| tripcanvas | indonesia.tripcanvas.co | playwright | |

### Singapore (8个)
| 爬虫 | 网站 | 类型 | 备注 |
|------|------|------|------|
| eatbook | eatbook.sg | sitemap | |
| miss_tam_chiak | misstamchiak.com | sitemap | |
| daniel_food_diary | danielfooddiary.com | sitemap | |
| urban_list_sg | theurbanlist.com | sitemap | |
| alexis_cheong | alexischeong.com | sitemap | |
| hungrygowhere | hungrygowhere.com | sitemap | Next.js SSR |
| lady_iron_chef | ladyironchef.com | pagination | |
| seth_lui | sethlui.com | sitemap | Elementor + Yoast |

### Thailand (3个)
| 爬虫 | 网站 | 类型 |
|------|------|------|
| bkkfoodie | bkkfoodie.com | sitemap |
| bangkok_foodies | bangkokfoodies.com | sitemap |
| clever_thai | cleverthai.com | sitemap |

### Malaysia (2个)
| 爬虫 | 网站 | 类型 |
|------|------|------|
| kl_foodie | klfoodie.com | sitemap |
| malaysian_foodie | malaysianfoodie.com | sitemap |

### Philippines (2个)
| 爬虫 | 网站 | 类型 | 备注 |
|------|------|------|------|
| booky_ph | booky.ph/blog | pagination | |
| guide_to_ph | guidetothephilippines.ph | sitemap | Next.js SSR + JSON-LD |

### Vietnam (1个)
| 爬虫 | 网站 | 类型 |
|------|------|------|
| vietnam_insiders | vietnaminsiders.com | sitemap |

### Taiwan (2个)
| 爬虫 | 网站 | 类型 |
|------|------|------|
| eating_in_taipei | eatingintaipei.com | sitemap |
| openrice_tw | openrice.com | pagination |

### Hong Kong (1个)
| 爬虫 | 网站 | 类型 |
|------|------|------|
| openrice_hk | openrice.com | pagination |

### Worldwide (21个)
| 爬虫 | 网站 | 类型 | 备注 |
|------|------|------|------|
| timeout | timeout.com | sitemap | :city |
| culture_trip | theculturetrip.com | sitemap | :city |
| chope | chope.co | sitemap | :city |
| honeycombers | thehoneycombers.com | sitemap | :city |
| the_asia_collective | theasiacollective.com | sitemap | Yoast |
| tourteller | tourteller.com | sitemap | |
| renaesworld | renaesworld.com.au | sitemap | CDATA |
| lepetitchef | lepetitchef.co.id | sitemap | |
| will_fly_for_food | willflyfor.food | sitemap | |
| elite_havens | elitehavens.com | sitemap | |
| food_fun_travel | foodfuntravel.com | sitemap | |
| michelin_guide | guide.michelin.com | sitemap | |
| asias_50_best | theworlds50best.com | sitemap | |
| eater | eater.com | sitemap | |
| destinasian | destinasian.com | sitemap | Next.js Apollo |
| travel_leisure_asia | travelandleisureasia.com | sitemap | :region, 20k+ articles |
| girl_on_a_zebra | girlonazebra.com | sitemap | Rank Math |
| hey_roseanne | heyroseanne.com | sitemap | Rank Math, Korea |
| lonely_planet | lonelyplanet.com | sitemap | :continent |
| tatler_asia | tatlerasia.com | pagination | |
| cnn_travel | cnn.com/travel | pagination | |

### 参数化爬虫
```
chope:jakarta, chope:bali, chope:singapore
timeout:jakarta, timeout:singapore, timeout:hong-kong
culture_trip:jakarta, culture_trip:tokyo, culture_trip:seoul
whats_new_indonesia:jakarta, whats_new_indonesia:bali
honeycombers:singapore, honeycombers:bali, honeycombers:hong-kong
idntimes:bali, idntimes:jabar
lonely_planet:asia, lonely_planet:europe, lonely_planet:africa
travel_leisure_asia:sea, travel_leisure_asia:sg, travel_leisure_asia:hk, travel_leisure_asia:th, travel_leisure_asia:my
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
STORAGE_CONFIG = {
    "bigquery": {
        "project_id": "oppo-gcp-prod-digfood-129869",
        "dataset": "maomao_poi_external_data",
        "table": "global_articles",
    },
}
```

### 代理
```python
PROXY_CONFIG = {
    "enabled": True,
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
