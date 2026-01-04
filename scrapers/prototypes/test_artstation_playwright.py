"""
Scraper de ArtStation con Playwright + Supabase
Proyecto: Sistema de Búsqueda Indie/Outsourcing
Autor: Cristian Meza Venegas

VERSIÓN INTEGRADA CON PERSISTENCIA EN SUPABASE
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

# Imports de base de datos
try:
    from models import (
        SessionLocal,
        save_job,
        start_job_run,
        finish_job_run,
    )

    DB_AVAILABLE = True
    print("✓ Módulo de base de datos cargado correctamente")
except ImportError as e:
    DB_AVAILABLE = False
    print(f"⚠️  Base de datos no disponible: {e}")
    print("   El scraper funcionará pero NO guardará en Supabase")


class ArtStationScraper(PlaywrightScraper):
    """Scraper específico para ArtStation Jobs con filtros Character Artist"""

    def __init__(self, headless: bool = False):
        """
        Inicializar scraper de ArtStation

        Args:
            headless: False para VER el navegador (útil para debugging)
        """
        super().__init__(headless=headless, delay=2)
        self.base_url = "https://www.artstation.com/jobs"

    def _is_character_artist(self, title: str) -> bool:
        """
        Determinar si el trabajo es para Character Artist

        Args:
            title: Título del trabajo

        Returns:
            True si es posición de character artist
        """
        title_lower = title.lower()

        # Keywords principales (alta prioridad)
        character_keywords = [
            'character artist',
            'character modeler',
            'character designer',
            '3d character',
            'character animator',
            'character sculptor',
            'character rigger',
        ]

        # Keywords secundarias (prioridad media - también relevantes)
        related_keywords = [
            '3d artist',
            '3d generalist',
            'game artist',
            'asset artist',
            'organic modeler',
        ]

        # Revisar keywords principales
        for keyword in character_keywords:
            if keyword in title_lower:
                return True

        # Revisar keywords secundarias
        for keyword in related_keywords:
            if keyword in title_lower:
                return True

        return False

    def _is_entry_level(self, title: str, description: str = '') -> bool:
        """
        Determinar si es posición entry-level o junior

        Args:
            title: Título del trabajo
            description: Descripción o información adicional

        Returns:
            True si es entry level
        """
        text_lower = f"{title} {description}".lower()

        # Indicators de entry level
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
            'less than 2 years',
        ]

        for keyword in entry_keywords:
            if keyword in text_lower:
                return True

        # Excluir explícitamente si menciona senior/lead
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

        # Si no menciona nivel específico, asumir que PODRÍA ser entry
        return True

    def _extract_experience_years(self, description: str) -> str:
        """
        Extraer años de experiencia requeridos

        Args:
            description: Texto de descripción

        Returns:
            String con años encontrados o 'Not specified'
        """
        patterns = [
            r'(\d+)\+?\s*years?',
            r'(\d+)-(\d+)\s*years?',
        ]

        for pattern in patterns:
            match = re.search(pattern, description.lower())
            if match:
                return match.group(0)

        return 'Not specified'

    def _calculate_relevance(self, is_character: bool, is_entry: bool) -> int:
        """
        Calcular score de relevancia (0-10)

        Args:
            is_character: Si es posición de character artist
            is_entry: Si es entry level

        Returns:
            Score de 0-10
        """
        score = 0

        if is_character:
            score += 6  # Base para character artist

        if is_entry:
            score += 4  # Bonus para entry level

        return score

    def _to_db_job(self, raw_job: dict) -> dict:
        """
        Convertir job scrapeado al formato del modelo Job (Supabase)

        Args:
            raw_job: Diccionario con datos scrapeados

        Returns:
            Diccionario con formato compatible con modelo Job
        """
        return {
            "platform": "ArtStation",
            "external_id": None,
            "url": raw_job.get("url"),
            "title": raw_job.get("title"),
            "company": raw_job.get("company"),
            "location": raw_job.get("location_info"),
            "remote_type": (
                "Remote"
                if "remote" in (raw_job.get("location_info") or "").lower()
                else None
            ),
            "description": raw_job.get("description"),
            "company_size": None,
            "company_type": None,
            "is_character_artist": raw_job.get("is_character_artist"),
            "is_entry_level": raw_job.get("is_entry_level"),
            "relevance_score": raw_job.get("relevance_score"),
            "posted_date": None
        }

    def scrape_job_detail(self, raw_job: dict) -> dict:
        """
        FASE DETAIL: Entra al job individual y extrae descripción completa

        Args:
            raw_job: Job base con URL

        Returns:
            Job enriquecido con descripción
        """
        job_url = raw_job.get("url")

        if not job_url or not job_url.startswith("http"):
            print("    ⚠️  URL inválida, se omite DETAIL")
            return raw_job

        print(f"    → Visitando detalle: {job_url[:60]}...")

        success = self.navigate_to(job_url)
        if not success:
            print("    ✗ No se pudo cargar el detalle")
            return raw_job

        time.sleep(2)

        html = self.get_html()
        soup = self.parse_html(html)

        # ===== DESCRIPCIÓN =====
        description = None
        description_header = soup.find("h2", string="Job Description")

        if description_header:
            description_block = description_header.find_next("div")
            if description_block:
                description = description_block.get_text(
                    separator="\n", strip=True
                )

        # ===== JOB DETAILS =====
        details_text = soup.get_text(" ", strip=True)

        seniority = "Junior" if "Junior" in details_text else None
        contract_type = "Permanent" if "Permanent" in details_text else None

        # ===== ACTUALIZAR RAW JOB =====
        raw_job["description"] = description
        raw_job["seniority"] = seniority
        raw_job["contract_type"] = contract_type

        return raw_job

    def scrape_jobs(self) -> list:
        """
        FASE LISTADO: Extraer trabajos de ArtStation con filtrado

        Returns:
            Lista de diccionarios con información de trabajos
        """
        print("\n" + "=" * 70)
        print("SCRAPER DE ARTSTATION - CHARACTER ARTIST FOCUS")
        print("=" * 70)

        jobs = []

        try:
            print("\n→ Navegando a ArtStation Jobs...")
            success = self.navigate_to(self.base_url)

            if not success:
                print("✗ No se pudo cargar la página")
                return jobs

            print("→ Esperando carga completa de trabajos...")
            time.sleep(4)

            print("→ Haciendo scroll para cargar más trabajos...")
            self.scroll_page(times=3)

            # Capturar screenshot
            screenshot_path = "../../research/platform_tests/artstation_playwright.png"
            self.screenshot(screenshot_path)
            print(f"✓ Screenshot guardado")

            # Obtener HTML
            print("→ Extrayendo HTML completo...")
            html = self.get_html()
            soup = self.parse_html(html)

            # Guardar HTML para análisis
            html_path = "../../research/platform_tests/artstation_playwright.html"
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html)
            print(f"✓ HTML guardado en: {html_path}")

            # BUSCAR TRABAJOS
            print("\n→ Buscando trabajos con selectores identificados...")

            job_elements = soup.select('.job-grid-item')

            if not job_elements:
                print("⚠️  No se encontró .job-grid-item, intentando selectores alternativos...")
                job_elements = (
                        soup.select('[class*="job-grid"]') or
                        soup.select('article') or
                        soup.select('[class*="job"]')
                )

            if not job_elements:
                print("❌ No se encontraron trabajos")
                return [{
                    "platform": "ArtStation",
                    "status": "NO_JOBS_FOUND",
                    "message": "Revisar HTML y selectores",
                    "html_file": html_path,
                    "screenshot": screenshot_path,
                    "timestamp": datetime.now().isoformat(),
                }]

            print(f"✅ Encontrados {len(job_elements)} trabajos")

            # EXTRAER DATOS
            print("\n→ Extrayendo información de trabajos...")

            for i, job_elem in enumerate(job_elements):
                try:
                    # Título
                    title_elem = (
                            job_elem.select_one('.job-grid-item-title-holder') or
                            job_elem.select_one('h2') or
                            job_elem.select_one('h3') or
                            job_elem.select_one('[class*="title"]')
                    )

                    # Empresa
                    company_elem = (
                            job_elem.select_one('.job-grid-item-company') or
                            job_elem.select_one('[class*="company"]')
                    )

                    # Info adicional
                    info_elem = job_elem.select_one('.job-grid-item-info')
                    location_info = info_elem.get_text(strip=True) if info_elem else 'N/A'

                    # Link al trabajo
                    link_elem = job_elem.select_one('a[href*="/jobs/"]')

                    # Logo
                    logo_elem = job_elem.select_one('.job-grid-item-logo img')
                    company_logo = logo_elem.get('src', None) if logo_elem else None

                    # Extraer textos
                    title = title_elem.get_text(strip=True) if title_elem else 'N/A'
                    company = company_elem.get_text(strip=True) if company_elem else 'N/A'
                    url = link_elem.get('href', 'N/A') if link_elem else 'N/A'

                    # Construir URL completa
                    if url.startswith('/jobs/'):
                        url = f"https://www.artstation.com{url}"

                    # APLICAR FILTROS
                    is_character = self._is_character_artist(title)
                    is_entry = self._is_entry_level(title, location_info)
                    experience = self._extract_experience_years(location_info)

                    # Construir objeto job
                    job = {
                        'platform': 'ArtStation',
                        'title': title,
                        'company': company,
                        'location_info': location_info,
                        'url': url,
                        'company_logo': company_logo,
                        'experience_required': experience,
                        'scraped_at': datetime.now().isoformat(),
                        'is_character_artist': is_character,
                        'is_entry_level': is_entry,
                        'relevance_score': self._calculate_relevance(is_character, is_entry)
                    }

                    jobs.append(job)

                    # Mostrar con indicadores visuales
                    if is_character:
                        level = "🟢 ENTRY" if is_entry else "🔵 MID/SR"
                        print(f"  [{i+1:2d}] {level} | {title[:50]}")
                        print(f"       └─ {company}")
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
    """Función principal con integración Supabase"""
    print("\n" + "=" * 70)
    print("ARTSTATION SCRAPER - CHARACTER ARTIST ENTRY LEVEL")
    print("=" * 70)
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Objetivo: Encontrar posiciones Character Artist (Entry Level)")
    print(f"Base de datos: {'✓ Supabase ACTIVO' if DB_AVAILABLE else '✗ Desactivada'}")
    print("=" * 70)

    # Ejecutar scraper
    with ArtStationScraper(headless=False) as scraper:
        jobs = scraper.scrape_jobs()

    # CLASIFICAR RESULTADOS
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

    # GUARDAR EN SUPABASE
    if DB_AVAILABLE and jobs:
        print("\n" + "=" * 70)
        print("💾 GUARDANDO EN SUPABASE")
        print("=" * 70)

        db = SessionLocal()
        saved_count = 0
        updated_count = 0
        error_count = 0

        try:
            for job in jobs:
                # Enriquecer con descripción (opcional, comentar si es muy lento)
                # detailed_job = scraper.scrape_job_detail(job)
                detailed_job = job  # Sin detail por ahora

                # Convertir a formato DB
                db_job = ArtStationScraper(headless=True)._to_db_job(detailed_job)

                # Guardar
                if save_job(db, db_job):
                    saved_count += 1
                else:
                    error_count += 1

        except Exception as e:
            print(f"\n❌ Error al guardar en BD: {e}")
        finally:
            db.close()

        print(f"\n✅ Persistencia completada:")
        print(f"   Guardados: {saved_count}")
        print(f"   Errores: {error_count}")

    # GUARDAR JSON
    character_jobs_sorted = sorted(
        character_jobs,
        key=lambda x: x.get('relevance_score', 0),
        reverse=True
    )

    result = {
        'platform': 'ArtStation',
        'scrape_date': datetime.now().isoformat(),
        'filters_applied': {
            'target_role': 'Character Artist',
            'target_level': 'Entry Level (preferred)',
            'keywords_used': [
                'character artist', '3d character', 'character modeler',
                'junior', 'entry level', 'associate'
            ]
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

    result_file = "../../research/platform_tests/artstation_playwright_result.json"
    with open(result_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"\n💾 Resultados guardados en: {result_file}")

    # MOSTRAR TOP RESULTADOS
    if entry_jobs:
        print("\n" + "=" * 70)
        print("🎯 TOP POSICIONES ENTRY LEVEL ENCONTRADAS")
        print("=" * 70)

        for i, job in enumerate(entry_jobs[:5], 1):
            print(f"\n{i}. {job['title']}")
            print(f"   🏢 Empresa: {job['company']}")
            print(f"   📍 Info: {job['location_info']}")
            print(f"   📅 Experiencia: {job['experience_required']}")
            print(f"   🔗 URL: {job['url']}")
            print(f"   ⭐ Relevancia: {job['relevance_score']}/10")

    # Archivos generados
    print("\n" + "=" * 70)
    print("📁 ARCHIVOS GENERADOS")
    print("=" * 70)
    print(f"  1. artstation_playwright.html (HTML completo)")
    print(f"  2. artstation_playwright.png (Screenshot)")
    print(f"  3. artstation_playwright_result.json (Datos estructurados)")
    if DB_AVAILABLE:
        print(f"  4. ✓ Datos guardados en Supabase")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()