"""
Scraper de ArtStation Jobs
Autor: Cristian Meza Venegas
"""

import sys
import os
import time
import re
import hashlib
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scraper_base import PlaywrightScraper


class ArtStationScraper(PlaywrightScraper):
    """Scraper de ArtStation Jobs con filtros Character Artist"""

    def __init__(self, headless: bool = True):
        super().__init__(headless=headless, delay=2)
        self.base_url = "https://www.artstation.com/jobs"

    def _is_character_artist(self, title: str) -> bool:
        """Determinar si es Character Artist"""
        title_lower = title.lower()

        character_keywords = [
            'character artist', 'character modeler', 'character designer',
            '3d character', 'character animator', 'character sculptor',
            'character rigger',
        ]

        related_keywords = [
            '3d artist', '3d generalist', 'game artist',
            'asset artist', 'organic modeler',
        ]

        for keyword in character_keywords:
            if keyword in title_lower:
                return True

        for keyword in related_keywords:
            if keyword in title_lower:
                return True

        return False

    def _is_entry_level(self, title: str, description: str = '') -> bool:
        """Determinar si es entry level"""
        text_lower = f"{title} {description}".lower()

        entry_keywords = [
            'junior', 'entry level', 'entry-level', 'associate',
            'graduate', 'intern', 'trainee', '0-2 years', '1-2 years',
            'early career', 'less than 2 years',
        ]

        for keyword in entry_keywords:
            if keyword in text_lower:
                return True

        senior_keywords = [
            'senior', 'lead', 'principal', 'director',
            'head of', '5+ years', '3+ years', 'experienced',
        ]

        for keyword in senior_keywords:
            if keyword in text_lower:
                return False

        return True

    def _calculate_relevance(self, is_character: bool, is_entry: bool) -> int:
        """Calcular relevancia 0-10"""
        score = 0
        if is_character:
            score += 6
        if is_entry:
            score += 4
        return score

    def _extract_external_id(self, url: str) -> str:
        """Extraer ID único desde URL"""
        match = re.search(r'/jobs/(\d+)', url)
        if match:
            return f"artstation_{match.group(1)}"
        return f"artstation_{hashlib.md5(url.encode()).hexdigest()[:12]}"

    def scrape_jobs(self) -> list[dict]:
        """Scraper principal"""
        print("\n" + "=" * 70)
        print("🎨 SCRAPER DE ARTSTATION - CHARACTER ARTIST FOCUS")
        print("=" * 70)

        jobs = []

        try:
            print("\n→ Navegando a ArtStation Jobs...")
            success = self.navigate_to(self.base_url)

            if not success:
                print("✗ No se pudo cargar la página")
                return jobs

            print("→ Esperando carga completa...")
            time.sleep(4)

            print("→ Haciendo scroll...")
            self.scroll_page(times=3)

            print("→ Extrayendo trabajos...")
            html = self.get_html()
            soup = self.parse_html(html)

            job_elements = soup.select('.job-grid-item')

            if not job_elements:
                print("⚠️  Intentando selectores alternativos...")
                job_elements = (
                        soup.select('[class*="job-grid"]') or
                        soup.select('article') or
                        soup.select('[class*="job"]')
                )

            if not job_elements:
                print("❌ No se encontraron trabajos")
                return jobs

            print(f"✅ Encontrados {len(job_elements)} trabajos\n")

            for i, job_elem in enumerate(job_elements):
                try:
                    title_elem = (
                            job_elem.select_one('.job-grid-item-title-holder') or
                            job_elem.select_one('h2') or
                            job_elem.select_one('h3') or
                            job_elem.select_one('[class*="title"]')
                    )

                    company_elem = (
                            job_elem.select_one('.job-grid-item-company') or
                            job_elem.select_one('[class*="company"]')
                    )

                    info_elem = job_elem.select_one('.job-grid-item-info')
                    location_info = info_elem.get_text(strip=True) if info_elem else None

                    link_elem = job_elem.select_one('a[href*="/jobs/"]')

                    title = title_elem.get_text(strip=True) if title_elem else None
                    company = company_elem.get_text(strip=True) if company_elem else None
                    url = link_elem.get('href', '') if link_elem else ''

                    if url.startswith('/jobs/'):
                        url = f"https://www.artstation.com{url}"

                    if not all([url, title, company]):
                        continue

                    is_character = self._is_character_artist(title)
                    is_entry = self._is_entry_level(title, location_info or '')

                    remote_type = None
                    if location_info and 'remote' in location_info.lower():
                        remote_type = 'Remote'

                    job = {
                        'platform': 'ArtStation',
                        'external_id': self._extract_external_id(url),
                        'url': url,
                        'title': title,
                        'company': company,
                        'location': location_info,
                        'remote_type': remote_type,
                        'description': None,
                        'company_size': None,
                        'company_type': None,
                        'is_character_artist': is_character,
                        'is_entry_level': is_entry,
                        'relevance_score': self._calculate_relevance(is_character, is_entry),
                        'posted_date': None,
                        'scraped_at': datetime.now().isoformat(),
                    }

                    jobs.append(job)

                    if is_character:
                        level = "🟢 ENTRY" if is_entry else "🔵 MID/SR"
                        print(f"  [{i+1:2d}] {level} | {title[:50]}")
                        print(f"       └─ {company}")

                except Exception as e:
                    continue

            print(f"\n✅ Procesados: {len(jobs)} trabajos")

            character_jobs = [j for j in jobs if j['is_character_artist']]
            entry_jobs = [j for j in character_jobs if j['is_entry_level']]

            print(f"\n📊 ESTADÍSTICAS:")
            print(f"   Total: {len(jobs)}")
            print(f"   Character Artists: {len(character_jobs)} ({len(character_jobs)/len(jobs)*100 if jobs else 0:.1f}%)")
            print(f"   └─ 🟢 Entry: {len(entry_jobs)}")
            print(f"   └─ 🔵 Mid/Sr: {len(character_jobs) - len(entry_jobs)}")

            return jobs

        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            return jobs

    def to_db_job(self, job: dict) -> dict:
        """Convierte job a formato compatible con Supabase"""
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