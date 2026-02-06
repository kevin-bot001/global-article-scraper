# -*- coding: utf-8 -*-
"""
Sitemap 模式爬虫
使用 Sitemap XML 获取文章列表，支持并发爬取
"""
from .manual_jakarta import ManualJakartaScraper
from .now_jakarta import NowJakartaScraper
from .timeout import TimeOutScraper
from .whats_new_indonesia import WhatsNewIndonesiaScraper
from .flokq_blog import FlokqBlogScraper
from .culture_trip import CultureTripScraper
from .chope import ChopeScraper
from .feastin import FeastinScraper
from .exquisite_taste import ExquisiteTasteScraper
from .the_asia_collective import TheAsiaCollectiveScraper
from .wandernesia import WandernesiaScraper
from .lepetitchef import LePetitChefScraper
from .tourteller import TourTellerScraper
from .ekaputrawisata import EkaputraWisataScraper
from .renaesworld import RenaesWorldScraper
from .urbanicon import UrbanIconScraper
from .hotelier import HotelierScraper
from .kompas_food import KompasFoodScraper
from .honeycombers import HoneycombersScraper
from .indoindians import IndoIndiansScraper
from .idntimes import IDNTimesScraper

__all__ = [
    "ManualJakartaScraper",
    "NowJakartaScraper",
    "TimeOutScraper",
    "WhatsNewIndonesiaScraper",
    "FlokqBlogScraper",
    "CultureTripScraper",
    "ChopeScraper",
    "FeastinScraper",
    "ExquisiteTasteScraper",
    "TheAsiaCollectiveScraper",
    "WandernesiaScraper",
    "LePetitChefScraper",
    "TourTellerScraper",
    "EkaputraWisataScraper",
    "RenaesWorldScraper",
    "UrbanIconScraper",
    "HotelierScraper",
    "KompasFoodScraper",
    "HoneycombersScraper",
    "IndoIndiansScraper",
    "IDNTimesScraper",
]
