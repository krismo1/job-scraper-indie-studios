"""
Scraper de GameJobs.co
Autor: Cristian Meza Venegas
"""

import sys
import os
import time
import hashlib
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scraper_base import PlaywrightScraper


class GameJobsScraper(PlaywrightScraper):
    """Scraper de GameJobs.co"""

    def __init__(self, headless: bool = True):
        super().__init__(headless=headless, delay=2)
        self.base_url = "https://gamejobs.co"
        self.search_url = "https://gamejobs.co/search?q=3d+character+artist"

    def _is_character_artist(self, title: str, description: str = '') -> bool:
        """Determinar si es Character Artist"""
        text_lower = f"{title} {description}".lower()

        character_keywords = [
            'character artist', 'character modeler', 'character designer',
            '3d character', 'character animator', 'character sculptor',
            'organic modeler',
        ]

        related_keywords = [
            '3d artist', '3d generalist', 'game artist', 'asset artist',
        ]

        for keyword in character_keywords:
            if keyword in text_lower:
                return True

        for keyword in related_keywords:
            if keyword in text_lower:
                return True

        return False

    def _is_entry_level(self, title: str, description: str = '') -> bool:
        """Determinar si es entry level"""
        text_lower = f"{title} {description}".lower()

        entry_keywords = [
            'junior', 'entry level', 'entry-level', 'associate',
            'graduate', '0-2 years', '1-2 years', 'regular',
        ]

        for keyword in entry_keywords:
            if keyword in text_lower:
                return True

        senior_keywords = [
            'senior', 'lead', 'principal', 'director',
            '5+ years', '3+ years',
        ]

        for keyword in senior_keywords:
            if keyword in text_lower:
                return False

        return True

    def _extract_location(self, location_text: str) -> dict:
        """Extraer info de ubicación"""
        if not location_text:
            return {'location': None, 'remote_type': None}

        location_text = location_text.strip()

        remote_keywords = ['remote', 'anywhere', 'work from home']
        is_remote = any(kw in location_text.lower() for kw in remote_keywords)

        return {
            'location': 'Remote' if is_remote else location_text,
            'remote_type': 'Remote' if is_remote else None,
        }

    def _calculate_relevance(self, is_character: bool, is_entry: bool, company: str = '') -> int:
        """Calcular relevancia 0-10"""
        score = 0

        if is_character:
            score += 6

        if is_entry:
            score += 3

        outsourcing = [
            'keywords', 'virtuos', 'streamline', 'ptw', 'sperasoft',
            'liquid development', 'magic media', 'dekogon'
        ]

        if any(comp in company.lower() for comp in outsourcing):
            score += 1

        return min(score, 10)

    def _extract_external_id(self, url: str) -> str:
        """Extraer ID único"""
        return f"gamejobs_{hashlib.md5(url.encode()).hexdigest()[:12]}"

    def scrape_jobs(self) -> list[dict]:
        """Scraper principal"""
        print("\n" + "=" * 70)
        print("🎮 SCRAPER DE GAMEJOBS - CHARACTER ARTIST FOCUS")
        print("=" * 70)

        jobs = []

        try:
            print(f"\n→ Navegando a {self.search_url}...")
            success = self.navigate_to(self.search_url)

            if not success:
                print("✗ No se pudo cargar")
                return jobs

            print("→ Esperando carga...")
            time.sleep(3)

            print("→ Haciendo scroll...")
            self.scroll_page(times=3)

            print("→ Extrayendo trabajos...")
            html = self.get_html()
            soup = self.parse_html(html)

            job_links = soup.select('a.title')

            if not job_links:
                print("⚠️  Intentando alternativas...")
                job_links = soup.select('a[href*="/"]') or soup.select('.job a')

            if not job_links:
                print("❌ No se encontraron ofertas")
                return jobs

            print(f"✅ Encontrados {len(job_links)} links\n")

            for i, link in enumerate(job_links):
                try:
                    title = link.get_text(strip=True)
                    href = link.get('href', '')

                    if href.startswith('/'):
                        url = f"{self.base_url}{href}"
                    else:
                        url = href

                    if not all([url, title]):
                        continue

                    parent = link.find_parent('div', class_='job') or link.find_parent()

                    company_elem = None
                    if parent:
                        company_elem = (
                                parent.find('a', class_='company') or
                                parent.find('span', class_='company')
                        )
                    company = company_elem.get_text(strip=True) if company_elem else 'Unknown'

                    location_elem = None
                    if parent:
                        location_elem = parent.find(class_='location')
                    location_raw = location_elem.get_text(strip=True) if location_elem else None

                    location_data = self._extract_location(location_raw or '')

                    is_character = self._is_character_artist(title)
                    is_entry = self._is_entry_level(title, location_raw or '')

                    job = {
                        'platform': 'GameJobs',
                        'external_id': self._extract_external_id(url),
                        'url': url,
                        'title': title,
                        'company': company,
                        'location': location_data['location'],
                        'remote_type': location_data['remote_type'],
                        'description': None,
                        'company_size': None,
                        'company_type': None,
                        'is_character_artist': is_character,
                        'is_entry_level': is_entry,
                        'relevance_score': self._calculate_relevance(is_character, is_entry, company),
                        'posted_date': None,
                    }

                    jobs.append(job)

                    if is_character:
                        level = "🟢 ENTRY" if is_entry else "🔵 MID/SR"
                        print(f"  [{i+1:2d}] {level} | {title[:50]}")
                        print(f"       └─ {company}")

                except:
                    continue

            print(f"\n✅ Procesados: {len(jobs)} trabajos")

            character_jobs = [j for j in jobs if j['is_character_artist']]
            entry_jobs = [j for j in character_jobs if j['is_entry_level']]

            print(f"\n📊 ESTADÍSTICAS:")
            print(f"   Total: {len(jobs)}")
            print(f"   Character Artists: {len(character_jobs)}")
            print(f"   └─ 🟢 Entry: {len(entry_jobs)}")
            print(f"   └─ 🔵 Mid/Sr: {len(character_jobs) - len(entry_jobs)}")

            return jobs

        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            return jobs

    def to_db_job(self, job: dict) -> dict:
        """Convierte job a formato Supabase"""
        return {
            'platform': job.get('platform'),
            'external_id': job.get('external_id'),
            'title': job.get('title'),
            'company': job.get('company'),
            'location': job.get('location'),
            'remote_type': job.get('remote_type'),
            'url': job.get('url'),
            'description': job.get('description'),
            'company_size': job.get('company_size'),
            'company_type': job.get('company_type'),
            'is_character_artist': job.get('is_character_artist', False),
            'is_entry_level': job.get('is_entry_level', False),
            'relevance_score': job.get('relevance_score', 0),
            'posted_date': None,
            'scraped_at': job.get('scraped_at'),
        }
