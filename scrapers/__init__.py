# -*- coding: utf-8 -*-
"""
各网站爬虫模块

目录结构（按国家/地区分组）：
- indonesia/   印尼爬虫（Jakarta、Bali、Bandung 等）
- singapore/   新加坡爬虫
- thailand/    泰国爬虫
- malaysia/    马来西亚爬虫
- philippines/ 菲律宾爬虫
- vietnam/     越南爬虫
- taiwan/      台湾爬虫
- hongkong/    香港爬虫
- worldwide/   跨国/全球站点爬虫
"""
# Indonesia (24)
from .indonesia import (
    ManualJakartaScraper,
    NowJakartaScraper,
    FlokqBlogScraper,
    FeastinScraper,
    ExquisiteTasteScraper,
    WandernesiaScraper,
    BaliFoodTravelScraper,
    EkaputraWisataScraper,
    HotelierScraper,
    KompasFoodScraper,
    IndoIndiansScraper,
    IndonesiaExpatScraper,
    IDNTimesScraper,
    WhatsNewIndonesiaScraper,
    MakanManaScraper,
    JakartaPostFoodScraper,
    OnBaliScraper,
    UrbanIconScraper,
    AperitifScraper,
    DetikFoodScraper,
    AlinearScraper,
    NibbleScraper,
    WeekenderScraper,
    TripCanvasScraper,
)
# Singapore (8)
from .singapore import (
    EatbookScraper,
    MissTamChiakScraper,
    DanielFoodDiaryScraper,
    UrbanListSGScraper,
    AlexisCheongScraper,
    HungryGoWhereScraper,
    LadyIronChefScraper,
    SethLuiScraper,
)
# Thailand (3)
from .thailand import (
    BKKFoodieScraper,
    BangkokFoodiesScraper,
    CleverThaiScraper,
)
# Malaysia (2)
from .malaysia import (
    KLFoodieScraper,
    MalaysianFoodieScraper,
)
# Philippines (2)
from .philippines import (
    GuideToPhScraper,
    BookyPhScraper,
)
# Vietnam (1)
from .vietnam import (
    VietnamInsidersScraper,
)
# Taiwan (2)
from .taiwan import (
    EatingInTaipeiScraper,
    OpenRiceTWScraper,
)
# Hong Kong (1)
from .hongkong import (
    OpenRiceHKScraper,
)
# Worldwide (20)
from .worldwide import (
    TimeOutScraper,
    CultureTripScraper,
    ChopeScraper,
    HoneycombersScraper,
    TheAsiaCollectiveScraper,
    TourTellerScraper,
    RenaesWorldScraper,
    LePetitChefScraper,
    WillFlyForFoodScraper,
    EliteHavensScraper,
    FoodFunTravelScraper,
    MichelinGuideScraper,
    Asias50BestScraper,
    EaterScraper,
    DestinAsianScraper,
    TravelLeisureAsiaScraper,
    GirlOnAZebraScraper,
    HeyRoseanneScraper,
    TatlerAsiaScraper,
    CnnTravelScraper,
    LonelyPlanetScraper,
)

