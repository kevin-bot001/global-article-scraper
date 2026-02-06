# -*- coding: utf-8 -*-
"""
Pagination 模式爬虫
通过分类/分页接口获取文章列表，不使用 Sitemap
适用于没有 Sitemap 或需要按分类过滤的网站
"""
from .alinear import AlinearScraper
from .lonely_planet import LonelyPlanetScraper

__all__ = [
    "AlinearScraper",
    "LonelyPlanetScraper",
]
