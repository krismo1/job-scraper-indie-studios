"""
Scraper de GameJobs.co con Playwright
Proyecto: Sistema de Búsqueda Character Artists
Autor: Cristian Meza Venegas

Scraper para GameJobs.co enfocado en posiciones de Character Artist
"""

import sys
import os
import json
import time
import re
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scraper_base import PlaywrightScraper


class GameJobsScraper(PlaywrightScraper):
    """Scraper específico para GameJobs.co"""

    def __init__(self, headless: bool = False):
        super().__init__(headless=headless, delay=2)
        self.base_url = "https://gamejobs.co"
        self.search_url = "https://gamejobs.co/search?q=3d+character+artist"

    def _is_character_artist(self, title: str, description: str = '') -> bool:
        """Determinar si es posición de Character Artist"""
        text_lower = f"{title} {description}".lower()

        character_keywords = [
            'character artist',
            'character modeler',
            'character designer',
            '3d character',
            'character animator',
            'character sculptor',
            'organic modeler',
        ]

        related_keywords = [
            '3d artist',
            '3d generalist',
            'game artist',
            'asset artist',
        ]

        for keyword in character_keywords:
            if keyword in text_lower:
                return True

        for keyword in related_keywords:
            if keyword in text_lower:
                return True

        return False

    def _is_entry_level(self, title: str, description: str = '') -> bool:
        """Determinar si es posición entry-level"""
        text_lower = f"{title} {description}".lower()

        entry_keywords = [
            'junior',
            'entry level',
            'entry-level',
            'associate',
            'graduate',
            '0-2 years',
            '1-2 years',
            'regular',  # GameJobs usa "Regular" para no-senior
        ]

        for keyword in entry_keywords:
            if keyword in text_lower:
                return True

        senior_keywords = [
            'senior',
            'lead',
            'principal',
            'director',
            '5+ years',
            '3+ years',
        ]

        for keyword in senior_keywords:
            if keyword in text_lower:
                return False

        return True

    def _extract_location(self, location_text: str) -> dict:
        """Extraer información de ubicación"""
        location_text = location_text.strip()

        remote_keywords = ['remote', 'anywhere', 'work from home']
        is_remote = any(keyword in location_text.lower() for keyword in remote_keywords)

        return {
            'raw': location_text,
            'is_remote': is_remote,
            'city': location_text if not is_remote else 'Remote',
        }

    def _extract_experience_level(self, text: str) -> str:
        """Extraer nivel de experiencia del texto"""
        text_lower = text.lower()

        if 'senior' in text_lower or 'lead' in text_lower:
            return 'Senior'
        elif 'principal' in text_lower:
            return 'Principal'
        elif 'junior' in text_lower or 'entry' in text_lower:
            return 'Junior'
        elif 'regular' in text_lower:
            return 'Regular'
        else:
            return 'Not specified'

    def _calculate_relevance(self, is_character: bool, is_entry: bool,
                             company: str = '') -> int:
        """Calcular score de relevancia 0-10"""
        score = 0

        if is_character:
            score += 6

        if is_entry:
            score += 3

        # Bonus si es empresa conocida de outsourcing
        outsourcing_companies = [
            'keywords', 'virtuos', 'streamline', 'ptw', 'sperasoft',
            'liquid development', 'magic media', 'dekogon'
        ]

        company_lower = company.lower()
        if any(outsource in company_lower for outsource in outsourcing_companies):
            score += 1

        return min(score, 10)

    def scrape_jobs(self) -> list:
        """Scraper principal de GameJobs"""
        print("\n" + "=" * 70)
        print("SCRAPER DE GAMEJOBS.CO - CHARACTER ARTIST FOCUS")
        print("=" * 70)

        jobs = []

        try:
            print(f"\n→ Navegando a {self.search_url}...")
            success = self.navigate_to(self.search_url)

            if not success:
                print("✗ No se pudo cargar la página")
                return jobs

            print("→ Esperando carga de resultados...")
            time.sleep(3)

            print("→ Haciendo scroll para cargar más ofertas...")
            self.scroll_page(times=3)

            screenshot_path = "../../research/platform_tests/gamejobs_playwright.png"
            self.screenshot(screenshot_path)
            print(f"✓ Screenshot guardado")

            print("→ Extrayendo HTML...")
            html = self.get_html()
            soup = self.parse_html(html)

            html_path = "../../research/platform_tests/gamejobs_playwright.html"
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html)
            print(f"✓ HTML guardado en: {html_path}")

            print("\n→ Buscando ofertas...")

            # Basado en tu screenshot: <a class="title" href="/Senior-3D-Character-Artist...">
            job_links = soup.select('a.title')

            if not job_links:
                print("⚠️  No se encontró 'a.title', intentando alternativas...")
                job_links = (
                        soup.select('a[href*="/"]') or
                        soup.select('.job') or
                        soup.select('article')
                )

            if not job_links:
                print("❌ No se encontraron ofertas")
                return [{
                    "platform": "GameJobs",
                    "status": "NO_JOBS_FOUND",
                    "html_file": html_path,
                    "screenshot": screenshot_path,
                    "timestamp": datetime.now().isoformat(),
                }]

            print(f"✅ Encontrados {len(job_links)} links de trabajos")

            # Extraer información de cada job
            print("\n→ Procesando ofertas...")

            for i, link in enumerate(job_links):
                try:
                    # Título está en el <a class="title">
                    title = link.get_text(strip=True)

                    # URL del trabajo
                    href = link.get('href', '')
                    if href.startswith('/'):
                        url = f"{self.base_url}{href}"
                    else:
                        url = href

                    # Buscar contenedor padre para más info
                    parent = link.find_parent('div', class_='job') or link.find_parent()

                    # Empresa - buscar cerca del link
                    company_elem = None
                    if parent:
                        company_elem = (
                                parent.find('a', class_='company') or
                                parent.find('span', class_='company') or
                                parent.find('div', class_='company')
                        )
                    company = company_elem.get_text(strip=True) if company_elem else 'N/A'

                    # Ubicación
                    location_elem = None
                    if parent:
                        location_elem = (
                                parent.find(class_='location') or
                                parent.find('span', string=re.compile(r'Remote|remote'))
                        )
                    location_raw = location_elem.get_text(strip=True) if location_elem else 'N/A'
                    location_data = self._extract_location(location_raw)

                    # Nivel de experiencia (buscar en tags o inline)
                    experience_level = self._extract_experience_level(f"{title} {location_raw}")

                    # Aplicar filtros
                    is_character = self._is_character_artist(title)
                    is_entry = self._is_entry_level(title, location_raw)

                    # Construir objeto job
                    job = {
                        'platform': 'GameJobs',
                        'title': title,
                        'company': company,
                        'location': location_data['city'],
                        'location_raw': location_raw,
                        'is_remote': location_data['is_remote'],
                        'url': url,
                        'experience_level': experience_level,
                        'scraped_at': datetime.now().isoformat(),

                        # Filtros
                        'is_character_artist': is_character,
                        'is_entry_level': is_entry,
                        'relevance_score': self._calculate_relevance(
                            is_character, is_entry, company
                        )
                    }

                    jobs.append(job)

                    # Display con indicadores
                    if is_character:
                        level = "🟢 ENTRY" if is_entry else "🔵 MID/SR"
                        print(f"  [{i+1:2d}] {level} | {title[:50]}")
                        print(f"       └─ {company} | {location_data['city']}")
                    else:
                        print(f"  [{i+1:2d}] ⚪ OTHER | {title[:50]}")

                except Exception as e:
                    print(f"  ✗ Error en trabajo {i+1}: {e}")
                    continue

            print(f"\n✅ Extracción completada: {len(jobs)} trabajos procesados")
            return jobs

        except Exception as e:
            print(f"\n❌ ERROR GENERAL: {e}")
            import traceback
            traceback.print_exc()
            return jobs