__all__ = [
    # Indonesia
    "ManualJakartaScraper", "NowJakartaScraper", "FlokqBlogScraper",
    "FeastinScraper", "ExquisiteTasteScraper", "WandernesiaScraper",
    "BaliFoodTravelScraper", "EkaputraWisataScraper", "HotelierScraper",
    "KompasFoodScraper", "IndoIndiansScraper", "IndonesiaExpatScraper",
    "IDNTimesScraper", "WhatsNewIndonesiaScraper", "MakanManaScraper",
    "JakartaPostFoodScraper", "OnBaliScraper", "UrbanIconScraper",
    "AperitifScraper", "DetikFoodScraper",
    "AlinearScraper", "NibbleScraper", "WeekenderScraper",
    "TripCanvasScraper",
    # Singapore
    "EatbookScraper", "MissTamChiakScraper", "DanielFoodDiaryScraper",
    "UrbanListSGScraper", "AlexisCheongScraper", "HungryGoWhereScraper",
    "LadyIronChefScraper", "SethLuiScraper",
    # Thailand
    "BKKFoodieScraper", "BangkokFoodiesScraper", "CleverThaiScraper",
    # Malaysia
    "KLFoodieScraper", "MalaysianFoodieScraper",
    # Philippines
    "GuideToPhScraper", "BookyPhScraper",
    # Vietnam
    "VietnamInsidersScraper",
    # Taiwan
    "EatingInTaipeiScraper", "OpenRiceTWScraper",
    # Hong Kong
    "OpenRiceHKScraper",
    # Worldwide
    "TimeOutScraper", "CultureTripScraper", "ChopeScraper",
    "HoneycombersScraper", "TheAsiaCollectiveScraper", "TourTellerScraper",
    "RenaesWorldScraper", "LePetitChefScraper", "WillFlyForFoodScraper",
    "EliteHavensScraper", "FoodFunTravelScraper",
    "MichelinGuideScraper", "Asias50BestScraper", "EaterScraper",
    "DestinAsianScraper", "TravelLeisureAsiaScraper",
    "GirlOnAZebraScraper", "HeyRoseanneScraper",
    "TatlerAsiaScraper", "CnnTravelScraper",
    "LonelyPlanetScraper",
]

# 爬虫注册表
SCRAPER_REGISTRY = {
    # Indonesia
    "manual_jakarta": ManualJakartaScraper,
    "now_jakarta": NowJakartaScraper,
    "flokq_blog": FlokqBlogScraper,
    "feastin": FeastinScraper,
    "exquisite_taste": ExquisiteTasteScraper,
    "wandernesia": WandernesiaScraper,
    "bali_food_travel": BaliFoodTravelScraper,
    "ekaputrawisata": EkaputraWisataScraper,
    "hotelier": HotelierScraper,
    "kompas_food": KompasFoodScraper,
    "indoindians": IndoIndiansScraper,
    "indonesia_expat": IndonesiaExpatScraper,
    "idntimes": IDNTimesScraper,              # 多城市: idntimes:bali, idntimes:jabar
    "whats_new_indonesia": WhatsNewIndonesiaScraper,  # 多城市: whats_new_indonesia:jakarta
    "makanmana": MakanManaScraper,
    "jakarta_post_food": JakartaPostFoodScraper,
    "onbali": OnBaliScraper,
    "urbanicon": UrbanIconScraper,
    "aperitif": AperitifScraper,
    "detik_food": DetikFoodScraper,
    "alinear": AlinearScraper,
    "nibble": NibbleScraper,
    "weekender": WeekenderScraper,
    "tripcanvas": TripCanvasScraper,
    # Singapore
    "eatbook": EatbookScraper,
    "miss_tam_chiak": MissTamChiakScraper,
    "daniel_food_diary": DanielFoodDiaryScraper,
    "urban_list_sg": UrbanListSGScraper,
    "alexis_cheong": AlexisCheongScraper,
    "hungrygowhere": HungryGoWhereScraper,
    "lady_iron_chef": LadyIronChefScraper,
    "seth_lui": SethLuiScraper,
    # Thailand
    "bkkfoodie": BKKFoodieScraper,
    "bangkok_foodies": BangkokFoodiesScraper,
    "clever_thai": CleverThaiScraper,
    # Malaysia
    "kl_foodie": KLFoodieScraper,
    "malaysian_foodie": MalaysianFoodieScraper,
    # Philippines
    "guide_to_ph": GuideToPhScraper,
    "booky_ph": BookyPhScraper,
    # Vietnam
    "vietnam_insiders": VietnamInsidersScraper,
    # Taiwan
    "eating_in_taipei": EatingInTaipeiScraper,
    "openrice_tw": OpenRiceTWScraper,
    # Hong Kong
    "openrice_hk": OpenRiceHKScraper,
    # Worldwide
    "timeout": TimeOutScraper,                # 多城市: timeout:jakarta, timeout:singapore
    "culture_trip": CultureTripScraper,       # 多城市: culture_trip:jakarta, culture_trip:tokyo
    "chope": ChopeScraper,                    # 多城市: chope:jakarta, chope:bali
    "honeycombers": HoneycombersScraper,      # 多城市: honeycombers:singapore, honeycombers:bali
    "the_asia_collective": TheAsiaCollectiveScraper,
    "tourteller": TourTellerScraper,
    "renaesworld": RenaesWorldScraper,
    "lepetitchef": LePetitChefScraper,
    "will_fly_for_food": WillFlyForFoodScraper,
    "elite_havens": EliteHavensScraper,
    "food_fun_travel": FoodFunTravelScraper,
    "michelin_guide": MichelinGuideScraper,
    "asias_50_best": Asias50BestScraper,
    "eater": EaterScraper,
    "destinasian": DestinAsianScraper,
    "travel_leisure_asia": TravelLeisureAsiaScraper,
    "girl_on_a_zebra": GirlOnAZebraScraper,
    "hey_roseanne": HeyRoseanneScraper,
    "tatler_asia": TatlerAsiaScraper,
    "cnn_travel": CnnTravelScraper,
    "lonely_planet": LonelyPlanetScraper,
}

