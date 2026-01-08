"""
FastAPI Application - JobScraper
API para consultar trabajos scrapeados
NO ejecuta scrapers (solo consulta BD)
"""

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from models import get_db, Job, JobRun

# =============================================================================
# APP INITIALIZATION
# =============================================================================

app = FastAPI(
    title="JobScraper API",
    description="API para consultar trabajos de Character Artist",
    version="1.0.0"
)

# =============================================================================
# HEALTH CHECK
# =============================================================================

@app.get("/")
def root():
    """Health check endpoint"""
    return {
        "status": "ok",
        "service": "JobScraper API",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    """Detailed health check with DB connection"""
    try:
        # Test DB connection
        db.execute("SELECT 1")
        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Database connection failed: {str(e)}"
        )

# =============================================================================
# JOBS ENDPOINTS
# =============================================================================

@app.get("/api/jobs")
def get_jobs(
        platform: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        db: Session = Depends(get_db)
):
    """
    Obtener lista de trabajos

    - **platform**: Filtrar por plataforma (ArtStation, GameJobs, Hitmarker)
    - **limit**: Número máximo de resultados (default: 100)
    - **offset**: Saltar N resultados (paginación)
    """
    try:
        query = db.query(Job).order_by(Job.scraped_at.desc())

        if platform:
            query = query.filter(Job.platform == platform)

        total = query.count()
        jobs = query.limit(limit).offset(offset).all()

        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "jobs": [
                {
                    "id": job.id,
                    "title": job.title,
                    "company": job.company,
                    "location": job.location,
                    "remote_type": job.remote_type,
                    "platform": job.platform,
                    "url": job.url,
                    "posted_date": job.posted_date.isoformat() if job.posted_date else None,
                    "scraped_at": job.scraped_at.isoformat() if job.scraped_at else None,
                }
                for job in jobs
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/jobs/{job_id}")
def get_job_detail(job_id: int, db: Session = Depends(get_db)):
    """Obtener detalle completo de un trabajo"""
    try:
        job = db.query(Job).filter(Job.id == job_id).first()

        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        return {
            "id": job.id,
            "platform": job.platform,
            "external_id": job.external_id,
            "title": job.title,
            "company": job.company,
            "location": job.location,
            "remote_type": job.remote_type,
            "url": job.url,
            "description": job.description,
            "company_size": job.company_size,
            "company_type": job.company_type,
            "posted_date": job.posted_date.isoformat() if job.posted_date else None,
            "scraped_at": job.scraped_at.isoformat() if job.scraped_at else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# =============================================================================
# STATS ENDPOINTS
# =============================================================================

@app.get("/api/stats")
def get_stats(db: Session = Depends(get_db)):
    """Obtener estadísticas generales"""
    try:
        from sqlalchemy import func

        total_jobs = db.query(func.count(Job.id)).scalar()

        by_platform = db.query(
            Job.platform,
            func.count(Job.id)
        ).group_by(Job.platform).all()

        recent_scrapes = db.query(JobRun).order_by(
            JobRun.started_at.desc()
        ).limit(5).all()

        return {
            "total_jobs": total_jobs,
            "by_platform": {
                platform: count for platform, count in by_platform
            },
            "recent_scrapes": [
                {
                    "platform": run.platform,
                    "status": run.status,
                    "jobs_found": run.jobs_found,
                    "jobs_saved": run.jobs_saved,
                    "started_at": run.started_at.isoformat() if run.started_at else None,
                }
                for run in recent_scrapes
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# =============================================================================
# PLATFORMS ENDPOINT
# =============================================================================

@app.get("/api/platforms")
def get_platforms():
    """Obtener lista de plataformas disponibles"""
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