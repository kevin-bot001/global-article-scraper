# -*- coding: utf-8 -*-
"""
Philippines 爬虫
"""
# Sitemap
from .guide_to_ph import GuideToPhScraper
# Pagination
from .booky_ph import BookyPhScraper

__all__ = [
    "GuideToPhScraper",
    "BookyPhScraper",
]