# 按爬虫类型分组（运行时用于判断执行方式）
SITEMAP_SCRAPERS = {
    # Indonesia
    "manual_jakarta", "now_jakarta", "flokq_blog", "feastin", "exquisite_taste",
    "wandernesia", "bali_food_travel", "ekaputrawisata", "hotelier", "kompas_food",
    "indoindians", "indonesia_expat", "idntimes", "whats_new_indonesia",
    "makanmana", "jakarta_post_food", "onbali", "urbanicon", "aperitif",
    "detik_food",
    # Singapore
    "eatbook", "miss_tam_chiak", "daniel_food_diary", "urban_list_sg", "alexis_cheong",
    "hungrygowhere", "seth_lui",
    # Thailand
    "bkkfoodie", "bangkok_foodies", "clever_thai",
    # Malaysia
    "kl_foodie", "malaysian_foodie",
    # Philippines
    "guide_to_ph",
    # Vietnam
    "vietnam_insiders",
    # Taiwan
    "eating_in_taipei",
    # Worldwide
    "timeout", "culture_trip", "chope", "honeycombers", "the_asia_collective",
    "tourteller", "renaesworld", "lepetitchef", "will_fly_for_food",
    "elite_havens", "food_fun_travel",
    "michelin_guide", "asias_50_best", "eater",
    "destinasian", "travel_leisure_asia",
    "girl_on_a_zebra", "hey_roseanne",
}

PAGINATION_SCRAPERS = {
    # Indonesia
    "alinear", "nibble", "weekender",
    # Singapore
    "lady_iron_chef",
    # Philippines
    "booky_ph",
    # Taiwan
    "openrice_tw",
    # Hong Kong
    "openrice_hk",
    # Worldwide
    "tatler_asia", "cnn_travel", "lonely_planet",
}

PLAYWRIGHT_SCRAPERS = {
    # Indonesia
    "tripcanvas",
}

# 支持参数化的爬虫 (格式: name:param)
PARAMETERIZED_SCRAPERS = {
    "chope": "city",              # chope:jakarta, chope:bali 等
    "timeout": "city",            # timeout:jakarta, timeout:singapore 等
    "culture_trip": "city",       # culture_trip:jakarta, culture_trip:tokyo 等
    "whats_new_indonesia": "city",  # whats_new_indonesia:jakarta, whats_new_indonesia:bali 等
    "honeycombers": "city",       # honeycombers:singapore, honeycombers:bali, honeycombers:hong-kong
    "idntimes": "city",           # idntimes:main, idntimes:bali, idntimes:jateng 等
    "lonely_planet": "continent", # lonely_planet:asia, lonely_planet:europe 等
    "travel_leisure_asia": "region",  # travel_leisure_asia:sea, travel_leisure_asia:sg 等
}

