"""
FastAPI Application - JobScraper PRODUCTION
Autor: Cristian Meza Venegas
"""

import os
import sys
from fastapi import FastAPI, Depends, Query, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel, EmailStr
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Agregar directorio padre al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import get_db, Job, JobRun

# =============================================================================
# CONFIGURACIÓN
# =============================================================================

app = FastAPI(
    title="JobScraper API",
    description="API para Character Artist Jobs",
    version="1.0.0"
)

# CORS - Permitir todos los orígenes
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configurar frontend
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

# Montar frontend si existe
if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
    print(f"✅ Frontend mounted at {FRONTEND_DIR}")
else:
    print(f"⚠️  Frontend directory not found: {FRONTEND_DIR}")

# Email config
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_FROM = os.getenv("EMAIL_FROM", EMAIL_USER)

# =============================================================================
# MODELS
# =============================================================================

class EmailRequest(BaseModel):
    to_email: EmailStr
    job_ids: List[int]
    message: Optional[str] = None

# =============================================================================
# HEALTH CHECK
# =============================================================================

@app.get("/")
async def root():
    """Servir frontend o health check"""
    index_path = os.path.join(FRONTEND_DIR, "index.html")

    if os.path.exists(index_path):
        return FileResponse(index_path)

    return {
        "status": "ok",
        "service": "JobScraper API",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "docs": "/docs"
    }

