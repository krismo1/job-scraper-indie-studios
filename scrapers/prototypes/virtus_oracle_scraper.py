"""
MULTI-PLATFORM SCRAPER — Virtuos + Oracle HCM
Salida formateada estilo ArtStation (Cristian Meza)
"""

import sys
import os
import json
import time
import re
from datetime import datetime
from typing import List, Dict

# Añadir path raíz para imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scraper_base import PlaywrightScraper


# =============================================================
# 🔵 VISUAL LOGGING (estilo PRO igual al screenshot)
# =============================================================

def line():
    print("=" * 65)

def print_header(title: str, icon: str = "📌"):
    line()
    print(f"{icon} {title.upper()}")
    line()

def print_step(msg: str):
    print(f"→ {msg}")

def print_success(msg: str):
    print(f"✔️  {msg}")

def print_warning(msg: str):
    print(f"⚠️  {msg}")

def print_error(msg: str):
    print(f"❌ {msg}")

def print_job(index: int, job: dict):
    print(f"\n{index}. {job['title']}")
    print(f"   🏢 Empresa: {job['company']}")
    print(f"   📍 Info: {job['location_info']}")
    print(f"   📝 Experiencia: {job['experience_required']}")
    print(f"   🔗 URL: {job['url']}")
    print(f"   ⭐ Relevancia: {job['relevance_score']}/10")


# =============================================================
# 📌 SCROLL INFINITO (hasta que no cargue más)
# =============================================================

