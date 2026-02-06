---
name: scraper:run
description: 运行爬虫。交互式选择爬虫并执行。触发词："运行爬虫", "爬取数据", "run scraper"。
version: 2.1.0
---

# Scraper Run Skill

交互式选择并执行爬虫，包含预检机制确保数据质量。

## Usage

```bash
/scraper:run [name]       # 运行爬虫（可选指定名称）
```

---

## Interactive Flow

```
1. SELECT - 选择爬虫
   ├── 如果指定了 name，直接使用
   ├── 否则执行 python main.py --list 显示列表
   ├── 如果是参数化爬虫（chope/timeout/honeycombers 等）
   │   └── AskUserQuestion: 选择城市
   └── 进入下一步

2. CONFIGURE - 配置增量日期
   └── AskUserQuestion: 输入 --since 日期
       ├── 默认: 2024-01-01
       └── 用户可自定义日期

3. PREVIEW - 预检运行 ⚠️ 重要步骤
   ├── 执行: python main.py -s <name> --since <date> -l 5 -v
   ├── 读取输出的 JSON 文件
   └── 检查以下字段质量:
       ┌─────────────┬─────────────────────────────────────────────────┐
       │ 字段         │ 检查项                                           │
       ├─────────────┼─────────────────────────────────────────────────┤
       │ content     │ 是否包含正文（长度 > 200 字符）                    │
       │ publish_date│ 是否有值且格式正确（YYYY-MM-DD）                   │
       │ category    │ 是否与网站分类一致（非空、非乱码）                  │
       │ country     │ ⚠️ 必须有值！检查是否在 LOCATION_MAP 中           │
       │ city        │ 检查是否在 LOCATION_MAP 中（可为空但需匹配）       │
       └─────────────┴─────────────────────────────────────────────────┘

4. VALIDATE - 展示预检结果
   ├── 以表格形式展示 5 篇文章的字段质量
   │   ├── ✅ 正常: 字段值正确且在 LOCATION_MAP 中
   │   ├── ⚠️ 警告: 字段值可疑（如 content 过短）
   │   ├── ❌ 错误: 字段值错误或缺失
   │   └── 🆕 新增: country/city 不在 LOCATION_MAP 中
   │
   ├── 如果发现 🆕 新的 country/city:
   │   ├── 提示: "发现新地点: {country}/{city}，需要更新 locations"
   │   ├── 自动更新 utils/locations.py:
   │   │   ├── 在 LOCATION_MAP 中添加新的 city → (country, city) 映射
   │   │   └── 在 COUNTRY_NAMES 中添加新的国家（如果是新国家）
   │   └── 显示更新内容让用户确认
   │
   ├── AskUserQuestion: 用户确认是否继续
   │   ├── 继续执行 → 进入 EXECUTE 步骤
   │   ├── 修改参数 → 返回 CONFIGURE 步骤
   │   └── 取消 → 结束流程
   └── 如果有 ❌ 错误（country 为空），强烈建议用户取消并修复爬虫

5. EXECUTE - 正式执行
   ├── 构建命令:
   │   python main.py -s <name> --since <date> --bq --no-json [-p]
   │   └── -p: 如果 PROXY_CONFIG["enabled"] = True，自动添加
   ├── 执行爬取
   └── 监控进度，显示实时日志

6. SUMMARY - 输出数据总结
   ├── 爬取统计:
   │   ├── 总文章数
   │   ├── 成功/失败数
   │   ├── 耗时
   │   └── 写入 BQ 的记录数
   └── 下一步建议（如有失败文章，建议重试）
```

## Parameters Reference

| 参数 | 说明 | 示例 |
|------|------|------|
| `-s <name>` | 爬虫名称 | `-s honeycombers:singapore` |
| `-l <num>` | 限制文章数 | `-l 5` |
| `--bq` | 写入 BigQuery | `--bq` |
| `--no-json` | 不输出 JSON 文件 | `--no-json` |
| `--since <date>` | 增量爬取 | `--since 2024-01-01` |
| `-p` | 启用代理 | `-p` |
| `-v` | 详细日志 | `-v` |

## Preview Validation Rules

