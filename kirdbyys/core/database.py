"""Database models for Kirdbyys."""
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Text, JSON, ForeignKey, UniqueConstraint, create_engine
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from datetime import datetime
from kirdbyys.config import settings

Base = declarative_base()

class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    sport = Column(String(64), default="soccer")
    source_folder = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    status = Column(String(32), default="idle")  # idle, importing, analyzing, complete, error
    weights = Column(JSON, default=dict)
    target_selection_count = Column(Integer, default=20)
    images = relationship("Image", back_populates="project", lazy="selectin")

class Image(Base):
    __tablename__ = "images"
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    filename = Column(String(512), nullable=False)
    original_path = Column(Text, nullable=False)
    rel_path = Column(Text, nullable=False)
    file_size = Column(Integer)
    width = Column(Integer)
    height = Column(Integer)
    capture_time = Column(DateTime)
    camera_make = Column(String(128))
    camera_model = Column(String(128))
    lens = Column(String(128))
    iso = Column(Integer)
    aperture = Column(String(32))
    shutter_speed = Column(String(32))
    focal_length = Column(String(32))
    
    # Scores
    technical_score = Column(Float, default=0.0)
    action_score = Column(Float, default=0.0)
    storytelling_score = Column(Float, default=0.0)
    composition_score = Column(Float, default=0.0)
    final_score = Column(Float, default=0.0)
    rank = Column(Integer, default=0)
    
    # Analysis
    detected_labels = Column(JSON, default=list)
    moments = Column(JSON, default=list)
    quality_breakdown = Column(JSON, default=dict)
    composition_breakdown = Column(JSON, default=dict)
    action_breakdown = Column(JSON, default=dict)
    explanation = Column(Text)
    selected = Column(Boolean, default=False)
    rejected = Column(Boolean, default=False)
    duplicate_group_id = Column(Integer, ForeignKey("duplicate_groups.id"), nullable=True)
    is_best_in_group = Column(Boolean, default=False)
    
    # Cache
    thumbnail_path = Column(Text)
    preview_path = Column(Text)
    perceptual_hash = Column(String(64))
    feature_vector = Column(Text)  # compressed numpy bytes as base64
    processed = Column(Boolean, default=False)
    processing_error = Column(Text)
    
    project = relationship("Project", back_populates="images")
    duplicate_group = relationship("DuplicateGroup", back_populates="images")

class DuplicateGroup(Base):
    __tablename__ = "duplicate_groups"
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    representative_image_id = Column(Integer, nullable=True)
    similarity_score = Column(Float)
    frame_count = Column(Integer, default=0)
    images = relationship("Image", back_populates="duplicate_group")

class Job(Base):
    __tablename__ = "jobs"
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    job_type = Column(String(32), nullable=False)  # import, analyze, export, duplicate
    status = Column(String(32), default="queued")  # queued, running, complete, error, cancelled
    progress = Column(Float, default=0.0)
    total_items = Column(Integer, default=0)
    processed_items = Column(Integer, default=0)
    message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    error_log = Column(Text)

class ExportPreset(Base):
    __tablename__ = "export_presets"
    id = Column(Integer, primary_key=True)
    name = Column(String(128), nullable=False)
    top_n = Column(Integer, default=20)
    mode = Column(String(32), default="copy")  # copy, move, xmp, csv, xlsx, pdf
    include_rejected = Column(Boolean, default=False)
    include_duplicates = Column(Boolean, default=False)
    destination = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

# Sync engine for model creation and sync tasks
sync_engine = create_engine(settings.SYNC_DATABASE_URL.replace("sqlite+aiosqlite:///", "sqlite:///"), echo=False)
SyncSessionLocal = sessionmaker(bind=sync_engine)

# Async engine for API
async_engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)

async def init_db():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

def init_db_sync():
    Base.metadata.create_all(bind=sync_engine)