# Last Edited: 2026-03-12
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.sql import func
import os

BASE_DIR = os.path.dirname(__file__)
DB_PATH = os.path.join(BASE_DIR, "data.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class KolPost(Base):
    __tablename__ = "kol_posts"
    id = Column(Integer, primary_key=True, index=True)
    kol_handle = Column(String(255), index=True)
    kol_name = Column(String(255))
    kol_avatar_url = Column(Text)
    posted_at = Column(DateTime, nullable=True)
    text = Column(Text)
    image_urls = Column(Text)
    likes = Column(Integer, default=0)
    retweets = Column(Integer, default=0)
    replies = Column(Integer, default=0)
    url = Column(Text, unique=True)
    created_at = Column(DateTime, server_default=func.now())


class BrowseLog(Base):
    __tablename__ = "browse_logs"
    id = Column(Integer, primary_key=True, index=True)
    visited_at = Column(DateTime, server_default=func.now())
    url = Column(Text, index=True)
    kol_handle = Column(String(255), index=True)
    kol_post_url = Column(Text)
    session_id = Column(String(255), index=True)


class KnowledgeItem(Base):
    __tablename__ = "knowledge_items"
    id = Column(Integer, primary_key=True, index=True)
    source_type = Column(String(64), index=True)
    source_subtype = Column(String(128), nullable=True)
    title = Column(String(512), nullable=True)
    content_raw = Column(Text, nullable=True)
    content_cleaned = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    author_id = Column(String(255), nullable=True)
    author_name = Column(String(255), nullable=True)
    publish_time = Column(DateTime, nullable=True)
    collected_time = Column(DateTime, server_default=func.now())
    url = Column(Text, nullable=True)
    media_paths = Column(Text, nullable=True)
    tags_primary = Column(String(255), nullable=True)
    tags_secondary = Column(Text, nullable=True)
    topic_ids = Column(Text, nullable=True)
    entity_ids = Column(Text, nullable=True)
    analysis_status = Column(String(64), default="pending")
    analysis_result = Column(Text, nullable=True)
    push_status = Column(String(64), default="pending")
    source_file = Column(String(512), nullable=True)
    extra_json = Column(Text, nullable=True)


class Topic(Base):
    __tablename__ = "topics"
    id = Column(Integer, primary_key=True, index=True)
    topic_name = Column(String(255), index=True)
    topic_type = Column(String(64), index=True)
    description = Column(Text, nullable=True)
    related_item_ids = Column(Text, nullable=True)
    short_term_view = Column(Text, nullable=True)
    mid_term_view = Column(Text, nullable=True)
    long_term_view = Column(Text, nullable=True)
    analysis_result = Column(Text, nullable=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class EntityProfile(Base):
    __tablename__ = "entity_profiles"
    id = Column(Integer, primary_key=True, index=True)
    entity_name = Column(String(255), unique=True, index=True)
    platform = Column(String(64), default="x")
    recent_views = Column(Text, nullable=True)
    reliability_score = Column(Float, default=0.5)
    forecast_score = Column(Float, default=0.5)
    hit_cases = Column(Integer, default=0)
    miss_cases = Column(Integer, default=0)
    profile_summary = Column(Text, nullable=True)


def init_db():
    Base.metadata.create_all(bind=engine)
