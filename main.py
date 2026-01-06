"""
Script principal para ejecutar todos los scrapers
Guarda resultados en Supabase
Autor: Cristian Meza Venegas
"""

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models import (
    SessionLocal,
    init_db,
    save_job,
    start_job_run,
    finish_job_run,
)

from scrapers.artstation import ArtStationScraper
from scrapers.gamejobs import GameJobsScraper
from scrapers.hitmarker import HitmarkerScraper


def run_scraper(
        scraper_class,
        scraper_name: str,
        platform: str,
        headless: bool = True
):
    """
    Ejecuta un scraper específico y guarda resultados en Supabase
    """
    db: Session = SessionLocal()

    job_run = start_job_run(
        db,
        scraper_name=scraper_name,
        platform=platform,
    )

    stats = {
        "platform": platform,
        "jobs_found": 0,
        "jobs_saved": 0,
        "jobs_duplicated": 0,
        "status": "pending",
    }

    scraper = None

    try:
        print("\n" + "=" * 70)
        print(f"🚀 EJECUTANDO {scraper_name}")
        print("=" * 70)

        scraper = scraper_class(headless=headless)
        scraper.start_browser()

        jobs = scraper.scrape_jobs()
        stats["jobs_found"] = len(jobs)

        print(f"💾 Guardando {len(jobs)} trabajos en Supabase...")

        for job in jobs:
            try:
                save_job(db, scraper.to_db_job(job))
                stats["jobs_saved"] += 1
            except IntegrityError:
                db.rollback()
                stats["jobs_duplicated"] += 1
            except Exception as e:
                print(f"⚠️ Error guardando job: {e}")
                db.rollback()

        finish_job_run(
            db,
            job_run,
            status="success",
            jobs_found=stats["jobs_found"],
            jobs_saved=stats["jobs_saved"],
        )

        stats["status"] = "success"

        print(f"✅ {platform} completado")
        print(f"   Encontrados: {stats['jobs_found']}")
        print(f"   Guardados: {stats['jobs_saved']}")
        print(f"   Duplicados: {stats['jobs_duplicated']}")

    except Exception as e:
        print(f"❌ Error en {platform}: {e}")

        import traceback
        traceback.print_exc()

        db.rollback()

        finish_job_run(
            db,
            job_run,
            status="error",
            error_message=str(e),
        )

        stats["status"] = "error"
        stats["error"] = str(e)

    finally:
        if scraper:
            try:
                scraper.close_browser()
            except Exception:
                pass

        db.close()

    return stats


def main():
    """
    Función principal
    """
    print("\n" + "=" * 70)
    print("🎨 JOBSCRAPER - CHARACTER ARTIST")
    print("Plataformas: ArtStation | GameJobs | Hitmarker")
    print("=" * 70)

    print("🔧 Inicializando base de datos...")
    try:
        init_db()
        print("✅ Base de datos lista\n")
    except Exception as e:
        print(f"❌ Error inicializando BD: {e}")
        print("Verifica tu DATABASE_URL en el archivo .env")
        return

    scrapers = [
        (ArtStationScraper, "ArtStationScraper", "ArtStation"),
        (GameJobsScraper, "GameJobsScraper", "GameJobs"),
        (HitmarkerScraper, "HitmarkerScraper", "Hitmarker"),
    ]

    all_stats = []

    for scraper_class, name, platform in scrapers:
        stats = run_scraper(
            scraper_class=scraper_class,
            scraper_name=name,
            platform=platform,
            headless=True,
        )
        all_stats.append(stats)

    print("\n" + "=" * 70)
    print("📊 RESUMEN FINAL")
    print("=" * 70)

    total_found = sum(s["jobs_found"] for s in all_stats)
    total_saved = sum(s["jobs_saved"] for s in all_stats)
    total_duplicated = sum(s["jobs_duplicated"] for s in all_stats)

    for stat in all_stats:
        icon = "✅" if stat["status"] == "success" else "❌"
        print(
            f"{icon} {stat['platform']:12} | "
            f"Encontrados: {stat['jobs_found']:3d} | "
            f"Guardados: {stat['jobs_saved']:3d} | "
            f"Duplicados: {stat['jobs_duplicated']:3d}"
        )

    print("=" * 70)
    print(
        f"TOTALES → Encontrados: {total_found} | "
        f"Guardados: {total_saved} | "
        f"Duplicados: {total_duplicated}"
    )
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