```python
from utils.locations import LOCATION_MAP, COUNTRY_NAMES

# 字段验证规则
validation_rules = {
    "content": {
        "check": lambda x: len(x or "") > 200,
        "error": "正文为空或过短",
        "warning_threshold": 500,  # 低于此值显示警告
    },
    "publish_date": {
        "check": lambda x: bool(re.match(r"\d{4}-\d{2}-\d{2}", x or "")),
        "error": "发布日期缺失或格式错误",
    },
    "category": {
        "check": lambda x: bool(x) and x != "uncategorized",
        "error": "分类为空",
        "warning": "分类为 uncategorized",
    },
    "country": {
        "check": lambda x: bool(x),  # ⚠️ country 必须有值！
        "error": "❌ country 为空，必须修复爬虫",
        "location_check": lambda x: x.lower() in COUNTRY_NAMES,
        "new_location": "🆕 新国家，需更新 COUNTRY_NAMES",
    },
    "city": {
        "check": lambda x: True,  # city 可以为空
        "location_check": lambda x: x.lower() in [loc for loc in LOCATION_MAP],
        "new_location": "🆕 新城市，需更新 LOCATION_MAP",
    },
}
```

## Location Update Logic

当发现新的 country/city 时，自动更新 `utils/locations.py`:

```python
# 1. 收集预检中发现的新地点
new_locations = []
for article in articles:
    country = article.get("country", "")
    city = article.get("city", "")

    # 检查 country 是否在 COUNTRY_NAMES 中
    if country and country.lower() not in COUNTRY_NAMES:
        new_locations.append(("country", country))

    # 检查 city 是否在 LOCATION_MAP 中
    if city and city.lower() not in LOCATION_MAP:
        new_locations.append(("city", city, country))

# 2. 如果有新地点，提示并更新
if new_locations:
    print("🆕 发现新地点，需要更新 utils/locations.py:")
    for loc in new_locations:
        if loc[0] == "country":
            # 添加到 COUNTRY_NAMES
            print(f"   - 新国家: {loc[1]} → 添加到 COUNTRY_NAMES")
        else:
            # 添加到 LOCATION_MAP
            print(f'   - 新城市: "{loc[1].lower()}": ("{loc[2]}", "{loc[1]}")')

    # 自动编辑 utils/locations.py 添加新地点
```

## Preview Output Format

```
预检结果 (5 篇文章)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  标题                    content  publish_date  category  country     city
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1  Best Cafes in Jakarta   ✅ 1.2k  ✅ 2025-01-15  ✅ food   ✅ Indonesia ✅ Jakarta
2  Weekend Brunch Guide    ✅ 890   ✅ 2025-01-10  ✅ dining ✅ Indonesia ✅ Jakarta
3  Hidden Gems in Medan    ⚠️ 450   ✅ 2025-01-08  ✅ travel ✅ Indonesia 🆕 Medan
4  New Restaurant Opens    ❌ 0     ❌ null        ⚠️ news  ❌ null      - (空)
5  Top 10 Bars             ✅ 2.1k  ✅ 2025-01-05  ✅ bars   ✅ Indonesia ✅ Jakarta
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
汇总: ✅ 3 正常 | ⚠️ 1 警告 | ❌ 1 错误 | 🆕 1 新地点

❌ 发现 1 个错误 (country 为空)，必须修复爬虫后再执行！

🆕 发现新地点，需要更新 utils/locations.py:
   - 新城市: "medan": ("Indonesia", "Medan")
```

## Proxy Auto-Detection

```python
# 从 config.py 读取代理配置
from config import PROXY_CONFIG

if PROXY_CONFIG.get("enabled", False):
    # 自动添加 -p 参数
    cmd += " -p"
```

## Parameterized Scrapers

从 `scrapers/__init__.py` 的 `PARAMETERIZED_SCRAPERS` 获取支持参数的爬虫：
- `chope`: city (jakarta, bali, singapore...)
- `timeout`: city (jakarta, singapore, hong-kong...)
- `culture_trip`: city (jakarta, tokyo, seoul...)
- `whats_new_indonesia`: city (jakarta, bali, yogyakarta...)
- `honeycombers`: city (singapore, bali, hong-kong)
