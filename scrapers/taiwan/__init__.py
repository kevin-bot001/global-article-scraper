# -*- coding: utf-8 -*-
"""
Taiwan 爬虫
"""
from .eating_in_taipei import EatingInTaipeiScraper
# Pagination
from .openrice_tw import OpenRiceTWScraper

__all__ = [
    "EatingInTaipeiScraper",
    "OpenRiceTWScraper",
]
