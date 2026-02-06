# -*- coding: utf-8 -*-
"""
爬虫配置文件
"""
import os
from typing import Dict, List

# ============ 代理配置 ============
PROXY_CONFIG = {
    # 代理池URL（如果有的话）
    "proxy_pool_url": os.getenv("PROXY_POOL_URL", ""),
    # 静态代理列表
    "proxies": [
        'http://95943_zPnhx:UHSzlXsl9i@149.18.109.200:61235',
        'http://95943_zPnhx:UHSzlXsl9i@95.134.139.131:61235',
        'http://95943_zPnhx:UHSzlXsl9i@149.18.109.39:61235',
        'http://95943_zPnhx:UHSzlXsl9i@95.134.139.40:61235',
        'http://95943_zPnhx:UHSzlXsl9i@149.18.109.227:61235',
        'http://95943_zPnhx:UHSzlXsl9i@95.134.139.114:61235',
        'http://95943_zPnhx:UHSzlXsl9i@95.134.139.241:61235',
        'http://95943_zPnhx:UHSzlXsl9i@95.134.139.206:61235',
        'http://95943_zPnhx:UHSzlXsl9i@149.18.109.54:61235',
        'http://95943_zPnhx:UHSzlXsl9i@95.134.139.10:61235',
        'http://95943_zPnhx:UHSzlXsl9i@149.18.109.221:61235',
        'http://95943_zPnhx:UHSzlXsl9i@95.134.139.64:61235',
        'http://95943_zPnhx:UHSzlXsl9i@149.18.109.145:61235',
        'http://95943_zPnhx:UHSzlXsl9i@95.134.139.132:61235',
        'http://95943_zPnhx:UHSzlXsl9i@149.18.109.139:61235',
    ],
    # 是否启用代理（命令行还需要加 --proxy 参数）
    "enabled": True,
}

# ============ 请求配置 ============
REQUEST_CONFIG = {
    "timeout": 30,
    "max_retries": 3,
    "retry_delay": 2,  # 重试间隔（秒）
}

# ============ 并发配置 ============
CONCURRENCY_CONFIG = {
    "max_workers": 20,  # 线程池最大工作线程数
    "batch_size": 10,  # 每批处理的文章数量
    "enabled": True,  # 是否启用并发
}

# ============ User-Agent 列表 ============
USER_AGENTS: List[str] = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.5) Gecko/20100101 Firefox/120.5",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
]

