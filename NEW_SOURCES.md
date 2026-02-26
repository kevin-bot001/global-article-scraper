# 新信源清单

> 最后更新: 2026-02-24 (标记已构建爬虫 + 已排除站点)
> 
> 状态: ✅ 已验证有效 | ❌ 已关站/无法访问 | ⚠️ 需要特殊处理 | 🏗️ 已构建爬虫
>
> **重要**: 🏪 = 有 POI（餐厅名称），适合做榜单 | 🍳 = 食谱/美食文化，无 POI

---

## ⚠️ 重要筛选标准

**做榜单需要 POI（餐厅/店铺名称）！**

- 🏪 **有 POI** = 餐厅评测、榜单、点评平台 → **有用**
- 🍳 **无 POI** = 食谱、烹饪教程、美食文化介绍 → **废物**

---

## 📊 统计摘要

| 分类 | 信源数 | 已构建 | 已排除 | 剩余 |
|------|--------|--------|--------|------|
| 印尼/雅加达 | 13 | 8 | 1 (Qraved) | 4 |
| 巴厘岛 | 3 | 2 | 1 (BFJ 无法访问) | 0 |
| 新加坡 | 9 | 9 | 0 (Burpple 403) | 0 |
| 马来西亚 | 2 | 2 | 0 | 0 |
| 泰国/曼谷 | 4 | 3 | 1 (Hot Thai Kitchen 食谱) | 0 |
| 香港 | 1 | 1 | 0 | 0 |
| 菲律宾 | 3 | 2 | 1 (Patay Gutom 死站) | 0 |
| 越南 | 2 | 1 | 1 (Foody VN 无法访问) | 0 |
| 韩国 | 1 | 0 | 1 (Visit Seoul 出错) | 0 |
| 台湾 | 4 | 2 | 2 (OpenTable/Tiffy 不适合) | 0 |
| 亚洲/国际 | 21 | 14 | 5 | 2 |
| **总计** | **63** | **44** | **12** | **6** |

---

## 🇮🇩 印尼/雅加达 (核心目标)

### 高优先级

| 网站 | URL | POI | 状态 | 备注 |
|------|-----|-----|------|------|
| Nibble | nibble.id | 🏪 | 🏗️ 已构建 | `nibble` (pagination) |
| MakanMana | makanmana.id | 🏪 | 🏗️ 已构建 | `makanmana` (sitemap) |
| Jakarta Post Food | thejakartapost.com | 🏪 | 🏗️ 已构建 | `jakarta_post_food` (sitemap) |
| Weekender | weekender.co.id | 🏪 | 🏗️ 已构建 | `weekender` (pagination) |
| Indonesia Expat | indonesiaexpat.id | 🏪 | 🏗️ 已构建 | `indonesia_expat` (sitemap) |
| Qraved | qraved.com | 🏪 | ❌ 无法访问 | 实测不可用 |
| Detik Food | food.detik.com | 🏪 | 🏗️ 已构建 | `detik_food` (sitemap, CDATA, 筛除食谱) |

### 中优先级

| 网站 | URL | POI | 状态 | 备注 |
|------|-----|-----|------|------|
| Tatler Asia | tatlerasia.com | 🏪 | 🏗️ 已构建 | `tatler_asia` (pagination) |
| Tempo EN | en.tempo.co | ⚠️ | ✅ 未构建 | 混合内容，需筛选 |
| THS Media | thesmedia.id | ⚠️ | ✅ 未构建 | 待验证 |

### 印尼新闻门户 (混合内容)

| 网站 | URL | POI | 状态 | 备注 |
|------|-----|-----|------|------|
| Kompas Travel Food | travel.kompas.com/makan-makan | ⚠️ | ✅ 未构建 | 混合内容 |
| Liputan6 Kuliner | liputan6.com/lifestyle/kuliner | ⚠️ | ✅ 未构建 | 混合内容 |
| Suara Food Travel | suara.com/.../food-travel | ⚠️ | ✅ 未构建 | 混合内容 |

