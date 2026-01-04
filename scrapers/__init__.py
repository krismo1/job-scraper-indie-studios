"""
Scrapers package
"""

from scrapers.artstation import ArtStationScraper
from scrapers.gamejobs import GameJobsScraper
from scrapers.hitmarker import HitmarkerScraper

__all__ = [
    'ArtStationScraper',
    'GameJobsScraper',
    'HitmarkerScraper',
]