def main():
    """Función principal de prueba"""
    print("\n" + "=" * 70)
    print("GAMEJOBS.CO SCRAPER - CHARACTER ARTIST ENTRY LEVEL")
    print("=" * 70)
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    with GameJobsScraper(headless=False) as scraper:
        jobs = scraper.scrape_jobs()

    # Clasificar resultados
    print("\n" + "=" * 70)
    print("CLASIFICANDO RESULTADOS")
    print("=" * 70)

    character_jobs = [j for j in jobs if j.get('is_character_artist', False)]
    entry_jobs = [j for j in character_jobs if j.get('is_entry_level', False)]
    mid_senior_jobs = [j for j in character_jobs if not j.get('is_entry_level', False)]
    other_jobs = [j for j in jobs if not j.get('is_character_artist', False)]

    print(f"\n📊 ESTADÍSTICAS:")
    print(f"  Total scraped: {len(jobs)}")
    print(f"  Character Artist: {len(character_jobs)} ({len(character_jobs)/len(jobs)*100 if jobs else 0:.1f}%)")
    print(f"    └─ 🟢 Entry Level: {len(entry_jobs)}")
    print(f"    └─ 🔵 Mid/Senior: {len(mid_senior_jobs)}")
    print(f"  Other roles: {len(other_jobs)}")

    # Ordenar por relevancia
    character_jobs_sorted = sorted(
        character_jobs,
        key=lambda x: x.get('relevance_score', 0),
        reverse=True
    )

    # Guardar resultados
    result = {
        'platform': 'GameJobs',
        'scrape_date': datetime.now().isoformat(),
        'search_url': 'https://gamejobs.co/search?q=3d+character+artist',
        'filters_applied': {
            'target_role': 'Character Artist',
            'target_level': 'Entry Level (preferred)',
        },
        'summary': {
            'total_scraped': len(jobs),
            'character_artist_total': len(character_jobs),
            'entry_level_count': len(entry_jobs),
            'mid_senior_count': len(mid_senior_jobs),
            'other_roles_count': len(other_jobs),
        },
        'jobs': {
            'top_matches_entry_level': entry_jobs,
            'character_artist_mid_senior': mid_senior_jobs,
            'all_character_artist': character_jobs_sorted,
            'all_jobs': jobs
        }
    }

    result_file = "../../research/platform_tests/gamejobs_playwright_result.json"
    with open(result_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"\n💾 Resultados guardados en: {result_file}")

    # Mostrar top resultados
    if entry_jobs:
        print("\n" + "=" * 70)
        print("🎯 TOP POSICIONES ENTRY LEVEL")
        print("=" * 70)

        for i, job in enumerate(entry_jobs[:5], 1):
            print(f"\n{i}. {job['title']}")
            print(f"   🏢 {job['company']}")
            print(f"   📍 {job['location']} {'(Remote)' if job['is_remote'] else ''}")
            print(f"   📊 Nivel: {job['experience_level']}")
            print(f"   🔗 {job['url']}")
            print(f"   ⭐ Relevancia: {job['relevance_score']}/10")

    print("\n" + "=" * 70)
    print("📁 ARCHIVOS GENERADOS")
    print("=" * 70)
    print("  1. gamejobs_playwright.html")
    print("  2. gamejobs_playwright.png")
    print("  3. gamejobs_playwright_result.json")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()