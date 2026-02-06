# -*- coding: utf-8 -*-
"""
Playwright 模式爬虫
用于有强力反爬机制的网站，需要浏览器渲染
"""
from .tripcanvas import TripCanvasScraper

__all__ = [
    "TripCanvasScraper",
]
