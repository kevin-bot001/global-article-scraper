# -*- coding: utf-8 -*-
"""
各网站爬虫模块

目录结构：
- sitemap/    Sitemap 模式爬虫（使用 XML sitemap 获取文章列表）
- pagination/ Pagination 模式爬虫（通过分类/分页接口获取文章列表）
- playwright/ Playwright 模式爬虫（用于有强力反爬的网站）
"""
# Sitemap 爬虫
from .sitemap import (
    ManualJakartaScraper,
    NowJakartaScraper,
    TimeOutScraper,
    WhatsNewIndonesiaScraper,
    FlokqBlogScraper,
    CultureTripScraper,
    ChopeScraper,
    FeastinScraper,
    ExquisiteTasteScraper,
    TheAsiaCollectiveScraper,
    WandernesiaScraper,
    LePetitChefScraper,
    TourTellerScraper,
    EkaputraWisataScraper,
    RenaesWorldScraper,
    UrbanIconScraper,
    HotelierScraper,
    KompasFoodScraper,
    HoneycombersScraper,
    IndoIndiansScraper,
    IDNTimesScraper,
)
# Pagination 爬虫（分类/分页模式）
from .pagination import AlinearScraper, LonelyPlanetScraper
# Playwright 爬虫（仅用于需要JS渲染的网站）
from .playwright import TripCanvasScraper

__all__ = [
    # Sitemap 爬虫
    "ManualJakartaScraper",
    "NowJakartaScraper",
    "TimeOutScraper",
    "WhatsNewIndonesiaScraper",
    "FlokqBlogScraper",
    "TheSmartLocalScraper",
    "CultureTripScraper",
    "ChopeScraper",
    "FeastinScraper",
    "ExquisiteTasteScraper",
    "TheAsiaCollectiveScraper",
    "WandernesiaScraper",
    "LePetitChefScraper",
    # Playwright 爬虫
    "TripCanvasScraper",
    "TourTellerScraper",
    "EkaputraWisataScraper",
    "RenaesWorldScraper",
    "UrbanIconScraper",
    "HotelierScraper",
    "KompasFoodScraper",
    "HoneycombersScraper",
    "AlinearScraper",
    "IndoIndiansScraper",
    "LonelyPlanetScraper",
    "IDNTimesScraper",
]

# 爬虫注册表
SCRAPER_REGISTRY = {
    # Sitemap 爬虫
    "manual_jakarta": ManualJakartaScraper,
    "now_jakarta": NowJakartaScraper,
    "timeout": TimeOutScraper,  # 支持多城市: timeout:jakarta, timeout:singapore
    "whats_new_indonesia": WhatsNewIndonesiaScraper,
    "flokq_blog": FlokqBlogScraper,
    "culture_trip": CultureTripScraper,
    "chope": ChopeScraper,  # 支持多城市: chope:jakarta, chope:bali
    "feastin": FeastinScraper,
    "exquisite_taste": ExquisiteTasteScraper,
    "the_asia_collective": TheAsiaCollectiveScraper,
    "wandernesia": WandernesiaScraper,
    "lepetitchef": LePetitChefScraper,
    # Playwright 爬虫
    "tripcanvas": TripCanvasScraper,
    "tourteller": TourTellerScraper,
    "ekaputrawisata": EkaputraWisataScraper,
    "renaesworld": RenaesWorldScraper,
    "urbanicon": UrbanIconScraper,
    "hotelier": HotelierScraper,
    "kompas_food": KompasFoodScraper,
    "honeycombers": HoneycombersScraper,  # 支持多城市: honeycombers:singapore, honeycombers:bali
    "alinear": AlinearScraper,
    "indoindians": IndoIndiansScraper,
    "lonely_planet": LonelyPlanetScraper,
    "idntimes": IDNTimesScraper,  # 支持多城市: idntimes:main, idntimes:bali
}

# 按类型分组
SITEMAP_SCRAPERS = {
    "manual_jakarta", "now_jakarta",
    "timeout", "whats_new_indonesia", "flokq_blog", "thesmartlocal",
    "culture_trip", "chope", "feastin", "exquisite_taste", "the_asia_collective",
    "wandernesia", "lepetitchef", "tourteller", "ekaputrawisata",
    "renaesworld", "urbanicon", "hotelier",
    "kompas_food", "honeycombers", "indoindians", "idntimes",
}
PAGINATION_SCRAPERS = {"alinear", "lonely_planet"}  # 分类/分页模式
PLAYWRIGHT_SCRAPERS = {"tripcanvas"}

# 支持参数化的爬虫 (格式: name:param)
PARAMETERIZED_SCRAPERS = {
    "chope": "city",              # chope:jakarta, chope:bali 等
    "timeout": "city",            # timeout:jakarta, timeout:singapore 等
    "culture_trip": "city",       # culture_trip:jakarta, culture_trip:tokyo 等
    "whats_new_indonesia": "city",  # whats_new_indonesia:jakarta, whats_new_indonesia:bali 等
    "honeycombers": "city",       # honeycombers:singapore, honeycombers:bali, honeycombers:hong-kong
    "idntimes": "city",           # idntimes:main, idntimes:bali, idntimes:jateng 等
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
            - type: 类型 (sitemap/playwright)
            - display_name: 显示名称
            - base_url: 网站URL
            - country: 国家/地区
            - cities: 支持的城市列表（仅多城市爬虫）
            - param_name: 参数名（仅参数化爬虫）
    """
    from config import SITE_CONFIGS

    scrapers = []
    for name in SCRAPER_REGISTRY:
        config = SITE_CONFIGS.get(name, {})

        # 基础信息 - 判断爬虫类型
        if name in PLAYWRIGHT_SCRAPERS:
            scraper_type = "playwright"
        elif name in PAGINATION_SCRAPERS:
            scraper_type = "pagination"
        else:
            scraper_type = "sitemap"

        info = {
            "name": name,
            "type": scraper_type,
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
