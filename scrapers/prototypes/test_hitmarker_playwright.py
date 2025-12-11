"""
Scraper de Hitmarker con Playwright
Proyecto: Sistema de Búsqueda Indie/Outsourcing
Autor: Cristian Meza Venegas

Este scraper usa Playwright para evitar bloqueos de Hitmarker.
Enfocado en Character Artist positions, especialmente Entry Level.
"""

import sys
import os
import json
import time
import re
from datetime import datetime

# Agregar carpeta raíz al path para imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scraper_base import PlaywrightScraper


class HitmarkerScraper(PlaywrightScraper):
    """Scraper específico para Hitmarker Jobs con filtros Character Artist"""

    def __init__(self, headless: bool = False):
        """
        Inicializar scraper de Hitmarker

        Args:
            headless: False para VER el navegador (útil para debugging)
        """
        super().__init__(headless=headless, delay=2)
        # Filtro directo por Character
        self.base_url = "https://hitmarker.net/jobs?keyword=character"

    # ---------------------------------------------------------
    # FILTROS / CLASIFICADORES
    # ---------------------------------------------------------

    def _is_character_artist(self, title: str) -> bool:
        """
        Determinar si el trabajo es para Character Artist
        """
        title_lower = title.lower()

        character_keywords = [
            'character artist',
            '3d character',
            'character model',
            'character designer',
            'character sculpt',
            'character rigger',
            'character animator',
            'creature artist',
        ]

        related_keywords = [
            '3d artist',
            '3d modeler',
            '3d generalist',
            'game artist',
            'asset artist',
        ]

        for keyword in character_keywords:
            if keyword in title_lower:
                return True

        for keyword in related_keywords:
            if keyword in title_lower:
                return True

        return False

    def _is_entry_level(self, title: str, description: str = '') -> bool:
        """
        Determinar si es posición entry-level o junior
        """
        text_lower = f"{title} {description}".lower()

        entry_keywords = [
            'junior',
            'entry level',
            'entry-level',
            'associate',
            'graduate',
            'intern',
            'trainee',
            '0-2 years',
            '1-2 years',
            'early career',
        ]

        for keyword in entry_keywords:
            if keyword in text_lower:
                return True

        senior_keywords = [
            'senior',
            'lead',
            'principal',
            'director',
            'head of',
            '5+ years',
            '3+ years',
            'experienced',
        ]

        for keyword in senior_keywords:
            if keyword in text_lower:
                return False

        return True

    def _extract_experience_years(self, description: str) -> str:
        """
        Extraer años de experiencia requeridos desde texto
        """
        patterns = [
            r'(\d+)\+?\s*years?',
            r'(\d+)-(\d+)\s*years?',
        ]

        for pattern in patterns:
            match = re.search(pattern, description.lower())
            if match:
                return match.group(0)

        return "Not specified"

    def _calculate_relevance(self, is_character: bool, is_entry: bool) -> int:
        """
        Score 0–10 basado en Character + Entry Level
        """
        score = 0
        if is_character:
            score += 6
        if is_entry:
            score += 4
        return score

    # ---------------------------------------------------------
    # SCRAPING PRINCIPAL
    # ---------------------------------------------------------

    def scrape_jobs(self) -> list:
        """
        Extraer trabajos desde Hitmarker con filtrado
        """
        print("\n" + "=" * 70)
        print("SCRAPER DE HITMARKER - CHARACTER ARTIST FOCUS")
        print("=" * 70)

        jobs = []

        try:
            print("\n→ Navegando a Hitmarker Jobs...")
            success = self.navigate_to(self.base_url)

            if not success:
                print("✗ No se pudo cargar la página")
                return jobs

            print("→ Esperando carga inicial...")
            time.sleep(4)

            print("→ Scroll para cargar todos los resultados...")
            self.scroll_page(times=6)

            screenshot_path = "../../research/platform_tests/hitmarker_playwright.png"
            self.screenshot(screenshot_path)
            print("✓ Screenshot guardado")

            print("→ Extrayendo HTML completo...")
            html = self.get_html()
            soup = self.parse_html(html)

            html_path = "../../research/platform_tests/hitmarker_playwright.html"
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html)
            print(f"✓ HTML guardado en: {html_path}")

            # Selectores basados en análisis de Hitmarker
            print("\n→ Buscando trabajos en DOM...")

            job_elements = soup.select("a[href*='/jobs/']")

            if not job_elements:
                print("❌ No se encontraron trabajos — revisar HTML guardado.")
                return []

            print(f"✔ Encontrados {len(job_elements)} trabajos potenciales")

            # ---------------------------------------------------------
            # EXTRAER CAMPOS
            # ---------------------------------------------------------

            for i, elem in enumerate(job_elements):
                try:
                    href = elem.get("href", "")
                    title = elem.get_text(" ", strip=True)

                    url = href if href.startswith("http") else f"https://hitmarker.net{href}"

                    company_elem = elem.select_one(".meta .company")
                    company = company_elem.get_text(strip=True) if company_elem else "N/A"

                    location_elem = elem.select_one(".meta .location")
                    location_info = location_elem.get_text(" ", strip=True) if location_elem else "N/A"

                    text_blob = f"{title} {location_info}"

                    is_character = self._is_character_artist(title)
                    is_entry = self._is_entry_level(title, location_info)
                    experience = self._extract_experience_years(text_blob)

                    job = {
                        "platform": "Hitmarker",
                        "title": title,
                        "company": company,
                        "location_info": location_info,
                        "url": url,
                        "experience_required": experience,
                        "scraped_at": datetime.now().isoformat(),

                        "is_character_artist": is_character,
                        "is_entry_level": is_entry,
                        "relevance_score": self._calculate_relevance(is_character, is_entry)
                    }

                    jobs.append(job)

                    # LOG VISUAL
                    if is_character:
                        level = "🟢 ENTRY" if is_entry else "🔵 MID/SR"
                        print(f"  [{i+1:2d}] {level} | {title[:50]}")
                    else:
                        print(f"  [{i+1:2d}] ⚪ OTHER | {title[:50]}")

                except Exception as e:
                    print(f"✗ Error procesando item {i+1}: {e}")
                    continue

            print(f"\n✔ Extracción completada: {len(jobs)} trabajos procesados")
            return jobs

        except Exception as e:
            print("\n❌ ERROR GENERAL")
            print(e)
            return jobs