### 已关站

| 网站 | URL | 状态 | 备注 |
|------|-----|------|------|
| PergiKuliner | pergikuliner.com | ❌ | 确认关站 |
| Coconuts | coconuts.co | ❌ | 2023年12月底关站 |

### 需要特殊处理

| 网站 | URL | 需要 | 状态 | 备注 |
|------|-----|------|------|------|
| Tribun Kuliner | tribunnews.com/travel/kuliner | Chrome UA | ✅ 未构建 | |
| Jawa Pos Kuliner | jawapos.com/kuliner | Playwright | ⚠️ 403 | |

---

## 🏝️ 巴厘岛

| 网站 | URL | POI | 状态 | 备注 |
|------|-----|-----|------|------|
| Bali Food Journal | balifoodjournal.com | 🏪 | ❌ 无法访问 | |
| Bali Food & Travel | balifoodandtravel.com | 🏪 | 🏗️ 已构建 | `bali_food_travel` (sitemap) |
| OnBali | onbali.com | 🏪 | 🏗️ 已构建 | `onbali` (sitemap) |

---

## 🇸🇬 新加坡

| 网站 | URL | POI | 状态 | 备注 |
|------|-----|-----|------|------|
| Seth Lui | sethlui.com | 🏪 | 🏗️ 已构建 | `seth_lui` (sitemap) |
| Daniel Food Diary | danielfooddiary.com | 🏪 | 🏗️ 已构建 | `daniel_food_diary` (sitemap) |
| Lady Iron Chef | ladyironchef.com | 🏪 | 🏗️ 已构建 | `lady_iron_chef` (pagination) |
| Burpple | burpple.com | 🏪 | ❌ 403 反爬 | 严格反爬，无法绕过 |
| HungryGoWhere | hungrygowhere.com | 🏪 | 🏗️ 已构建 | `hungrygowhere` (sitemap, Next.js) |
| Eatbook SG | eatbook.sg | 🏪 | 🏗️ 已构建 | `eatbook` (sitemap) |
| Miss Tam Chiak | misstamchiak.com | 🏪 | 🏗️ 已构建 | `miss_tam_chiak` (sitemap) |
| Urban List SG | theurbanlist.com | 🏪 | 🏗️ 已构建 | `urban_list_sg` (sitemap) |
| Alexis Cheong | alexischeong.com | 🏪 | 🏗️ 已构建 | `alexis_cheong` (sitemap) |

---

## 🇲🇾 马来西亚

| 网站 | URL | POI | 状态 | 备注 |
|------|-----|-----|------|------|
| KL Foodie | klfoodie.com | 🏪 | 🏗️ 已构建 | `kl_foodie` (sitemap) |
| Malaysian Foodie | malaysianfoodie.com | 🏪 | 🏗️ 已构建 | `malaysian_foodie` (sitemap) |

---

## 🇹🇭 泰国/曼谷

| 网站 | URL | POI | 状态 | 备注 |
|------|-----|-----|------|------|
| Bangkok Foodie | bkkfoodie.com | 🏪 | 🏗️ 已构建 | `bkkfoodie` (sitemap) |
| Bangkok Foodies | bangkokfoodies.com | 🏪 | 🏗️ 已构建 | `bangkok_foodies` (sitemap) |
| Clever Thai | cleverthai.com | 🏪 | 🏗️ 已构建 | `clever_thai` (sitemap) |
| Hot Thai Kitchen | hot-thai-kitchen.com | 🍳 | ❌ 排除 | 食谱/烹饪教程，无 POI |

---

## 🇭🇰 香港

| 网站 | URL | POI | 状态 | 备注 |
|------|-----|-----|------|------|
| OpenRice HK | openrice.com/en/hongkong | 🏪 | 🏗️ 已构建 | `openrice_hk` (pagination) |

---

## 🇵🇭 菲律宾

