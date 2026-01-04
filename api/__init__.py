"""
Paquete de scrapers para JobScraper
Importa todos los scrapers disponibles
"""

from scrapers.artstation import ArtStationScraper
from scrapers.gamejobs import GameJobsScraper
from scrapers.hitmarker import HitmarkerScraper

__all__ = [
    'ArtStationScraper',
    'GameJobsScraper',
    'HitmarkerScraper',
]

__version__ = '1.0.0'