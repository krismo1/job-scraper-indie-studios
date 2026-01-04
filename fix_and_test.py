"""
Script para regenerar todos los scrapers
"""

import os

# Crear carpeta scrapers si no existe
os.makedirs('scrapers', exist_ok=True)

print("Regenerando scrapers...")

# __init__.py
with open('scrapers/__init__.py', 'w', encoding='utf-8') as f:
    f.write('''"""
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
''')

print("✅ __init__.py creado")
print("\nAhora copia manualmente:")
print("1. El contenido de artstation.py")
print("2. El contenido de gamejobs.py")
print("3. El contenido de hitmarker.py")
print("\nDe los artifacts que te di.")