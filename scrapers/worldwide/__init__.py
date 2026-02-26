# -*- coding: utf-8 -*-
"""
Worldwide 爬虫（跨国/全球站点）
"""
from .timeout import TimeOutScraper
from .culture_trip import CultureTripScraper
from .chope import ChopeScraper
from .honeycombers import HoneycombersScraper
from .the_asia_collective import TheAsiaCollectiveScraper
from .tourteller import TourTellerScraper
from .renaesworld import RenaesWorldScraper
from .lepetitchef import LePetitChefScraper
from .will_fly_for_food import WillFlyForFoodScraper
from .elite_havens import EliteHavensScraper
from .food_fun_travel import FoodFunTravelScraper
from .michelin_guide import MichelinGuideScraper
from .asias_50_best import Asias50BestScraper
from .eater import EaterScraper
from .destinasian import DestinAsianScraper
from .travel_leisure_asia import TravelLeisureAsiaScraper
from .girl_on_a_zebra import GirlOnAZebraScraper
from .hey_roseanne import HeyRoseanneScraper
# Pagination
from .tatler_asia import TatlerAsiaScraper
from .cnn_travel import CnnTravelScraper
from .lonely_planet import LonelyPlanetScraper

__all__ = [
    "TimeOutScraper",
    "CultureTripScraper",
    "ChopeScraper",
    "HoneycombersScraper",
    "TheAsiaCollectiveScraper",
    "TourTellerScraper",
    "RenaesWorldScraper",
    "LePetitChefScraper",
    "WillFlyForFoodScraper",
    "EliteHavensScraper",
    "FoodFunTravelScraper",
    "MichelinGuideScraper",
    "Asias50BestScraper",
    "EaterScraper",
    "DestinAsianScraper",
    "TravelLeisureAsiaScraper",
    "GirlOnAZebraScraper",
    "HeyRoseanneScraper",
    "TatlerAsiaScraper",
    "CnnTravelScraper",
    "LonelyPlanetScraper",
]
