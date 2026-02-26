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
        'http://95943_zPnhx:UHSzlXsl9i@95.134.139.164:61235',
        'http://95943_zPnhx:UHSzlXsl9i@95.134.139.228:61235',
        'http://95943_zPnhx:UHSzlXsl9i@149.18.109.98:61235',
        'http://95943_zPnhx:UHSzlXsl9i@149.18.109.5:61235',
        'http://95943_zPnhx:UHSzlXsl9i@95.134.139.62:61235',
        'http://95943_zPnhx:UHSzlXsl9i@95.134.139.240:61235',
        'http://95943_zPnhx:UHSzlXsl9i@95.134.139.92:61235',
        'http://95943_zPnhx:UHSzlXsl9i@149.18.109.51:61235',
        'http://95943_zPnhx:UHSzlXsl9i@149.18.109.238:61235',
        'http://95943_zPnhx:UHSzlXsl9i@149.18.109.235:61235',
        'http://95943_zPnhx:UHSzlXsl9i@95.134.139.180:61235',
        'http://95943_zPnhx:UHSzlXsl9i@95.134.139.45:61235',
        'http://95943_zPnhx:UHSzlXsl9i@149.18.109.79:61235',
        'http://95943_zPnhx:UHSzlXsl9i@149.18.109.160:61235',
        'http://95943_zPnhx:UHSzlXsl9i@149.18.109.214:61235',
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
    # Bali Food & Travel (Sitemap 模式)
    # 巴厘岛美食旅游网站，Rank Math SEO + Elementor
    # Sitemap: https://www.balifoodandtravel.com/sitemap_index.xml
    "bali_food_travel": {
        "name": "Bali Food & Travel",
        "base_url": "https://www.balifoodandtravel.com",
        "delay": 1.0,
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
    # Weekender (分类分页模式)
    # Jakarta Post 周末刊，专注餐厅推荐、美食评论和生活方式内容
    # 无 sitemap，使用分类分页: ?page=N
    # JSON-LD NewsArticle 元数据
    "weekender": {
        "name": "Weekender",
        "base_url": "https://weekender.thejakartapost.com",
        "delay": 0.5,
        "use_playwright": False,
        # 主要爬取分类 (life/table-setting 是餐厅推荐)
        "categories": ["life/table-setting", "life/weekend-five"],
        "country": "Indonesia",
        "city": "Jakarta",
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
    # Indonesia Expat (Sitemap 模式)
    # 印尼外籍人士社区网站
    # Sitemap Index: /sitemap_index.xml -> /post-sitemap1~11.xml (Yoast SEO)
    # 只爬取 /lifestyle/food-drink/ 分类
    "indonesia_expat": {
        "name": "Indonesia Expat",
        "base_url": "https://indonesiaexpat.id",
        "delay": 0.5,
        "use_playwright": False,
        "categories": ["food-drink"],  # 只爬 food-drink
        "country": "Indonesia",
        "city": "",  # 覆盖雅加达和巴厘岛
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
    # MakanMana (Sitemap 模式)
    # 印尼本土美食点评平台
    # Sitemap Index: /sitemap_index.xml -> /post-sitemap.xml (Yoast SEO)
    # 分类: rekomendasi, ragam-kuliner, ulasan-restoran
    "makanmana": {
        "name": "MakanMana",
        "base_url": "https://makanmana.id",
        "delay": 0.5,
        "use_playwright": False,
        "categories": [],  # 不过滤分类，爬取全部
        "country": "Indonesia",
        "city": "",  # 覆盖全国
    },
    # Jakarta Post Food (News Sitemap 模式)
    # 印尼最大英文报纸美食频道
    # Sitemap: /culture/food/news/sitemap.xml (Google News 格式，CDATA)
    # JSON-LD NewsArticle 元数据
    "jakarta_post_food": {
        "name": "Jakarta Post Food",
        "base_url": "https://www.thejakartapost.com",
        "delay": 0.5,
        "use_playwright": False,
        "categories": [],  # food 频道，不需要过滤
        "country": "Indonesia",
        "city": "Jakarta",
    },
    # Eatbook.sg (Sitemap 模式)
    # 新加坡本地美食指南，WordPress + Yoast SEO
    # Sitemap Index: /sitemap_index.xml -> /post-sitemap.xml ~ /post-sitemap9.xml
    # JSON-LD @graph 结构化数据
    "eatbook": {
        "name": "Eatbook.sg",
        "base_url": "https://eatbook.sg",
        "delay": 0.5,
        "use_playwright": False,
        "categories": [],  # 不过滤分类，爬取全部美食文章
        "max_sitemaps": 10,  # post-sitemap 最大数量
        "country": "Singapore",
        "city": "Singapore",
    },
    # Nibble.id (分类分页模式)
    # 印尼美食点评平台，餐厅指南和美食文章
    # 无 Sitemap，通过分类页面分页获取
    # 覆盖多个印尼城市: Jakarta, Bandung, Surabaya, Bali 等
    "nibble": {
        "name": "Nibble.id",
        "base_url": "https://www.nibble.id",
        "delay": 0.5,
        "use_playwright": False,
        # 要爬取的分类（空=全部）
        # 可选: nibbles-guide, foodie-trends, healthy-foodies, food, reviews
        "categories": [
            "nibbles-guide",
            "foodie-trends",
            "healthy-foodies",
        ],
        "max_pages": 15,  # 每个分类最大页数
        "country": "Indonesia",
        "city": "",  # 从文章内容自动识别城市
    },
    # Miss Tam Chiak (Sitemap 模式)
    # 新加坡顶级美食博客，Gatsby 静态站点
    # Sitemap: /sitemap-0.xml (注意: URL 域名为 uat.misstamchiak.com，需替换为 www)
    # JSON-LD @graph 格式 (Yoast SEO)
    "miss_tam_chiak": {
        "name": "Miss Tam Chiak",
        "base_url": "https://www.misstamchiak.com",
        "delay": 0.5,
        "use_playwright": False,
        "categories": [],  # 不过滤分类
        "country": "Singapore",
        "city": "Singapore",
    },
    # Tatler Asia (分类分页模式)
    # 亚洲高端生活杂志，Tatler Best Indonesia 餐厅榜单等
    # 无 Sitemap (robots.txt 无 sitemap 指令，sitemap.xml 返回 404)
    # 通过 /dining 分类分页获取文章
    # JSON-LD @graph 格式
    "tatler_asia": {
        "name": "Tatler Asia",
        "base_url": "https://www.tatlerasia.com",
        "delay": 1.0,  # robots.txt Crawl-delay: 10，保守设置 1 秒
        "use_playwright": False,
        "categories": ["food", "drinks"],  # 主要爬取 dining 下的 food 和 drinks
        "country": "",  # 亚洲多国，从标题/内容自动识别
        "city": "",
    },
    # SethLui.com (Playwright 模式)
    # 新加坡顶级美食博客，详细餐厅评测
    # Cloudflare Turnstile 保护，必须使用 Playwright
    # WordPress + Yoast SEO，覆盖新加坡和马来西亚
    "seth_lui": {
        "name": "SethLui.com",
        "base_url": "https://sethlui.com",
        "delay": 1.5,  # 较长延迟避免触发反爬
        "use_playwright": True,  # Cloudflare Turnstile 保护
        # 要爬取的分类（从分类页获取文章列表）
        # 可选: singapore/food, singapore/travel, singapore/lifestyle, singapore/nightlife
        #       malaysia/food, malaysia/travel
        "categories": ["singapore/food", "singapore/travel"],
        "country": "Singapore",
        "city": "",  # 从文章内容自动识别
    },
    # BKK Foodie (Sitemap 模式)
    # 泰国曼谷美食博客，餐厅评测和美食指南
    # WordPress + Yoast SEO
    # Sitemap: /post-sitemap.xml
    "bkkfoodie": {
        "name": "BKK Foodie",
        "base_url": "https://bkkfoodie.com",
        "delay": 0.5,
        "use_playwright": False,
        "categories": [],  # 不过滤分类
        "country": "Thailand",
        "city": "Bangkok",
    },
    # KL Foodie (Sitemap 模式)
    # 马来西亚吉隆坡美食评测网站
    # WordPress + Yoast SEO + Jannah Theme
    # Sitemap: /sitemap_index.xml -> /post-sitemap.xml ~ /post-sitemap4.xml
    "kl_foodie": {
        "name": "KL Foodie",
        "base_url": "https://klfoodie.com",
        "delay": 0.5,
        "use_playwright": False,
        "categories": [],  # 不过滤分类
        "country": "Malaysia",
        "city": "Kuala Lumpur",
    },
    # Malaysian Foodie (Sitemap 模式)
    # 马来西亚美食博客，覆盖吉隆坡餐厅、咖啡馆和美食指南
    # WordPress + Yoast SEO
    # Sitemap Index: /sitemap.xml -> /post-sitemap.xml ~ /post-sitemap19.xml
    # URL 格式: /YYYY/MM/slug.html
    "malaysian_foodie": {
        "name": "Malaysian Foodie",
        "base_url": "https://www.malaysianfoodie.com",
        "delay": 0.5,
        "use_playwright": False,
        "categories": [],  # 不过滤分类
        "country": "Malaysia",
        "city": "Kuala Lumpur",
    },
    # LadyIronChef (分页模式)
    # 新加坡顶级美食博客，餐厅推荐和美食指南
    # 无有效 Sitemap，使用首页分页 /page/N/
    # URL 格式: /YYYY/MM/slug/
    # Open Graph 元数据丰富
    "lady_iron_chef": {
        "name": "LadyIronChef",
        "base_url": "https://www.ladyironchef.com",
        "delay": 0.5,
        "use_playwright": False,
        "categories": [],  # 首页分页模式，不需要分类
        "country": "Singapore",
        "city": "Singapore",
    },
    # Booky.ph (分页模式)
    # 菲律宾餐厅预订/榜单平台博客
    # WordPress，无有效 Sitemap，使用分类分页 /blog/food/page/N/
    # Meta 标签: article:published_time, og:title, og:description, og:image
    # 主要覆盖 Metro Manila (BGC, Makati, Pasig 等)
    "booky_ph": {
        "name": "Booky.ph",
        "base_url": "https://booky.ph/blog",
        "delay": 0.5,
        "use_playwright": False,
        # 要爬取的分类（空=全部）
        # 可选: food, beauty, fitness, activities, wellness, smartness
        "categories": ["food"],
        "max_pages": 50,  # 每个分类最大页数
        "country": "Philippines",
        "city": "Metro Manila",
    },
    # Daniel Food Diary (Sitemap 模式)
    # 新加坡美食博客，餐厅评测和咖啡馆推荐
    # WordPress + All in One SEO Pro
    # Sitemap Index: /sitemap.xml -> /post-sitemap.xml ~ /post-sitemap8.xml
    # URL 格式: /YYYY/MM/DD/slug/
    # JSON-LD @graph 格式
    "daniel_food_diary": {
        "name": "Daniel Food Diary",
        "base_url": "https://danielfooddiary.com",
        "delay": 0.5,
        "use_playwright": False,
        "categories": [],  # 不过滤分类
        "max_sitemaps": 8,  # post-sitemap 最大数量
        "country": "Singapore",
        "city": "Singapore",
    },
    # The Urban List Singapore (Sitemap 模式)
    # 澳洲起源的城市生活方式指南，新加坡版本
    # Sitemap Index: /singapore/sitemap -> /singapore/sitemap/alist-sitemap-entries/P0,P100,P200
    # URL 格式: /singapore/a-list/{slug}
    # 日期格式: "6th Feb 2026"
    "urban_list_sg": {
        "name": "The Urban List SG",
        "base_url": "https://www.theurbanlist.com/singapore",
        "delay": 0.5,
        "use_playwright": False,
        "categories": [],  # 全部 a-list 文章
        "country": "Singapore",
        "city": "Singapore",
    },
    # Eating in Taipei (Sitemap 模式)
    # 台北美食博客，英国人在台湾的美食探索指南
    # WordPress + Rank Math SEO
    # Sitemap Index: /sitemap_index.xml -> /post-sitemap1.xml, /post-sitemap2.xml
    # URL 格式: /slug/
    "eating_in_taipei": {
        "name": "Eating in Taipei",
        "base_url": "https://eatingintaipei.com",
        "delay": 0.5,
        "use_playwright": False,
        "categories": [],  # 不过滤分类
        "country": "Taiwan",
        "city": "Taipei",
    },
    # Bangkok Foodies (Sitemap 模式)
    # 泰国曼谷美食博客，餐厅评测、美食活动和用餐指南
    # WordPress + Yoast SEO Premium
    # Sitemap: /post-sitemap.xml (有 PHP 警告，需要清理)
    "bangkok_foodies": {
        "name": "Bangkok Foodies",
        "base_url": "https://www.bangkokfoodies.com",
        "delay": 0.5,
        "use_playwright": False,
        "categories": [],  # 不过滤分类
        "country": "Thailand",
        "city": "Bangkok",
    },
    # Will Fly For Food (Sitemap 模式)
    # 亚洲跨区域美食旅行指南，覆盖全球餐厅、街头美食、烹饪体验
    # WordPress, 单一 sitemap.xml (非 sitemap index)
    # JSON-LD @graph 格式 (Article type)
    "will_fly_for_food": {
        "name": "Will Fly For Food",
        "base_url": "https://www.willflyforfood.net",
        "delay": 0.5,
        "use_playwright": False,
        "categories": [],  # 不过滤分类
        "country": "",  # 跨区域网站，从文章内容自动识别
        "city": "",
    },
    # OnBali (Sitemap 模式)
    # 巴厘岛旅游美食指南，Next.js 构建
    # Sitemap Index: /sitemap.xml -> /sitemap_1.xml ~ /sitemap_7.xml
    # JSON-LD @graph 格式 (Article + FAQPage)
    "onbali": {
        "name": "OnBali",
        "base_url": "https://onbali.com",
        "delay": 0.5,
        "use_playwright": False,
        "categories": [],
        "country": "Indonesia",
        "city": "Bali",
    },
    # Alexis Cheong (Sitemap 模式)
    # 新加坡美食博客，Blogger 平台
    # Sitemap Index: /sitemap.xml -> /sitemap.xml?page=1, ?page=2
    # URL Pattern: /YYYY/MM/slug.html
    # 无 JSON-LD，日期从 .entry-meta 文本提取
    "alexis_cheong": {
        "name": "Alexis Cheong",
        "base_url": "https://www.alexischeong.com",
        "delay": 0.5,
        "use_playwright": False,
        "categories": [],  # 不过滤分类
        "country": "Singapore",
        "city": "Singapore",
    },
    # Vietnam Insiders (Sitemap 模式)
    # 越南新闻媒体，涵盖米其林/餐厅/美食报道
    # Jetpack sitemap: /sitemap.xml -> /sitemap-index-1.xml -> /sitemap-1.xml ~ /sitemap-23.xml
    # JSON-LD BlogPosting/Article 格式
    # 综合新闻站，需要 URL 关键词过滤只保留美食相关文章
    "vietnam_insiders": {
        "name": "Vietnam Insiders",
        "base_url": "https://vietnaminsiders.com",
        "delay": 0.5,
        "use_playwright": False,
        "categories": [],
        "country": "Vietnam",
        "city": "",
    },
    # Elite Havens Magazine (Sitemap 模式)
    # 高端别墅/美食杂志，覆盖东南亚多区域
    # WordPress + Avada Theme + Yoast SEO
    # Sitemap: magazine-proxy.elitehavens.com/post-sitemap.xml (代理域名，需 URL 转换)
    # 实际文章: www.elitehavens.com/magazine/slug/
    "elite_havens": {
        "name": "Elite Havens Magazine",
        "base_url": "https://www.elitehavens.com",
        "delay": 0.5,
        "use_playwright": False,
        "categories": [],
        "country": "",  # 跨区域网站，从文章内容自动识别
        "city": "",
    },
    # Clever Thai (Sitemap 模式)
    # 泰国生活指南网站，涵盖餐厅推荐、娱乐、购物等
    # WordPress + Yoast SEO
    # Sitemap Index: /sitemap_index.xml -> /post-sitemap.xml, /post-sitemap2.xml
    # JSON-LD @graph (WebPage + Person)
    "clever_thai": {
        "name": "Clever Thai",
        "base_url": "https://www.cleverthai.com",
        "delay": 0.5,
        "use_playwright": False,
        "categories": [],
        "country": "Thailand",
        "city": "",
    },
    # Food Fun Travel (Sitemap 模式)
    # 跨区域美食旅行博客，涵盖巴厘岛、格鲁吉亚、意大利、泰国等
    # WordPress + Yoast SEO + SASWP (Schema & Structured Data)
    # Sitemap: /post-sitemap.xml
    # JSON-LD Article 格式 (SASWP 插件，非 @graph)
    "food_fun_travel": {
        "name": "Food Fun Travel",
        "base_url": "https://foodfuntravel.com",
        "delay": 0.5,
        "use_playwright": False,
        "categories": [],
        "country": "",  # 跨区域网站，从文章内容自动识别
        "city": "",
    },
    # OpenRice 香港 (API 分页模式)
    # 香港最大餐廳評價平台
    # 無 Sitemap，HTML 頁面有 ByteDance CDN JS Challenge 反爬
    # 通過內部 JSON API (/api/articles) 獲取文章列表
    # API 提供標題、摘要(100字)、發布日期、作者、分類、封面圖
    # 總計約 7116+ 篇文章，每頁 10 條
    # 與 TW 版本共用相同的 API 結構，不需要 cityId 參數
    "openrice_hk": {
        "name": "OpenRice Hong Kong",
        "base_url": "https://www.openrice.com",
        "delay": 0.5,
        "use_playwright": False,
        "categories": [],
        "country": "Hong Kong",
        "city": "Hong Kong",
        "max_pages": 720,
    },
    # OpenRice 台灣 (API 分页模式)
    # 台灣最大餐廳評價平台，類似大眾點評
    # 無 Sitemap，HTML 頁面有 ByteDance CDN JS Challenge 反爬
    # 通過內部 JSON API (/api/articles) 獲取文章列表
    # API 提供標題、摘要(100字)、發布日期、作者、分類、封面圖
    # 總計約 5880+ 篇文章，每頁 10 條
    "openrice_tw": {
        "name": "OpenRice Taiwan",
        "base_url": "https://tw.openrice.com",
        "delay": 0.5,
        "use_playwright": False,
        "categories": [],
        "country": "Taiwan",
        "city": "Taipei",
        "max_pages": 600,
    },
    # Michelin Guide (Sitemap 模式)
    # 全球米其林指南编辑内容，涵盖餐厅推荐、厨师访谈、美食旅行等
    # Sitemap Index: /sitemap.xml -> /sitemap/article/{region}.xml (48 个区域)
    # JSON-LD @type Article 格式（headline, datePublished, author, articleSection, keywords）
    # 内容区域: div.js-poool__content > div.detail-page__content
    # URL Pattern: /{region}/en/article/{category}/{slug}
    "michelin_guide": {
        "name": "Michelin Guide",
        "base_url": "https://guide.michelin.com",
        "delay": 1.0,
        "use_playwright": False,
        "categories": [],
        "country": "",  # 全球多区域网站，从 URL region code 自动识别
        "city": "",
    },
    # Asia's 50 Best Restaurants - 全球顶级餐厅榜单编辑内容
    # 涵盖亚洲/全球餐厅排名、厨师访谈、美食趋势、旅行推荐等
    # Sitemap: /stories/sitemap.xml (1600+ articles)
    # JSON-LD @type Article 格式（headline, datePublished, author）
    # 内容区域: div.article > div.content
    # URL Pattern: /stories/News/<slug>.html
    "asias_50_best": {
        "name": "Asia's 50 Best Restaurants",
        "base_url": "https://www.theworlds50best.com",
        "delay": 1.0,
        "categories": [],
        "country": "",
        "city": "",
    },
    # Eater (Sitemap Index 模式)
    # Vox Media 美食媒体，涵盖全球餐厅新闻、评测、美食趋势
    # Sitemap Index: /sitemaps/sitemap-index-articles.xml -> /sitemaps/article-YYYY-MM.xml
    # JSON-LD NewsArticle 格式 (headline, datePublished, author, articleSection, keywords)
    # 内容区域: .duet--layout--entry-body-container
    # URL Pattern: /section/numericid/slug
    "eater": {
        "name": "Eater",
        "base_url": "https://www.eater.com",
        "delay": 0.5,
        "use_playwright": False,
        "categories": [],
        "max_sitemaps": 24,  # 最近 24 个月的 sitemap
        "country": "",  # 全球网站
        "city": "",
    },
    # Lonely Planet (Pagination 模式)
    # 全球旅行指南，涵盖目的地、美食、探险、文化等
    # 无 Sitemap (返回 404)，通过 /articles/page/{N} 分页获取
    # JSON-LD NewsArticle 格式 (headline, datePublished, author, image)
    # 内容区域: div.content-block
    # CloudFront 保护，curl_cffi 可绕过
    "lonely_planet": {
        "name": "Lonely Planet",
        "base_url": "https://www.lonelyplanet.com",
        "delay": 1.0,
        "use_playwright": False,
        "categories": [],
        "max_pages": 225,  # /articles/page/N max page num
        "continent": "asia",  # Default continent filter (via ?slug=)
        # Available: asia, europe, north-america, south-america, pacific,
        #            africa, middle-east, caribbean, central-america, antarctica
        # Set to "" or None to disable filter (all continents)
        "country": "",  # Global site, auto-detect from content
        "city": "",
    },
    # CNN Travel (Category Page 模式)
    # 全球旅游新闻网站，涵盖美食、目的地、酒店、航空等
    # 无有效 Sitemap (sitemap 不含 /travel/ 路径)
    # 通过 5 个分类页面获取文章: travel 主页, food-and-drink, destinations, stay, news
    # JSON-LD NewsArticle 格式 (headline, datePublished, author, articleBody)
    # 内容区域: div.article__content
    # URL Pattern: /YYYY/MM/DD/travel/slug 或 /travel/slug
    "cnn_travel": {
        "name": "CNN Travel",
        "base_url": "https://www.cnn.com",
        "delay": 1.0,
        "use_playwright": False,
        "categories": [],
        "country": "",  # 全球网站，从文章内容自动识别
        "city": "",
    },
    # HungryGoWhere (Sitemap/Yoast 模式)
    # 新加坡美食发现平台，餐厅评论和美食指南
    # WordPress + Yoast SEO
    # Sitemap Index: /sitemap_index.xml -> /post-sitemap.xml, /post-sitemap2.xml
    # 内容区域: #articleContent
    # JSON-LD 仅含 author 信息
    # 分类: food-news, what-to-eat, critics-reviews
    "hungrygowhere": {
        "name": "HungryGoWhere",
        "base_url": "https://hungrygowhere.com",
        "delay": 0.5,
        "use_playwright": False,
        "categories": [],
        "country": "Singapore",
        "city": "Singapore",
    },
    # Travel+Leisure Asia (Multi-Region Sitemap 模式)
    # 亚洲旅行杂志，多区域站点 (SEA/SG/HK/TH/MY)
    # WordPress + Yoast SEO
    # Sitemap: /{region}/sitemap_index.xml -> post-sitemap*.xml
    # JSON-LD: NewsArticle (headline, datePublished, author)
    # 内容区域: <article> 标签
    # URL Pattern: /{region}/{category}/{subcategory}/{slug}/
    "travel_leisure_asia": {
        "name": "Travel+Leisure Asia",
        "base_url": "https://www.travelandleisureasia.com",
        "delay": 0.5,
        "use_playwright": False,
        "categories": [],
        "country": "",  # 由 region 参数决定
        "city": "",
        "cities": {
            "sea": {"country": "", "city": ""},                          # Southeast Asia - 自动检测
            "sg": {"country": "Singapore", "city": "Singapore"},
            "hk": {"country": "Hong Kong", "city": "Hong Kong"},
            "th": {"country": "Thailand", "city": "Bangkok"},
            "my": {"country": "Malaysia", "city": "Kuala Lumpur"},
        },
    },
    # Guide to the Philippines (Sitemap 模式)
    # 菲律宾旅游平台，覆盖旅行指南、美食、景点、岛屿
    # Next.js SSR + JSON-LD Article
    # Sitemap Index: /sitemap.xml -> sitemap0-3.xml (~465 articles)
    # 内容区域: <article> -> div[class*="articleWidgetHTML"]
    # 分类: 从 URL 提取 /articles/{category}/{slug}
    "guide_to_ph": {
        "name": "Guide to the Philippines",
        "base_url": "https://guidetothephilippines.ph",
        "delay": 0.8,
        "use_playwright": False,
        "categories": [],
        "country": "Philippines",
        "city": "",  # Multi-city, inferred from content
    },
    # DestinAsian (Sitemap/Yoast 模式)
    # 亚洲高端旅行杂志，覆盖亚太地区美食、酒店、目的地
    # WordPress + Yoast SEO
    # Sitemap Index: /sitemap.xml -> editorial-sitemap, post-sitemap, update-sitemap 等
    # 无 JSON-LD，使用 GraphQL/Apollo 状态管理
    # 内容区域: WordPress .wp-caption + <p> 标签
    # URL Pattern: /editorial/{slug}/, /{city}-{type}-{name}/
    "destinasian": {
        "name": "DestinAsian",
        "base_url": "https://destinasian.com",
        "delay": 0.8,
        "use_playwright": False,
        "categories": [],
        "country": "",  # 跨国杂志，从文章内容自动识别
        "city": "",
    },
    # Detik Food (Sitemap/CDATA 模式)
    # 印尼最大美食门户之一（detik.com 美食频道）
    # 自定义 CMS + JSON-LD NewsArticle
    # Sitemap: tempat-makan/sitemap_web.xml + kabar-kuliner/sitemap_web.xml (~200 articles)
    # 排除: resep/(食谱), makanan-anak/(儿童), sehat/(健康)
    # 内容区域: div.detail__body
    # URL Pattern: /{subcategory}/d-{id}/{slug}
    "detik_food": {
        "name": "Detik Food",
        "base_url": "https://food.detik.com",
        "delay": 0.5,
        "use_playwright": False,
        "categories": ["tempat-makan", "kabar-kuliner"],
        "country": "Indonesia",
        "city": "",
    },
    # Aperitif (Sitemap/Yoast 模式)
    # 巴厘岛精品餐饮博客（Ubud 为主），美食新闻、活动、餐厅指南
    # WordPress + Yoast SEO, Gutenberg blocks, 无 JSON-LD @graph
    # Sitemap Index: /sitemap.xml -> post-sitemap.xml (~128 articles)
    # 内容区域: <article> (Gutenberg blocks)
    # URL Pattern: /{category}/{slug}/ (blog/news/events)
    "aperitif": {
        "name": "Aperitif",
        "base_url": "https://www.aperitif.com",
        "delay": 0.8,
        "use_playwright": False,
        "categories": ["blog", "news", "events"],
        "country": "Indonesia",
        "city": "Bali",
    },
    # Girl on a Zebra (Sitemap/Rank Math 模式)
    # 亚太旅行美食博客，覆盖亚太、拉美、欧洲
    # WordPress + Rank Math SEO, 无 JSON-LD
    # Sitemap Index: /sitemap_index.xml -> post-sitemap1~3.xml (~403 articles)
    # 内容区域: div.entry-content.single-content
    # URL Pattern: /{slug}/
    "girl_on_a_zebra": {
        "name": "Girl on a Zebra",
        "base_url": "https://girlonazebra.com",
        "delay": 0.8,
        "use_playwright": False,
        "categories": [],
        "country": "",  # Global blog, auto-detect from content
        "city": "",
    },
    # Hey Roseanne (Sitemap/Rank Math 模式)
    # 韩国文化旅行博客，聚焦韩剧取景地、首尔旅行、韩国美食
    # WordPress + Rank Math SEO, 无 JSON-LD
    # Sitemap Index: /sitemap_index.xml -> post-sitemap.xml (~159 articles)
    # 内容区域: div.entry-content
    # URL Pattern: /{slug}/
    "hey_roseanne": {
        "name": "Hey Roseanne",
        "base_url": "https://heyroseanne.com",
        "delay": 0.8,
        "use_playwright": False,
        "categories": [],
        "country": "South Korea",
        "city": "",
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