@app.get("/api/health")
def health_check(db: Session = Depends(get_db)):
    """Health check with DB test"""
    try:
        job_count = db.query(Job).count()
        return {
            "status": "healthy",
            "database": "connected",
            "jobs_in_db": job_count,
            "email_configured": bool(EMAIL_USER and EMAIL_PASSWORD),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

# =============================================================================
# JOBS ENDPOINTS
# =============================================================================

@app.get("/api/jobs")
def get_jobs(
        platform: Optional[str] = None,
        character_only: bool = False,
        entry_only: bool = False,
        min_relevance: Optional[int] = Query(None, ge=0, le=10),
        limit: int = Query(50, ge=1, le=100),
        offset: int = Query(0, ge=0),
        db: Session = Depends(get_db)
):
    """Get jobs with filters"""
    try:
        query = db.query(Job)

        if platform:
            query = query.filter(Job.platform == platform)
        if character_only:
            query = query.filter(Job.is_character_artist == True)
        if entry_only:
            query = query.filter(Job.is_entry_level == True)
        if min_relevance is not None:
            query = query.filter(Job.relevance_score >= min_relevance)

        query = query.order_by(Job.relevance_score.desc(), Job.scraped_at.desc())

        total = query.count()
        jobs = query.offset(offset).limit(limit).all()

        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "results": [
                {
                    "id": job.id,
                    "platform": job.platform,
                    "title": job.title,
                    "company": job.company,
                    "location": job.location,
                    "remote_type": job.remote_type,
                    "url": job.url,
                    "is_character_artist": job.is_character_artist,
                    "is_entry_level": job.is_entry_level,
                    "relevance_score": job.relevance_score,
                    "scraped_at": job.scraped_at.isoformat() if job.scraped_at else None,
                }
                for job in jobs
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/jobs/{job_id}")
def get_job_detail(job_id: int, db: Session = Depends(get_db)):
    """Get job details"""
    job = db.query(Job).filter(Job.id == job_id).first()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return {
        "id": job.id,
        "platform": job.platform,
        "title": job.title,
        "company": job.company,
        "location": job.location,
        "remote_type": job.remote_type,
        "url": job.url,
        "description": job.description,
        "is_character_artist": job.is_character_artist,
        "is_entry_level": job.is_entry_level,
        "relevance_score": job.relevance_score,
        "scraped_at": job.scraped_at.isoformat() if job.scraped_at else None,
    }

@app.get("/api/stats")
def get_stats(db: Session = Depends(get_db)):
    """Get statistics"""
    try:
        from sqlalchemy import func

        total = db.query(func.count(Job.id)).scalar() or 0
        character = db.query(func.count(Job.id)).filter(Job.is_character_artist == True).scalar() or 0
        entry = db.query(func.count(Job.id)).filter(Job.is_entry_level == True).scalar() or 0

        platforms = db.query(
            Job.platform,
            func.count(Job.id)
        ).group_by(Job.platform).all()

        return {
            "total_jobs": total,
            "character_artists": character,
            "entry_level": entry,
            "by_platform": {p: c for p, c in platforms},
            "updated_at": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/platforms")
def get_platforms(db: Session = Depends(get_db)):
    """Get available platforms"""
    try:
        from sqlalchemy import func
        platforms = db.query(Job.platform).distinct().all()
        return {
            "platforms": [p[0] for p in platforms]
        }
    except:
        return {"platforms": ["ArtStation", "GameJobs", "Hitmarker"]}

# =============================================================================
# EMAIL ENDPOINT
# =============================================================================

def send_email(to_email: str, subject: str, html_body: str):
    """Send email"""
    try:
        if not EMAIL_USER or not EMAIL_PASSWORD:
            print("❌ Email not configured")
            return False

        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = EMAIL_FROM
        msg['To'] = to_email

        html_part = MIMEText(html_body, 'html')
        msg.attach(html_part)

        with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT, timeout=10) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            server.send_message(msg)

        return True
    except Exception as e:
        print(f"❌ Email error: {e}")
        return False

def create_job_email_html(jobs: List[Job], custom_message: str = None) -> str:
    """Create email HTML"""
    jobs_html = ""
    for job in jobs:
        level = "🟢 ENTRY" if job.is_entry_level else "🔵 MID/SR"
        jobs_html += f"""
        <div style="background: #1a1a2e; border-left: 4px solid #00d4ff; padding: 20px; margin: 15px 0; border-radius: 8px;">
            <h3 style="color: #00d4ff;">{job.title}</h3>
            <p style="color: #fff;"><strong>🏢 {job.company}</strong></p>
            <p style="color: #a0a0a0;">📍 {job.location or 'Not specified'}</p>
            <p style="color: #a0a0a0;">⭐ Relevance: {job.relevance_score}/10</p>
            <span style="background: #00ff88; color: #000; padding: 5px 10px; border-radius: 10px;">{level}</span>
            <div style="margin-top: 15px;">
                <a href="{job.url}" style="background: linear-gradient(135deg, #667eea, #764ba2); color: white; padding: 10px 20px; text-decoration: none; border-radius: 20px;">🚀 APPLY NOW</a>
            </div>
        </div>
        """

    custom_msg_html = ""
    if custom_message:
        custom_msg_html = f'<div style="background: #16213e; padding: 20px; border-radius: 8px; margin: 20px 0;"><p style="color: #ffd700;">💬 {custom_message}</p></div>'

    return f"""
    <html>
    <body style="background: #0f0f1e; font-family: Arial; padding: 20px;">
        <div style="max-width: 800px; margin: 0 auto;">
            <h1 style="color: #00d4ff;">🎨 JobScraper</h1>
            {custom_msg_html}
            <h2 style="color: #fff;">🎯 Selected Jobs ({len(jobs)})</h2>
            {jobs_html}
            <p style="color: #666; margin-top: 30px;">Powered by JobScraper • {datetime.now().strftime('%B %d, %Y')}</p>
        </div>
    </body>
    </html>
    """

@app.post("/api/email/send")
async def send_jobs_email(
        request: EmailRequest,
        background_tasks: BackgroundTasks,
        db: Session = Depends(get_db)
):
    """Send jobs via email"""
    if not EMAIL_USER or not EMAIL_PASSWORD:
        raise HTTPException(
            status_code=503,
            detail="Email service not configured"
        )

    if not request.job_ids:
        raise HTTPException(status_code=400, detail="No jobs selected")

    jobs = db.query(Job).filter(Job.id.in_(request.job_ids)).all()

    if not jobs:
        raise HTTPException(status_code=404, detail="No jobs found")

    html_body = create_job_email_html(jobs, request.message)
    subject = f"🎨 {len(jobs)} Character Artist Jobs for You"

    background_tasks.add_task(send_email, request.to_email, subject, html_body)

    return {
        "success": True,
        "message": f"Email will be sent to {request.to_email}",
        "jobs_count": len(jobs)
    }

# =============================================================================
# STARTUP
# =============================================================================

@app.on_event("startup")
async def startup_event():
    """Startup tasks"""
    print("=" * 70)
    print("🎮 JOBSCRAPER API STARTING")
    print("=" * 70)
    print(f"📂 Frontend: {FRONTEND_DIR}")
    print(f"📧 Email: {'✅ Configured' if EMAIL_USER else '❌ Not configured'}")
    print("=" * 70)