| 网站 | URL | POI | 状态 | 备注 |
|------|-----|-----|------|------|
| Booky PH | booky.ph | 🏪 | 🏗️ 已构建 | `booky_ph` (pagination) |
| Guide to PH | guidetothephilippines.ph | 🏪 | 🏗️ 已构建 | `guide_to_ph` (sitemap, Next.js + JSON-LD) |
| Patay Gutom | pataygutom.com | 🏪 | ❌ 死站 | 2013年停更，WordPress 3.9 |

### 需要 Playwright

| 网站 | URL | POI | 状态 | 备注 |
|------|-----|-----|------|------|
| Spot PH | spot.ph | 🏪 | ⚠️ 403 | 需 Playwright |

---

## 🇻🇳 越南

| 网站 | URL | POI | 状态 | 备注 |
|------|-----|-----|------|------|
| Vietnam Insiders | vietnaminsiders.com | 🏪 | 🏗️ 已构建 | `vietnam_insiders` (sitemap) |
| Foody VN | foody.vn | 🏪 | ❌ 无法访问 | robots.txt 返回 404 错误页 |

---

## 🇰🇷 韩国

| 网站 | URL | POI | 状态 | 备注 |
|------|-----|-----|------|------|
| Visit Seoul | english.visitseoul.net | 🏪 | ❌ 不可用 | sitemap 返回韩语错误页 |

### 需要韩国 IP

| 网站 | URL | POI | 状态 | 备注 |
|------|-----|-----|------|------|
| MangoPlate | mangoplate.com | 🏪 | ❌ 000 | 需韩国 IP |
| Siksin | siksin.com | 🏪 | ❌ 000 | 需韩国 IP |

---

## 🇹🇼 台湾

| 网站 | URL | POI | 状态 | 备注 |
|------|-----|-----|------|------|
| OpenRice TW | tw.openrice.com | 🏪 | 🏗️ 已构建 | `openrice_tw` (pagination) |
| Eating in Taipei | eatingintaipei.com | 🏪 | 🏗️ 已构建 | `eating_in_taipei` (sitemap) |
| OpenTable TW | opentable.com/metro/taiwan | 🏪 | ❌ 排除 | 餐厅预订 listing，不是文章 |
| Tiffy Cooks | tiffycooks.com | ⚠️ | ❌ 排除 | 混合食谱内容 |

---

## 🌏 亚洲/国际

### 高端媒体 & 榜单

| 网站 | URL | POI | 状态 | 备注 |
|------|-----|-----|------|------|
| Eater | eater.com | 🏪 | 🏗️ 已构建 | `eater` (sitemap) |
| Asia's 50 Best | theworlds50best.com | 🏪 | 🏗️ 已构建 | `asias_50_best` (sitemap) |
| Michelin Guide | guide.michelin.com | 🏪 | 🏗️ 已构建 | `michelin_guide` (sitemap) |
| CNA Luxury | cnaluxury.channelnewsasia.com | 🏪 | ❌ 不可达 | 无法访问 |
| DestinAsian | destinasian.com | 🏪 | 🏗️ 已构建 | `destinasian` (sitemap, Next.js Apollo) |
| CNN Travel | cnn.com/travel | 🏪 | 🏗️ 已构建 | `cnn_travel` (pagination) |
| Aperitif | aperitif.com | 🏪 | 🏗️ 已构建 | `aperitif` (sitemap, Yoast, Bali fine dining) |

### 旅行美食博客

