# =============================================================================
# SCRAPING ENDPOINTS - Agregar después de los otros endpoints
# =============================================================================

from scrapers.artstation import ArtStationScraper
from scrapers.gamejobs import GameJobsScraper
from scrapers.hitmarker import HitmarkerScraper
from models import start_job_run, finish_job_run, save_job
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel
from fastapi import FastAPI
from api.routers.scrape import router as scrape_router
from typing import List


app = FastAPI()

app.include_router(scrape_router)




class ScrapeRequest(BaseModel):
    """Request para ejecutar scrapers"""
    platforms: List[str] = ["ArtStation", "GameJobs", "Hitmarker"]
    headless: bool = True

class ScrapeResponse(BaseModel):
    """Response del scraping"""
    status: str
    message: str
    results: List[dict]

def run_single_scraper(scraper_class, scraper_name: str, platform: str, headless: bool, db: Session):
    """Ejecutar un scraper específico"""

    job_run = start_job_run(db, scraper_name=scraper_name, platform=platform)

    stats = {
        "platform": platform,
        "jobs_found": 0,
        "jobs_saved": 0,
        "jobs_duplicated": 0,
        "status": "pending",
        "error": None
    }

    scraper = None

    try:
        print(f"\n{'='*70}")
        print(f"🚀 EJECUTANDO {scraper_name}")
        print(f"{'='*70}")

        scraper = scraper_class(headless=headless)
        scraper.start_browser()

        jobs = scraper.scrape_jobs()
        stats["jobs_found"] = len(jobs)

        print(f"💾 Guardando {len(jobs)} trabajos en base de datos...")

        for job in jobs:
            try:
                save_job(db, scraper.to_db_job(job))
                stats["jobs_saved"] += 1
            except IntegrityError:
                db.rollback()
                stats["jobs_duplicated"] += 1
            except Exception as e:
                print(f"  ⚠️  Error guardando job: {e}")
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
            except:
                pass

    return stats

@app.post("/api/scrape/run", response_model=ScrapeResponse)
async def run_scrapers(
        request: ScrapeRequest,
        background_tasks: BackgroundTasks,
        db: Session = Depends(get_db)
):
    """
    Ejecutar scrapers seleccionados
    
    Plataformas disponibles:
    - ArtStation
    - GameJobs
    - Hitmarker
    """

    scrapers_map = {
        "ArtStation": (ArtStationScraper, "ArtStationScraper"),
        "GameJobs": (GameJobsScraper, "GameJobsScraper"),
        "Hitmarker": (HitmarkerScraper, "HitmarkerScraper"),
    }

    # Validar plataformas
    invalid_platforms = [p for p in request.platforms if p not in scrapers_map]
    if invalid_platforms:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid platforms: {invalid_platforms}. Valid: {list(scrapers_map.keys())}"
        )

    all_stats = []

    try:
        for platform in request.platforms:
            scraper_class, scraper_name = scrapers_map[platform]

            stats = run_single_scraper(
                scraper_class=scraper_class,
                scraper_name=scraper_name,
                platform=platform,
                headless=request.headless,
                db=db
            )

            all_stats.append(stats)

        # Calcular totales
        total_found = sum(s["jobs_found"] for s in all_stats)
        total_saved = sum(s["jobs_saved"] for s in all_stats)
        total_duplicated = sum(s["jobs_duplicated"] for s in all_stats)

        success_count = sum(1 for s in all_stats if s["status"] == "success")

        return {
            "status": "success" if success_count == len(request.platforms) else "partial",
            "message": f"Scraping completado: {total_found} encontrados, {total_saved} guardados, {total_duplicated} duplicados",
            "results": all_stats
        }

    except Exception as e:
        print(f"❌ Error general en scraping: {e}")
        import traceback
        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=f"Error ejecutando scrapers: {str(e)}"
        )

@app.get("/api/scrape/status")
async def get_scrape_status(db: Session = Depends(get_db)):
    """Obtener estado de los últimos scrapes"""
    try:
        from models import JobRun

        recent_runs = db.query(JobRun).order_by(JobRun.started_at.desc()).limit(10).all()

        return {
            "recent_runs": [
                {
                    "id": run.id,
                    "platform": run.platform,
                    "scraper_name": run.scraper_name,
                    "status": run.status,
                    "jobs_found": run.jobs_found,
                    "jobs_saved": run.jobs_saved,
                    "started_at": run.started_at.isoformat() if run.started_at else None,
                    "finished_at": run.finished_at.isoformat() if run.finished_at else None,
                    "error_message": run.error_message
                }
                for run in recent_runs
            ]
        }
    except Exception as e:
        print(f"Error getting scrape status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/scrape/platforms")
async def get_available_platforms():
    """Obtener plataformas disponibles para scraping"""
    return {
        "platforms": [
            {
                "name": "ArtStation",
                "description": "ArtStation Jobs - Character Artist positions"
            },
            {
                "name": "GameJobs",
                "description": "GameJobs.co - Game industry jobs"
            },
            {
                "name": "Hitmarker",
                "description": "Hitmarker.net - Gaming and esports jobs"
            }
        ]
    }