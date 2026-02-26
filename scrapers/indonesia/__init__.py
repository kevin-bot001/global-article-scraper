# -*- coding: utf-8 -*-
"""
Indonesia 爬虫
覆盖 Jakarta、Bali、Bandung、Yogyakarta、Surabaya 等城市
"""
from .manual_jakarta import ManualJakartaScraper
from .now_jakarta import NowJakartaScraper
from .flokq_blog import FlokqBlogScraper
from .feastin import FeastinScraper
from .exquisite_taste import ExquisiteTasteScraper
from .wandernesia import WandernesiaScraper
from .bali_food_travel import BaliFoodTravelScraper
from .ekaputrawisata import EkaputraWisataScraper
from .hotelier import HotelierScraper
from .kompas_food import KompasFoodScraper
from .indoindians import IndoIndiansScraper
from .indonesia_expat import IndonesiaExpatScraper
from .idntimes import IDNTimesScraper
from .whats_new_indonesia import WhatsNewIndonesiaScraper
from .makanmana import MakanManaScraper
from .jakarta_post_food import JakartaPostFoodScraper
from .onbali import OnBaliScraper
from .urbanicon import UrbanIconScraper
from .aperitif import AperitifScraper
from .detik_food import DetikFoodScraper
# Pagination
from .alinear import AlinearScraper
from .nibble import NibbleScraper
from .weekender import WeekenderScraper
# Playwright
from .tripcanvas import TripCanvasScraper

__all__ = [
    "ManualJakartaScraper",
    "NowJakartaScraper",
    "FlokqBlogScraper",
    "FeastinScraper",
    "ExquisiteTasteScraper",
    "WandernesiaScraper",
    "BaliFoodTravelScraper",
    "EkaputraWisataScraper",
    "HotelierScraper",
    "KompasFoodScraper",
    "IndoIndiansScraper",
    "IndonesiaExpatScraper",
    "IDNTimesScraper",
    "WhatsNewIndonesiaScraper",
    "MakanManaScraper",
    "JakartaPostFoodScraper",
    "OnBaliScraper",
    "UrbanIconScraper",
    "AperitifScraper",
    "DetikFoodScraper",
    "AlinearScraper",
    "NibbleScraper",
    "WeekenderScraper",
    "TripCanvasScraper",
]
