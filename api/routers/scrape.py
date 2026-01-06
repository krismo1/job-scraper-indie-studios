from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError

from models import get_db, start_job_run, finish_job_run, save_job
from scrapers.artstation import ArtStationScraper
from scrapers.gamejobs import GameJobsScraper
from scrapers.hitmarker import HitmarkerScraper

router = APIRouter(prefix="/api/scrape", tags=["Scraping"])


# ==========================
# SCHEMAS
# ==========================
class ScrapeRequest(BaseModel):
    platforms: List[str] = ["ArtStation", "GameJobs", "Hitmarker"]
    headless: bool = True


class ScrapeResponse(BaseModel):
    status: str
    message: str
    results: List[dict]


# ==========================
# CORE SCRAPER
# ==========================
def run_single_scraper(
        scraper_class,
        scraper_name: str,
        platform: str,
        headless: bool,
        db: Session
):
    job_run = start_job_run(db, scraper_name=scraper_name, platform=platform)

    stats = {
        "platform": platform,
        "jobs_found": 0,
        "jobs_saved": 0,
        "jobs_duplicated": 0,
        "status": "pending",
        "error": None,
    }

    scraper = None

    try:
        scraper = scraper_class(headless=headless)
        scraper.start_browser()

        jobs = scraper.scrape_jobs()
        stats["jobs_found"] = len(jobs)

        for job in jobs:
            try:
                save_job(db, scraper.to_db_job(job))
                stats["jobs_saved"] += 1
            except IntegrityError:
                db.rollback()
                stats["jobs_duplicated"] += 1
            except Exception as e:
                db.rollback()
                print(f"⚠️ Error guardando job: {e}")

        finish_job_run(
            db,
            job_run,
            status="success",
            jobs_found=stats["jobs_found"],
            jobs_saved=stats["jobs_saved"],
        )

        stats["status"] = "success"

    except Exception as e:
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


# ==========================
# ENDPOINTS
# ==========================
@router.post("/run", response_model=ScrapeResponse)
def run_scrapers(
        request: ScrapeRequest,
        db: Session = Depends(get_db),
):
    scrapers_map = {
        "ArtStation": (ArtStationScraper, "ArtStationScraper"),
        "GameJobs": (GameJobsScraper, "GameJobsScraper"),
        "Hitmarker": (HitmarkerScraper, "HitmarkerScraper"),
    }

    invalid = [p for p in request.platforms if p not in scrapers_map]
    if invalid:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid platforms: {invalid}"
        )

    all_stats = []

    for platform in request.platforms:
        scraper_class, scraper_name = scrapers_map[platform]

        stats = run_single_scraper(
            scraper_class,
            scraper_name,
            platform,
            request.headless,
            db
        )
        all_stats.append(stats)

    total_found = sum(s["jobs_found"] for s in all_stats)
    total_saved = sum(s["jobs_saved"] for s in all_stats)
    total_duplicated = sum(s["jobs_duplicated"] for s in all_stats)

    return {
        "status": "success",
        "message": (
            f"Scraping completado: "
            f"{total_found} encontrados, "
            f"{total_saved} guardados, "
            f"{total_duplicated} duplicados"
        ),
        "results": all_stats,
    }


@router.get("/platforms")
def get_platforms():
    return {
        "platforms": ["ArtStation", "GameJobs", "Hitmarker"]
    }
