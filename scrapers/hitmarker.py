"""
Scraper de Hitmarker.net
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


class HitmarkerScraper(PlaywrightScraper):
    """Scraper de Hitmarker.net"""

    def __init__(self, headless: bool = True):
        super().__init__(headless=headless, delay=2)
        self.base_url = "https://hitmarker.net/jobs?keyword=character"

    def _is_character_artist(self, title: str) -> bool:
        """Determinar si es Character Artist"""
        title_lower = title.lower()

        character_keywords = [
            'character artist', '3d character', 'character model',
            'character designer', 'character sculpt', 'character rigger',
            'character animator', 'creature artist',
        ]

        related_keywords = [
            '3d artist', '3d modeler', '3d generalist',
            'game artist', 'asset artist',
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
            'graduate', 'intern', 'trainee', '0-2 years',
            '1-2 years', 'early career',
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
        """Extraer ID único"""
        match = re.search(r'/jobs/(\d+)', url)
        if match:
            return f"hitmarker_{match.group(1)}"
        return f"hitmarker_{hashlib.md5(url.encode()).hexdigest()[:12]}"

    def scrape_jobs(self) -> list[dict]:
        """Scraper principal"""
        print("\n" + "=" * 70)
        print("🎯 SCRAPER DE HITMARKER - CHARACTER ARTIST FOCUS")
        print("=" * 70)

        jobs = []

        try:
            print("\n→ Navegando a Hitmarker...")
            success = self.navigate_to(self.base_url)

            if not success:
                print("✗ No se pudo cargar")
                return jobs

            print("→ Esperando carga...")
            time.sleep(4)

            print("→ Haciendo scroll...")
            self.scroll_page(times=5)

            print("→ Extrayendo trabajos...")
            html = self.get_html()
            soup = self.parse_html(html)

            job_elements = soup.select("a[href*='/jobs/']")

            if not job_elements:
                print("❌ No se encontraron trabajos")
                return jobs

            print(f"✅ Encontrados {len(job_elements)} elementos\n")

            seen_urls = set()

            for elem in job_elements:
                try:
                    href = elem.get("href", "")

                    if href.startswith("http"):
                        url = href
                    else:
                        url = f"https://hitmarker.net{href}"

                    if url in seen_urls:
                        continue
                    seen_urls.add(url)

                    title = elem.get_text(" ", strip=True)

                    if len(title) < 5 or len(title) > 200:
                        continue

                    parent = elem.find_parent('div') or elem.find_parent('article')
                    company = 'Unknown'

                    if parent:
                        company_elem = parent.find(class_='company')
                        if company_elem:
                            company = company_elem.get_text(strip=True).replace('Company:', '').strip()

                    location_info = None
                    if parent:
                        location_elem = parent.find(class_='location')
                        if location_elem:
                            location_info = location_elem.get_text(" ", strip=True)

                    remote_type = None
                    if location_info and 'remote' in location_info.lower():
                        remote_type = 'Remote'

                    is_character = self._is_character_artist(title)
                    is_entry = self._is_entry_level(title, location_info or '')

                    job = {
                        'platform': 'Hitmarker',
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
                        print(f"  [{len(jobs):2d}] {level} | {title[:50]}")
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