# 按国家/地区分组
COUNTRY_SCRAPERS = {
    "indonesia": {
        "manual_jakarta", "now_jakarta", "flokq_blog", "feastin", "exquisite_taste",
        "wandernesia", "bali_food_travel", "ekaputrawisata", "hotelier", "kompas_food",
        "indoindians", "indonesia_expat", "idntimes", "whats_new_indonesia",
        "makanmana", "jakarta_post_food", "onbali", "urbanicon",
        "alinear", "nibble", "weekender", "tripcanvas",
        "aperitif", "detik_food",
    },
    "singapore": {
        "eatbook", "miss_tam_chiak", "daniel_food_diary", "urban_list_sg",
        "alexis_cheong", "hungrygowhere", "lady_iron_chef", "seth_lui",
    },
    "thailand": {"bkkfoodie", "bangkok_foodies", "clever_thai"},
    "malaysia": {"kl_foodie", "malaysian_foodie"},
    "philippines": {"guide_to_ph", "booky_ph"},
    "vietnam": {"vietnam_insiders"},
    "taiwan": {"eating_in_taipei", "openrice_tw"},
    "hongkong": {"openrice_hk"},
    "worldwide": {
        "timeout", "culture_trip", "chope", "honeycombers", "the_asia_collective",
        "tourteller", "renaesworld", "lepetitchef", "will_fly_for_food",
        "elite_havens", "food_fun_travel",
        "michelin_guide", "asias_50_best", "eater",
        "tatler_asia", "cnn_travel", "lonely_planet",
        "destinasian", "travel_leisure_asia",
        "girl_on_a_zebra", "hey_roseanne",
    },
}


def get_scraper(name: str):
    """
    获取爬虫类

    支持参数化格式: chope:jakarta, chope:bali 等
    """
    # 解析参数化格式
    param = None
    if ":" in name:
        name, param = name.split(":", 1)

    if name not in SCRAPER_REGISTRY:
        raise ValueError(f"未知爬虫: {name}，可用的爬虫: {list(SCRAPER_REGISTRY.keys())}")

    scraper_class = SCRAPER_REGISTRY[name]

    # 如果是参数化爬虫，返回一个工厂函数
    if name in PARAMETERIZED_SCRAPERS:
        param_name = PARAMETERIZED_SCRAPERS[name]

        def factory(use_proxy=False):
            return scraper_class(**{param_name: param}, use_proxy=use_proxy)

        return factory

    return scraper_class


def list_scrapers():
    """
    列出所有可用的爬虫，返回完整元数据

    Returns:
        List[dict]: 爬虫信息列表，每个包含:
            - name: 爬虫名称
            - type: 类型 (sitemap/pagination/playwright)
            - region: 国家/地区目录名
            - display_name: 显示名称
            - base_url: 网站URL
            - country: 国家/地区
            - cities: 支持的城市列表（仅多城市爬虫）
            - param_name: 参数名（仅参数化爬虫）
    """
    from config import SITE_CONFIGS

    # 构建爬虫→国家映射
    scraper_region = {}
    for region, names in COUNTRY_SCRAPERS.items():
        for n in names:
            scraper_region[n] = region

    scrapers = []
    for name in SCRAPER_REGISTRY:
        config = SITE_CONFIGS.get(name, {})

        # 判断爬虫类型
        if name in PLAYWRIGHT_SCRAPERS:
            scraper_type = "playwright"
        elif name in PAGINATION_SCRAPERS:
            scraper_type = "pagination"
        else:
            scraper_type = "sitemap"

        info = {
            "name": name,
            "type": scraper_type,
            "region": scraper_region.get(name, ""),
            "display_name": config.get("name", name),
            "base_url": config.get("base_url", ""),
            "country": config.get("country", ""),
        }

        # 多城市爬虫
        if name in PARAMETERIZED_SCRAPERS:
            info["param_name"] = PARAMETERIZED_SCRAPERS[name]
            cities_config = config.get("cities", {})
            info["cities"] = list(cities_config.keys())
        else:
            info["cities"] = []
            info["param_name"] = ""

        scrapers.append(info)
    return scrapers