# ---------------------------------------------------------
# MAIN — IGUAL A TU ARTSTATION SCRAPER
# ---------------------------------------------------------

def main():
    print("\n" + "=" * 70)
    print("HITMARKER SCRAPER - CHARACTER ARTIST ENTRY LEVEL")
    print("=" * 70)
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("Objetivo: Encontrar posiciones Character Artist (Entry Level)")
    print("=" * 70)

    with HitmarkerScraper(headless=False) as scraper:
        jobs = scraper.scrape_jobs()

    # ---------------------------------------------------------
    # CLASIFICACIÓN
    # ---------------------------------------------------------

    character_jobs = [j for j in jobs if j.get('is_character_artist')]
    entry_jobs = [j for j in character_jobs if j.get('is_entry_level')]
    mid_senior_jobs = [j for j in character_jobs if not j.get('is_entry_level')]
    other_jobs = [j for j in jobs if not j.get('is_character_artist')]

    print("\n" + "=" * 70)
    print("CLASIFICANDO RESULTADOS")
    print("=" * 70)

    print("\n📊 ESTADÍSTICAS:")
    print(f"  Total scraped: {len(jobs)}")
    print(f"  Character Artist: {len(character_jobs)}")
    print(f"    └─ 🟢 Entry Level: {len(entry_jobs)}")
    print(f"    └─ 🔵 Mid/Senior: {len(mid_senior_jobs)}")
    print(f"  Other roles: {len(other_jobs)}")

    # Ordenar por relevancia
    character_sorted = sorted(
        character_jobs,
        key=lambda x: x.get('relevance_score', 0),
        reverse=True
    )

    # ---------------------------------------------------------
    # GUARDAR RESULTADOS
    # ---------------------------------------------------------

    result = {
        "platform": "Hitmarker",
        "scrape_date": datetime.now().isoformat(),
        "filters_applied": {
            "target_role": "Character Artist",
            "target_level": "Entry Level (preferred)",
            "keywords_used": [
                'character artist', '3d character', 'character modeler',
                'junior', 'entry level', 'associate'
            ]
        },
        "summary": {
            "total_scraped": len(jobs),
            "character_artist_total": len(character_jobs),
            "entry_level_count": len(entry_jobs),
            "mid_senior_count": len(mid_senior_jobs),
            "other_roles_count": len(other_jobs),
        },
        "jobs": {
            "top_matches_entry_level": entry_jobs,
            "character_artist_mid_senior": mid_senior_jobs,
            "all_character_artist": character_sorted,
            "all_jobs": jobs
        }
    }

    result_file = "../../research/platform_tests/hitmarker_playwright_result.json"
    with open(result_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"\n💾 Resultados guardados en: {result_file}")

    # ---------------------------------------------------------
    # IMPRIMIR TOP ENTRY LEVEL
    # ---------------------------------------------------------

    if entry_jobs:
        print("\n" + "=" * 70)
        print("🎯 TOP POSICIONES ENTRY LEVEL")
        print("=" * 70)

        for i, job in enumerate(entry_jobs[:5], 1):
            print(f"\n{i}. {job['title']}")
            print(f"   🏢 {job['company']}")
            print(f"   📍 {job['location_info']}")
            print(f"   🎓 Exp: {job['experience_required']}")
            print(f"   🔗 {job['url']}")
            print(f"   ⭐ {job['relevance_score']}/10")

    elif character_jobs:
        print("\n⚠ No hay entry level pero sí Character Artist.")
    else:
        print("\n⚠ No se encontraron Character Artist.")

    print("\n" + "=" * 70)
    print("📁 ARCHIVOS GENERADOS")
    print("=" * 70)
    print("  1. hitmarker_playwright.html")
    print("  2. hitmarker_playwright.png")
    print("  3. hitmarker_playwright_result.json")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
