# -*- coding: utf-8 -*-
"""
Singapore 爬虫
"""
from .eatbook import EatbookScraper
from .miss_tam_chiak import MissTamChiakScraper
from .daniel_food_diary import DanielFoodDiaryScraper
from .urban_list import UrbanListSGScraper
from .alexis_cheong import AlexisCheongScraper
from .hungrygowhere import HungryGoWhereScraper
# Pagination
from .lady_iron_chef import LadyIronChefScraper
# Playwright
from .seth_lui import SethLuiScraper

__all__ = [
    "EatbookScraper",
    "MissTamChiakScraper",
    "DanielFoodDiaryScraper",
    "UrbanListSGScraper",
    "AlexisCheongScraper",
    "HungryGoWhereScraper",
    "LadyIronChefScraper",
    "SethLuiScraper",
]
