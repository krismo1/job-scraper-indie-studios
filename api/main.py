"""
API REST para JobScraper Character Artists
Sistema completo con emails y analytics
Autor: Cristian Meza Venegas
VERSION: Production Ready
"""

from fastapi import FastAPI, Depends, Query, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, EmailStr
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import sys

# Agregar el directorio padre al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import SessionLocal, Job, JobRun
from dotenv import load_dotenv

load_dotenv()

# =============================================================================
# CONFIGURACIÓN
# =============================================================================

app = FastAPI(
    title="JobScraper API",
    description="API para búsqueda de empleos Character Artist",
    version="2.0.0"
)

# CORS - Permitir todos los orígenes en producción
# IMPORTANTE: En producción real, especifica solo tus dominios
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción: ["https://tu-dominio.com"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ruta al directorio frontend
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

# Verificar que el directorio existe
if not os.path.exists(FRONTEND_DIR):
    print(f"⚠️  WARNING: Frontend directory not found at {FRONTEND_DIR}")
    os.makedirs(FRONTEND_DIR, exist_ok=True)
else:
    print(f"✅ Frontend directory found at {FRONTEND_DIR}")

# Montar archivos estáticos
try:
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
except Exception as e:
    print(f"⚠️  Could not mount static files: {e}")

# =============================================================================
# EMAIL CONFIGURATION
# =============================================================================

EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_FROM = os.getenv("EMAIL_FROM", EMAIL_USER)

# Verificar configuración de email
if not EMAIL_USER or not EMAIL_PASSWORD:
    print("⚠️  WARNING: Email not configured. Email features will not work.")
    print("   Set EMAIL_USER and EMAIL_PASSWORD in environment variables.")

# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class JobResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    platform: str
    title: str
    company: str
    location: Optional[str]
    remote_type: Optional[str]
    url: str
    is_character_artist: bool
    is_entry_level: bool
    relevance_score: int
    scraped_at: Optional[str]

class EmailRequest(BaseModel):
    to_email: EmailStr
    job_ids: List[int]
    message: Optional[str] = None

# =============================================================================
# DATABASE DEPENDENCY
# =============================================================================

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# =============================================================================
# EMAIL FUNCTIONS
# =============================================================================

def send_email(to_email: str, subject: str, html_body: str):
    """Enviar email con HTML"""
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

        print(f"✅ Email sent to {to_email}")
        return True

    except Exception as e:
        print(f"❌ Error sending email: {e}")
        return False

def create_job_email_html(jobs: List[Job], custom_message: str = None) -> str:
    """Crear HTML para email de jobs"""

    jobs_html = ""
    for job in jobs:
        level_badge = "🟢 ENTRY" if job.is_entry_level else "🔵 MID/SR"

        jobs_html += f"""
        <div style="background: #1a1a2e; border-left: 4px solid #00d4ff; padding: 20px; margin: 15px 0; border-radius: 8px;">
            <div style="display: flex; justify-content: space-between; align-items: start; flex-wrap: wrap;">
                <div style="flex: 1; min-width: 250px;">
                    <h3 style="color: #00d4ff; margin: 0 0 10px 0; font-size: 20px;">{job.title}</h3>
                    <p style="color: #a0a0a0; margin: 5px 0;">
                        <strong style="color: #fff;">🏢 {job.company}</strong>
                    </p>
                    <p style="color: #a0a0a0; margin: 5px 0;">
                        📍 {job.location or 'Not specified'}
                        {f' • {job.remote_type}' if job.remote_type else ''}
                    </p>
                    <p style="color: #a0a0a0; margin: 5px 0;">
                        🎯 Platform: <strong style="color: #00d4ff;">{job.platform}</strong>
                    </p>
                </div>
                <div style="text-align: right;">
                    <span style="background: {'#00ff88' if job.is_entry_level else '#0088ff'}; 
                                 color: #000; 
                                 padding: 5px 15px; 
                                 border-radius: 20px; 
                                 font-weight: bold; 
                                 font-size: 12px;">
                        {level_badge}
                    </span>
                    <p style="color: #ffd700; margin: 10px 0 0 0; font-size: 14px;">
                        ⭐ Relevance: {job.relevance_score}/10
                    </p>
                </div>
            </div>
            <div style="margin-top: 15px;">
                <a href="{job.url}" 
                   style="display: inline-block; 
                          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                          color: white; 
                          padding: 12px 30px; 
                          text-decoration: none; 
                          border-radius: 25px; 
                          font-weight: bold;
                          box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);">
                    🚀 APPLY NOW
                </a>
            </div>
        </div>
        """

    custom_msg_html = ""
    if custom_message:
        custom_msg_html = f"""
        <div style="background: #16213e; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #ffd700;">
            <p style="color: #ffd700; margin: 0; font-style: italic;">💬 Personal Message:</p>
            <p style="color: #fff; margin: 10px 0 0 0;">{custom_message}</p>
        </div>
        """

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="margin: 0; padding: 0; background: #0f0f1e; font-family: 'Segoe UI', Arial, sans-serif;">
        <div style="max-width: 800px; margin: 0 auto; padding: 40px 20px;">
            <div style="text-align: center; margin-bottom: 40px;">
                <h1 style="color: #00d4ff; font-size: 42px; margin: 0; text-shadow: 0 0 20px rgba(0, 212, 255, 0.5);">
                    🎨 JobScraper
                </h1>
                <p style="color: #a0a0a0; font-size: 18px; margin: 10px 0 0 0;">
                    Your Character Artist Opportunities
                </p>
                <div style="height: 3px; background: linear-gradient(90deg, transparent, #00d4ff, transparent); margin: 20px auto; width: 200px;"></div>
            </div>
            
            {custom_msg_html}
            
            <div style="margin: 30px 0;">
                <h2 style="color: #fff; border-bottom: 2px solid #00d4ff; padding-bottom: 10px;">
                    🎯 Selected Opportunities ({len(jobs)})
                </h2>
                {jobs_html}
            </div>
            
            <div style="text-align: center; margin-top: 50px; padding-top: 30px; border-top: 1px solid #333;">
                <p style="color: #666; font-size: 14px;">
                    Powered by <strong style="color: #00d4ff;">JobScraper</strong> • Character Artist Job Aggregator
                </p>
                <p style="color: #666; font-size: 12px; margin: 10px 0 0 0;">
                    {datetime.now().strftime('%B %d, %Y')}
                </p>
            </div>
        </div>
    </body>
    </html>
    """

# =============================================================================
# ENDPOINTS
# =============================================================================

@app.get("/", response_class=HTMLResponse)
async def root():
    """Servir frontend"""
    index_path = os.path.join(FRONTEND_DIR, "index.html")

    if os.path.exists(index_path):
        return FileResponse(index_path)
    else:
        return HTMLResponse(content="""
        <html>
            <body style="background: #0f0f1e; color: white; font-family: Arial; padding: 50px; text-align: center;">
                <h1>⚠️ Frontend not found</h1>
                <p>Please ensure frontend/index.html exists</p>
                <p>API is running at: <a href="/docs" style="color: #00d4ff;">/docs</a></p>
            </body>
        </html>
        """)

@app.get("/api/health")
def health_check(db: Session = Depends(get_db)):
    """Health check con verificación de BD"""
    try:
        job_count = db.query(Job).count()
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "2.0.0",
            "database": "connected",
            "jobs_in_db": job_count,
            "email_configured": bool(EMAIL_USER and EMAIL_PASSWORD)
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }

@app.get("/api/jobs")
def get_jobs(
        limit: int = Query(50, ge=1, le=100),
        offset: int = Query(0, ge=0),
        platform: Optional[str] = None,
        character_only: bool = False,
        entry_only: bool = False,
        min_relevance: Optional[int] = Query(None, ge=0, le=10),
        db: Session = Depends(get_db)
):
    """Obtener lista de jobs con filtros"""
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

        query = query.order_by(Job.relevance_score.desc(), Job.updated_at.desc())

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
        print(f"Error in get_jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/jobs/{job_id}")
def get_job_detail(job_id: int, db: Session = Depends(get_db)):
    """Obtener detalle de un job"""
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
        "is_character_artist": job.is_character_artist,
        "is_entry_level": job.is_entry_level,
        "relevance_score": job.relevance_score,
        "posted_date": job.posted_date.isoformat() if job.posted_date else None,
        "scraped_at": job.scraped_at.isoformat() if job.scraped_at else None,
        "updated_at": job.updated_at.isoformat() if job.updated_at else None,
    }

@app.get("/api/stats")
def get_stats(db: Session = Depends(get_db)):
    """Estadísticas generales"""
    try:
        total = db.query(Job).count()
        character = db.query(Job).filter(Job.is_character_artist == True).count()
        entry = db.query(Job).filter(Job.is_entry_level == True).count()

        platforms = db.query(
            Job.platform,
            db.func.count(Job.id)
        ).group_by(Job.platform).all()

        return {
            "total_jobs": total,
            "character_artists": character,
            "entry_level": entry,
            "by_platform": {p: c for p, c in platforms},
            "updated_at": datetime.now().isoformat()
        }
    except Exception as e:
        print(f"Error in get_stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/platforms")
def get_platforms(db: Session = Depends(get_db)):
    """Obtener plataformas disponibles"""
    platforms = db.query(Job.platform).distinct().all()
    return {
        "platforms": [p[0] for p in platforms]
    }

@app.post("/api/email/send")
async def send_jobs_email(
        request: EmailRequest,
        background_tasks: BackgroundTasks,
        db: Session = Depends(get_db)
):
    """Enviar jobs seleccionados por email"""

    if not EMAIL_USER or not EMAIL_PASSWORD:
        raise HTTPException(
            status_code=503,
            detail="Email service not configured on server"
        )

    if not request.job_ids:
        raise HTTPException(status_code=400, detail="No jobs selected")

    jobs = db.query(Job).filter(Job.id.in_(request.job_ids)).all()

    if not jobs:
        raise HTTPException(status_code=404, detail="No jobs found")

    html_body = create_job_email_html(jobs, request.message)
    subject = f"🎨 {len(jobs)} Character Artist Opportunities for You"

    # Enviar en background
    background_tasks.add_task(send_email, request.to_email, subject, html_body)

    return {
        "success": True,
        "message": f"Email will be sent to {request.to_email}",
        "jobs_count": len(jobs)
    }

@app.get("/api/jobs/top")
def get_top_jobs(
        limit: int = Query(20, ge=1, le=50),
        entry_only: bool = False,
        db: Session = Depends(get_db)
):
    """Top jobs por relevancia"""
    query = db.query(Job).filter(Job.is_character_artist == True)

    if entry_only:
        query = query.filter(Job.is_entry_level == True)

    jobs = query.order_by(Job.relevance_score.desc()).limit(limit).all()

    return {
        "total": len(jobs),
        "results": [
            {
                "id": job.id,
                "platform": job.platform,
                "title": job.title,
                "company": job.company,
                "location": job.location,
                "url": job.url,
                "is_entry_level": job.is_entry_level,
                "relevance_score": job.relevance_score,
            }
            for job in jobs
        ]
    }

# =============================================================================
# STARTUP
# =============================================================================

@app.on_event("startup")
async def startup_event():
    """Ejecutar al iniciar la aplicación"""
    print("=" * 70)
    print("🎮 JOBSCRAPER API STARTING")
    print("=" * 70)
    print(f"📂 Frontend directory: {FRONTEND_DIR}")
    print(f"📧 Email configured: {bool(EMAIL_USER and EMAIL_PASSWORD)}")
    print("=" * 70)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port, reload=False)