| 网站 | URL | POI | 状态 | 备注 |
|------|-----|-----|------|------|
| Will Fly For Food | willflyforfood.net | 🏪 | 🏗️ 已构建 | `will_fly_for_food` (sitemap) |
| Food Fun Travel | foodfuntravel.com | 🏪 | 🏗️ 已构建 | `food_fun_travel` (sitemap) |
| Wanderlog | wanderlog.com | 🏪 | ❌ 排除 | 聚合 listing，非文章 |
| TableCheck | tablecheck.com | 🏪 | ❌ 排除 | 餐厅预订 listing，非文章 |
| World of Mouth | worldofmouth.app | 🏪 | ❌ 排除 | 短推荐，非文章格式 |
| Elite Havens | elitehavens.com | 🏪 | 🏗️ 已构建 | `elite_havens` (sitemap) |
| With Husband in Tow | withhusbandintow.com | 🏪 | ❌ 排除 | 2023年停更 |
| Food Travel Guides | foodandtravelguides.com | 🏪 | ❌ 排除 | Wix，文章极少 |
| Hey Roseanne | heyroseanne.com | 🏪 | 🏗️ 已构建 | `hey_roseanne` (sitemap, Korea, ~159 articles) |
| Girl on a Zebra | girlonazebra.com | 🏪 | 🏗️ 已构建 | `girl_on_a_zebra` (sitemap, ~403 articles) |
| Belletrist Travels | belletristravels.com | 🏪 | ❌ 排除 | 仅 14 篇文章 |
| Travelling Foodie | travellingfoodie.net | ⚠️ | ✅ 未构建 | 混合内容 |
| Nikkei Asia | asia.nikkei.com | ⚠️ | ❌ 排除 | 商业新闻为主，餐厅内容极少 |

### 需要特殊处理

| 网站 | URL | 需要 | 状态 | 备注 |
|------|-----|------|------|------|
| Travel+Leisure Asia | travelandleisureasia.com | Chrome UA | 🏗️ 已构建 | `travel_leisure_asia` (sitemap, 参数化 :region, 20k+ articles) |
| Prestige Online | prestigeonline.com | Playwright | ❌ 排除 | AWS WAF JS 验证 |
| SCMP | scmp.com | 代理 | ✅ 未构建 | 有餐厅评测 |

---

## 📋 剩余未构建清单

以下为可行但尚未构建的信源（按优先级排序）：

| # | 网站 | URL | 地区 | 备注 |
|---|------|-----|------|------|
| 1 | Kompas Travel Food | travel.kompas.com/makan-makan | 🇮🇩 | 混合内容需筛选 |
| 2 | Liputan6 Kuliner | liputan6.com/lifestyle/kuliner | 🇮🇩 | 混合内容需筛选 |
| 3 | Suara Food Travel | suara.com | 🇮🇩 | 混合内容需筛选 |
| 4 | Tribun Kuliner | tribunnews.com/travel/kuliner | 🇮🇩 | 需 Chrome UA |
| 5 | Travelling Foodie | travellingfoodie.net | 🌏 | 混合内容 |
| 6 | SCMP | scmp.com | 🇭🇰 | 需代理 |

### 需要特殊基础设施

| 网站 | 需要 | 备注 |
|------|------|------|
| Jawa Pos Kuliner | Playwright | 403 反爬 |
| Spot PH | Playwright | 403 反爬 |
| MangoPlate | 韩国 IP | SSL 问题 |
| Siksin | 韩国 IP | SSL 问题 |

---

## 📝 备注

1. **已有爬虫覆盖的网站** (不在此列表):
   - whatsnewindonesia.com, theasiacollective.com, manual.co.id, nowjakarta.co.id
   - ekaputrawisata.com, timeout.com, chope.co, honeycombers.com, idntimes.com
   - lonelyplanet.com 等共 20 个初始爬虫

2. **POI 筛选方法**:
   - 文章标题/URL 包含餐厅名
   - 文章内容有地址、电话、营业时间
   - 文章有"推荐"、"榜单"、"best"、"top" 等关键词

3. **混合内容站处理**:
   - 在 `is_valid_article_url()` 中排除食谱类 URL
   - 例如排除 `/resep/`、`/recipe/`、`/cara-membuat/` 等路径

4. **不适合文章爬虫框架的站点** (已排除):
   - 餐厅预订平台 (OpenTable, TableCheck) → listing 格式，非文章
   - 短推荐应用 (World of Mouth) → 非长文章
   - 聚合榜单 (Wanderlog) → 非原创文章