def scroll_until_no_change(page, pause=2.5, max_loops=25):
    last_height = 0
    loops = 0

    while loops < max_loops:
        height = page.evaluate("() => document.body.scrollHeight")
        if height == last_height:
            break
        page.evaluate("() => window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(pause)
        last_height = height
        loops += 1


# =============================================================
# 🔵 SCRAPER MULTI-PLATAFORMA
# =============================================================

class MultiPlatformScraper(PlaywrightScraper):

    def __init__(self, headless=True, delay=2):
        super().__init__(headless=headless, delay=delay)
        self.platforms = {
            "virtuos": "https://www.virtuosgames.com/careers/",
            "oracle_hcm": "https://fa-exhj-saasfaprod1.fa.ocs.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1/jobs"
        }

    # ---------------------------
    # 🔍 DETECCIÓN DE RELEVANCIA
    # ---------------------------

    def _is_character_artist(self, title: str) -> bool:
        title_lower = title.lower()
        keywords = [
            'character', 'rigger', 'rigging', 'creature', '3d artist',
            'generalist', 'modeler', 'modeller', 'concept artist'
        ]
        return any(k in title_lower for k in keywords)

    def _is_entry_level(self, title: str, description: str = '') -> bool:
        text = (title + " " + description).lower()
        entry_kw = ['junior', 'entry', 'associate', 'trainee', 'intern', '0-2 years']
        senior_kw = ['senior', 'lead', 'principal', 'director']
        if any(k in text for k in senior_kw):
            return False
        return any(k in text for k in entry_kw) or True

    def _extract_experience_years(self, description: str) -> str:
        patterns = [
            r'(\d+)\+?\s*years?',
            r'(\d+)-(\d+)\s*years?',
        ]
        for p in patterns:
            m = re.search(p, description.lower())
            if m:
                return m.group(0)
        return "Not specified"

    def _calculate_relevance(self, is_char, is_entry):
        score = 0
        if is_char: score += 6
        if is_entry: score += 4
        return score

    def _normalize_url(self, href, base):
        if href.startswith("http"):
            return href
        return base.rstrip("/") + "/" + href.lstrip("/")

    # =============================================================
    # 🟣 SCRAPER VIRTUOS
    # =============================================================

    def _scrape_virtuos(self) -> List[Dict]:
        results = []
        base = self.platforms["virtuos"]

        print_header("SCRAPER VIRTUOS", "🎮")
        print_step(f"Navegando a {base}")

        if not self.navigate_to(base):
            print_error("No se pudo cargar Virtuos")
            return results

        time.sleep(4)
        scroll_until_no_change(self.page)

        html = self.get_html()
        soup = self.parse_html(html)

        job_links = soup.select("a[href*='job']") or soup.select("a[href*='careers']")

        for a in job_links:
            try:
                href = a.get("href")
                title = a.get_text(strip=True)
                url = self._normalize_url(href, base)

                job = {
                    'platform': "Virtuos",
                    'title': title,
                    'company': "Virtuos",
                    'location_info': "N/A",
                    'url': url,
                    'experience_required': "Not specified",
                    'scraped_at': datetime.now().isoformat(),
                }

                job['is_character_artist'] = self._is_character_artist(title)
                job['is_entry_level'] = self._is_entry_level(title)
                job['relevance_score'] = self._calculate_relevance(
                    job['is_character_artist'], job['is_entry_level']
                )

                results.append(job)

            except:
                continue

        print_success(f"{len(results)} trabajos detectados en Virtuos")
        return results

    # =============================================================
    # 🟠 SCRAPER ORACLE CLOUD HCM
    # =============================================================

    def _scrape_oracle_hcm(self) -> List[Dict]:
        results = []
        base = self.platforms["oracle_hcm"]

        print_header("SCRAPER ORACLE HCM", "☁️")
        print_step(f"Navegando a {base}")

        if not self.navigate_to(base):
            print_error("No se pudo cargar Oracle HCM")
            return results

        time.sleep(5)
        scroll_until_no_change(self.page)

        html = self.get_html()
        soup = self.parse_html(html)

        anchors = soup.select("a[href*='requisition']") or soup.select("a[href*='job']")

        for a in anchors:
            try:
                href = a.get("href")
                title = a.get_text(strip=True)
                url = self._normalize_url(href, base)

                job = {
                    'platform': "Oracle_HCM",
                    'title': title,
                    'company': "Oracle / Client",
                    'location_info': "N/A",
                    'url': url,
                    'experience_required': "Not specified",
                    'scraped_at': datetime.now().isoformat(),
                }

                job['is_character_artist'] = self._is_character_artist(title)
                job['is_entry_level'] = self._is_entry_level(title)
                job['relevance_score'] = self._calculate_relevance(
                    job['is_character_artist'], job['is_entry_level']
                )

                results.append(job)

            except:
                continue

        print_success(f"{len(results)} trabajos detectados en Oracle HCM")
        return results

    # =============================================================
    # 🔵 PROCESO PRINCIPAL
    # =============================================================

    def scrape_all(self) -> Dict[str, List[Dict]]:

        print_header("MULTI-PLATFORM SCRAPER", "🚀")

        virtuos = self._scrape_virtuos()
        oracle = self._scrape_oracle_hcm()

        all_results = {
            "virtuos": virtuos,
            "oracle_hcm": oracle
        }

        # --------------------
        # Guardar JSON
        # --------------------
        out_path = "../../research/platform_tests/multi_platform_result.json"
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(all_results, f, indent=2, ensure_ascii=False)

        print_success("Resultados guardados correctamente")

        # --------------------
        # Filtrado TOP MATCHES
        # --------------------
        print_header("TOP POSICIONES ENTRY LEVEL ENCONTRADAS", "🎯")

        filtered = [
            j for group in all_results.values()
            for j in group
            if j["is_entry_level"]
        ]

        if not filtered:
            print_warning("No se encontraron posiciones entry-level")
        else:
            filtered = sorted(filtered, key=lambda x: x["relevance_score"], reverse=True)
            for i, job in enumerate(filtered[:10], 1):
                print_job(i, job)

            print_success(f"{len(filtered)} posiciones entry-level encontradas")

        # --------------------
        # Archivos generados
        # --------------------
        print_header("ARCHIVOS GENERADOS", "📁")
        print("1. multi_platform_result.json (Datos estructurados)")
        line()

        return all_results


# =============================================================
# 🔵 MAIN
# =============================================================

def main():
    print_header("EJECUTANDO MULTI-PLATFORM SCRAPER", "🚀")

    with MultiPlatformScraper(headless=False, delay=2) as scraper:
        scraper.scrape_all()

    print_success("Proceso finalizado")


if __name__ == "__main__":
    main()