# ============ 各网站爬取配置 ============
SITE_CONFIGS: Dict[str, dict] = {
    "manual_jakarta": {
        "name": "Manual Jakarta",
        "base_url": "https://manual.co.id",
        "delay": 0.5,
        "use_playwright": False,
        # "categories": ["food-drink", "nightlife", "fashion", "culture", "guides", "street"],
        "categories": ["food-drink", "nightlife", "fashion", "guides"],
        "country": "Indonesia",
        "city": "Jakarta",
    },
    "now_jakarta": {
        "name": "NOW! Jakarta",
        "base_url": "https://www.nowjakarta.co.id",
        "delay": 0.5,
        "use_playwright": False,
        # "categories": ["news", "dining", "discover-jakarta", "features", "art-and-culture", "lifestyle", "travel"],
        "categories": ["dining", "discover-jakarta", "travel"],
        "country": "Indonesia",
        "city": "Jakarta",
    },
    # Time Out (多城市支持)
    # 参考页面: https://www.timeout.com/ 底部城市列表
    "timeout": {
        "name": "Time Out",
        "base_url": "https://www.timeout.com",
        "delay": 0.5,
        "use_playwright": False,
        # "categories": ["restaurants", "things-to-do", "hotels", "travel", "music"],
        "categories": ["restaurants", "things-to-do", "hotels", "travel"],
        # 支持的城市 (用法: timeout:jakarta 或 timeout:jakarta,singapore)
        # city -> country 映射
        "cities": {
            "jakarta": "Indonesia",
            "singapore": "Singapore",
            "hong-kong": "China",
            "tokyo": "Japan",
            "bangkok": "Thailand",
            "kuala-lumpur": "Malaysia",
            "taipei": "China",
            "seoul": "South Korea",
            "sydney": "Australia",
            "melbourne": "Australia",
        },
        "city": "",
    },
    # What's New Indonesia (多城市支持)
    # 参考页面: https://whatsnewindonesia.com/ URL路径
    "whats_new_indonesia": {
        "name": "What's New Indonesia",
        "base_url": "https://whatsnewindonesia.com",
        "delay": 0.5,
        "use_playwright": False,
        # "categories": ["feature", "ultimate-guide", "event", "directory"],
        "categories": ["ultimate-guide"],
        # 支持的城市 (用法: whats_new_indonesia:jakarta 或 whats_new_indonesia:jakarta,bali)
        # city -> country 映射（印尼网站，所有城市都在印尼）
        "cities": {
            "jakarta": "Indonesia",
            "bali": "Indonesia",
            "bandung": "Indonesia",
            "yogyakarta": "Indonesia",
            "surabaya": "Indonesia",
        },
        "city": "",
    },
    "flokq_blog": {
        "name": "Flokq Blog",
        "base_url": "https://www.flokq.com/blog",
        "delay": 0.5,
        "use_playwright": False,
        "categories": ["panduan-lokal", "tempat-tinggal", "tips-di-rumah"],
        "country": "Indonesia",
        "city": "",
    },
    # Culture Trip (多城市支持)
    # 参考页面: https://theculturetrip.com/asia/ 国家和城市列表
    # 用法: culture_trip:jakarta 或 culture_trip:tokyo
    "culture_trip": {
        "name": "The Culture Trip",
        "base_url": "https://theculturetrip.com",
        "delay": 0.5,
        "use_playwright": False,
        "categories": ["food-and-drinks", "things-to-do", "places-to-stay", "guides-and-tips", "culture"],
        # city -> country 映射（爬虫内部做 city -> URL path 映射）
        "cities": {
            # 印尼
            "jakarta": "Indonesia",
            "bali": "Indonesia",
            "yogyakarta": "Indonesia",
            "bandung": "Indonesia",
            # 日本
            "tokyo": "Japan",
            "osaka": "Japan",
            "kyoto": "Japan",
            # 泰国
            "bangkok": "Thailand",
            "phuket": "Thailand",
            "chiang-mai": "Thailand",
            # 新加坡（城市国家）
            "singapore": "Singapore",
            # 马来西亚
            "kuala-lumpur": "Malaysia",
            # 越南
            "ho-chi-minh-city": "Vietnam",
            "hanoi": "Vietnam",
            # 菲律宾
            "manila": "Philippines",
            # 韩国
            "seoul": "South Korea",
            # 中国
            "beijing": "China",
            "shanghai": "China",
            "hong-kong": "China",
            # 印度
            "mumbai": "India",
            "delhi": "India",
        },
        "city": "",
    },
    # TripCanvas Indonesia (多城市支持)
    # 参考页面: https://indonesia.tripcanvas.co/ 顶部导航
    "tripcanvas": {
        "name": "TripCanvas Indonesia",
        "base_url": "https://indonesia.tripcanvas.co",
        "delay": 0.5,
        "use_playwright": True,  # post-sitemap.xml 被服务器禁用，只能用 Playwright
        # 支持的城市（作为 categories 传入）
        # 用法: 在下方 cities 列表中选择要爬取的城市
        # city -> country 映射（印尼网站，所有城市都在印尼）
        "cities": {
            "jakarta": "Indonesia",
            "bali": "Indonesia",
            "bandung": "Indonesia",
            "jogja": "Indonesia",
            "java": "Indonesia",
            "lombok": "Indonesia",
            "surabaya": "Indonesia",
            "malang": "Indonesia",
            "semarang": "Indonesia",
        },
        "categories": ["jakarta", "bali", "bandung", "jogja"],  # 实际爬取的城市列表
        "city": "",
    },
    # Chope (多城市支持)
    # 参考页面: https://www.chope.co/ 底部城市选择
    "chope": {
        "name": "Chope",
        "base_url": "https://www.chope.co",
        "delay": 0.5,
        "use_playwright": False,
        # 要爬取的 guide 类型（空=全部）
        # 可选: best-restaurants, buffet-guides, pizzaguide, rooftop-guide, seafood-guide 等
        "categories": [],
        # 支持的城市 (用法: chope:jakarta 或 chope:jakarta,bali)
        # city -> country 映射
        "cities": {
            "jakarta": "Indonesia",
            "bangkok": "Thailand",
            "bali": "Indonesia",
            "singapore": "Singapore",
            "phuket": "Thailand",
            "penang": "Malaysia",
            "hong-kong": "China",
            "beijing": "China",
            "shanghai": "China",
        },
        "city": "",
    },
    "feastin": {
        "name": "Feastin Indonesia",
        "base_url": "https://www.feastin.id",
        "delay": 0.5,
        "use_playwright": False,
        # 要爬取的分类（空=全部），使用 URL 路径格式
        # 可选: food-news-stories, eating-out, table-talk, travel, home, common-table
        "categories": ["food-news-stories", "eating-out"],
        "country": "Indonesia",
        "city": "",
    },
    "exquisite_taste": {
        "name": "Exquisite Taste Magazine",
        "base_url": "https://exquisite-taste-magazine.com",
        "delay": 0.5,
        "use_playwright": False,
        # 要爬取的分类（空=全部），从 category-sitemap.xml 获取
        # 主要分类: best-restaurants, extraordinary-dishes, gourmet, exquisite-awards-xxx,
        #          exquisite-cocktails, exquisite-wine-pairing, culinary-masters, new-tables 等
        "categories": [
            "best-restaurants",
            "extraordinary-dishes",
            "gourmet",
            "exquisite-awards-2024",
            "exquisite-awards-2025",
            "exquisite-cocktails",
            "exquisite-wine-pairing",
            "exquisite-dining",
            "culinary-masters",
            "new-tables",
            "unique-concept-dining",
        ],
        "country": "Indonesia",
        "city": "",
    },
    # The Asia Collective
    # 参考页面: https://theasiacollective.com/ 导航栏
    # REST API: https://theasiacollective.com/wp-json/wp/v2/categories
    "the_asia_collective": {
        "name": "The Asia Collective",
        "base_url": "https://theasiacollective.com",
        "delay": 0.5,
        "use_playwright": False,
        # 要爬取的分类（空=全部），共 45 个分类，通过 REST API 预建映射过滤
        # 内容类: travel-guides, hotel-reviews, restaurants, bars, cafes, lifestyle, influencers
        # 地区类: bali, singapore, japan, vietnam, malaysia, australia, dubai, europe, india
        # 巴厘岛: canggu, seminyak, sanur, ubud, uluwatu
        # 婚礼类: the-honeymoon, the-real-wedding, the-venue
        "categories": [
            "travel-guides",
            "hotel-reviews",
            "bars",
            "cafes",
            "restaurants",
            "bali", "canggu", "seminyak", "sanur", "ubud", "uluwatu"
        ],
        "country": "",  # 覆盖多个亚洲国家
        "city": "",
    },
    # Wandernesia (Sitemap 模式)
    # 印尼旅游博客，主要覆盖巴厘岛
    # Sitemap: https://www.wandernesia.com/post-sitemap.xml
    "wandernesia": {
        "name": "Wandernesia",
        "base_url": "https://www.wandernesia.com",
        "delay": 0.5,
        "use_playwright": False,
        "categories": [],  # 不过滤分类
        "country": "Indonesia",
        "city": "Bali",
    },
    # LePetitChef (Sitemap 模式)
    # 多语言餐厅指南 (ja, de, en)
    # Sitemap: https://lepetitchef.com/blog/post-sitemap.xml
    "lepetitchef": {
        "name": "Le Petit Chef",
        "base_url": "https://lepetitchef.com/blog",
        "delay": 0.5,
        "use_playwright": False,
        "categories": [],  # 不过滤分类
        "country": "",  # 全球餐厅
        "city": "",
    },
    # TourTeller (Sitemap 模式)
    # 旅游活动比较平台博客，Yoast SEO sitemap
    # Sitemap: /blog/sitemap_index.xml -> /blog/post-sitemap.xml
    "tourteller": {
        "name": "TourTeller",
        "base_url": "https://tourteller.com/blog",
        "delay": 1.0,
        "use_playwright": False,
        "categories": [],
        "country": "",
        "city": "",
    },
    # EkaputraWisata (Sitemap 模式)
    # 印尼旅游运营商博客，Rank Math sitemap
    # Sitemap: /sitemap_index.xml -> /post-sitemap1~3.xml
    "ekaputrawisata": {
        "name": "Ekaputra Wisata",
        "base_url": "https://ekaputrawisata.com",
        "delay": 1.0,
        "use_playwright": False,
        "categories": [],
        "country": "Indonesia",
        "city": "Jakarta",
    },
    # Renae's World (Sitemap 模式)
    # 澳大利亚旅游博客
    # Sitemap: post-sitemap.xml, post-sitemap2.xml
    "renaesworld": {
        "name": "Renae's World",
        "base_url": "https://renaesworld.com.au",
        "delay": 0.5,
        "use_playwright": False,
        "categories": [],
        "country": "",  # 全球旅游
        "city": "",
    },
    # Urban Icon Magazine (Sitemap 模式)
    # 印尼城市生活杂志
    # Sitemap: post-sitemap1.xml, post-sitemap2.xml
    "urbanicon": {
        "name": "Urban Icon Magazine",
        "base_url": "https://magazine.urbanicon.co.id",
        "delay": 0.5,
        "use_playwright": False,
        "categories": [],
        "country": "Indonesia",
        "city": "Jakarta",
    },
    # Hotelier Indonesia (Sitemap 模式)
    # 印尼酒店行业资讯
    # Sitemap: post-sitemap.xml ~ post-sitemap4.xml
    "hotelier": {
        "name": "Hotelier Indonesia",
        "base_url": "https://hotelier.id",
        "delay": 0.5,
        "use_playwright": False,
        "categories": [],
        "country": "Indonesia",
        "city": "",
    },
    # Kompas Food (Sitemap 模式)
    # 印尼最大新闻门户美食频道
    # Sitemap: sitemap-news-food.xml (Google News 格式)
    "kompas_food": {
        "name": "Kompas Food",
        "base_url": "https://www.kompas.com",
        "delay": 0.5,
        "use_playwright": False,
        "categories": [],
        "country": "Indonesia",
        "city": "",
    },
    # The Honeycombers (Sitemap 模式，多城市)
    # 亚洲生活方式指南
    # 支持城市: singapore, bali, hong-kong
    "honeycombers": {
        "name": "The Honeycombers",
        "base_url": "https://thehoneycombers.com",
        "delay": 0.5,
        "use_playwright": False,
        "categories": [],
        # 支持的城市 (用法: honeycombers:singapore, honeycombers:bali)
        "cities": {
            "singapore": "Singapore",
            "bali": "Indonesia",
            "hong-kong": "China",
        },
        "city": "",
        "max_sitemaps": 8,  # 最大 sitemap 数量
    },
    # Alinear Indonesia (F&B 分类分页模式)
    # 印尼 F&B 美食杂志，从分类分页获取（按时间倒序）
    # 列表页: /en/recent/food-beverage?page=N
    "alinear": {
        "name": "Alinear Indonesia",
        "base_url": "https://www.alinear.id",
        "delay": 0.5,
        "use_playwright": False,
        "categories": ["F&B", "Cafe & Resto", "Fine Dining", "Sweet & Dessert", "Street Food"],
        "country": "Indonesia",
        "city": "",  # 全国性杂志，不限定城市
    },
    # IndoIndians (Sitemap 模式)
    # 印度人在印尼社区网站，涵盖生活、美食、文化等
    # Sitemap: post-sitemap.xml ~ post-sitemap5.xml (Yoast SEO)
    "indoindians": {
        "name": "IndoIndians",
        "base_url": "https://www.indoindians.com",
        "delay": 0.5,
        "use_playwright": False,
        "categories": [],
        "country": "Indonesia",
        "city": "Jakarta",
    },
    # Lonely Planet (Category Page 模式)
    # 全球旅游指南网站，sitemap 全废，用分类页获取文章
    # 13 个分类: adventure, food-and-drink, beaches, etc.
    # JSON-LD NewsArticle 元数据，正文在 div.content-block
    "lonely_planet": {
        "name": "Lonely Planet",
        "base_url": "https://www.lonelyplanet.com",
        "delay": 0.5,
        "use_playwright": False,
        # 要爬取的分类（空=全部13个分类）
        # 可选: adventure, adventure-travel, art-and-culture, beaches, budget-travel,
        #       family-travel, festivals-and-events, food-and-drink, road-trips,
        #       romance, sustainable-travel, travel-advice, wildlife-and-nature
        "categories": [],
        "country": "",  # 全球网站，从内容识别
        "city": "",
    },
    # IDN Times (Sitemap Index 模式，多城市子域名)
    # 印尼大型综合媒体平台
    # 主站: www.idntimes.com, 子站: bali/jateng/ntb.idntimes.com
    # JSON-LD NewsArticle 元数据
    "idntimes": {
        "name": "IDN Times",
        "base_url": "https://www.idntimes.com",
        "delay": 0.5,
        "use_playwright": False,
        # 要爬取的分类（空=全部）
        # 可选: food, travel, life, news, sport, health, business, tech, science
        "categories": ["food"],
        # 子分类过滤（空=全部）
        # food 下可选: dining-guide, recipe, diet, restaurant
        "subcategories": ["dining-guide"],
        # 支持的城市子域名 (用法: idntimes:bali, idntimes:jabar)
        # key = 子域名, value = {"country": ..., "city": 真实城市名}
        # "main" = 主站 www.idntimes.com (Jakarta)
        "cities": {
            "bali": {"country": "Indonesia", "city": "Bali"},
            "jabar": {"country": "Indonesia", "city": "Jawa Barat"},
        },
        "country": "Indonesia",
        "city": "Jakarta",  # 主站默认城市
    },
}

# ============ 数据存储配置 ============

STORAGE_CONFIG = {
    "output_dir": os.getenv("OUTPUT_DIR", "./output"),
    "output_format": "json",  # json, csv, bigquery
    # BigQuery 配置（如果需要）
    "bigquery": {
        "project_id": "oppo-gcp-prod-digfood-129869",
        "dataset": "maomao_poi_external_data",
        "table": "global_articles",
    },
}
# ============ 日志配置 ============
LOG_CONFIG = {
    "level": os.getenv("LOG_LEVEL", "INFO"),
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
}
