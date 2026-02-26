# -*- coding: utf-8 -*-
"""
Thailand 爬虫
"""
from .bkkfoodie import BKKFoodieScraper
from .bangkok_foodies import BangkokFoodiesScraper
from .clever_thai import CleverThaiScraper

__all__ = [
    "BKKFoodieScraper",
    "BangkokFoodiesScraper",
    "CleverThaiScraper",
]
