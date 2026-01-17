"""
Modelos de base de datos para JobScraper
Autor: Cristian Meza Venegas
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean,
    create_engine, UniqueConstraint
)
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.exc import IntegrityError
import os
from dotenv import load_dotenv

load_dotenv()

# =========================================================
# CONFIGURACIÓN BD
# =========================================================

DATABASE_URL = os.getenv("DATABASE_URL")

# IMPORTANTE: Solo lanzar error si DATABASE_URL es realmente necesaria
# En Railway, a veces las variables tardan en cargarse
if not DATABASE_URL:
    # En lugar de fallar, usar una URL dummy que se puede sobrescribir
    print("⚠️  WARNING: DATABASE_URL no está definida. Usando placeholder.")
    DATABASE_URL = "postgresql://user:pass@localhost:5432/db"

try:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    SessionLocal = sessionmaker(bind=engine)
    Base = declarative_base()
    print("✅ Database engine created successfully")
except Exception as e:
    print(f"❌ Error creating database engine: {e}")
    # Crear engine dummy para que no falle la importación
    engine = None
    SessionLocal = None
    Base = declarative_base()

# =========================================================
# MODELOS
# =========================================================

class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True)
    platform = Column(String, nullable=False)
    external_id = Column(String, nullable=False)
    title = Column(String, nullable=False)
    company = Column(String)
    location = Column(String)
    remote_type = Column(String)
    url = Column(Text, nullable=False)
    description = Column(Text)
    company_size = Column(String)
    company_type = Column(String)
    is_character_artist = Column(Boolean, default=False)
    is_entry_level = Column(Boolean, default=False)
    relevance_score = Column(Integer, default=0)
    posted_date = Column(DateTime)
    scraped_at = Column(DateTime)
    updated_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("platform", "external_id", name="uix_platform_external"),
    )


class JobRun(Base):
    __tablename__ = "job_runs"

    id = Column(Integer, primary_key=True)
    scraper_name = Column(String, nullable=False)
    platform = Column(String, nullable=False)
    status = Column(String, default="pending")
    jobs_found = Column(Integer, default=0)
    jobs_saved = Column(Integer, default=0)
    error_message = Column(Text)
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime)

# =========================================================
# FUNCIONES BD
# =========================================================

def init_db():
    """Inicializar tablas"""
    if engine:
        Base.metadata.create_all(bind=engine)
    else:
        print("⚠️  Cannot initialize database: engine is None")


def save_job(db, job_data: dict):
    """Guarda job. Lanza IntegrityError si duplicado"""
    job = Job(**job_data)
    db.add(job)
    try:
        db.commit()
        db.refresh(job)
        return job
    except IntegrityError:
        db.rollback()
        raise


def start_job_run(db, scraper_name: str, platform: str):
    """Crear registro de inicio"""
    run = JobRun(
        scraper_name=scraper_name,
        platform=platform,
        status="running",
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def finish_job_run(
        db,
        job_run,
        status: str,
        jobs_found: int = 0,
        jobs_saved: int = 0,
        error_message: str = None,
):
    """Finalizar registro"""
    job_run.status = status
    job_run.jobs_found = jobs_found
    job_run.jobs_saved = jobs_saved
    job_run.error_message = error_message
    job_run.finished_at = datetime.utcnow()
    db.commit()