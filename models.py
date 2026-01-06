"""
Modelos de base de datos para JobScraper
Autor: Cristian Meza Venegas
"""

from datetime import datetime
import os

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Boolean,
    create_engine,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.exc import IntegrityError
from dotenv import load_dotenv

# =========================================================
# CONFIGURACIÓN BD
# =========================================================

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("❌ DATABASE_URL no está definida")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()

# =========================================================
# DEPENDENCIA FASTAPI - DB SESSION
# =========================================================

def get_db():
    """Dependency para FastAPI"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

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

    # Metadata empresa
    company_size = Column(String)
    company_type = Column(String)

    # Clasificación
    is_character_artist = Column(Boolean, default=False)
    is_entry_level = Column(Boolean, default=False)
    relevance_score = Column(Integer, default=0)

    # Fechas
    posted_date = Column(DateTime)
    scraped_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    __table_args__ = (
        UniqueConstraint(
            "platform",
            "external_id",
            name="uix_platform_external",
        ),
        Index("idx_jobs_platform", "platform"),
        Index("idx_jobs_external_id", "external_id"),
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
    """
    Inicializar tablas.
    ⚠️ En producción usar migraciones (Alembic).
    """
    Base.metadata.create_all(bind=engine)


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
