"""
Database models for Smart Assistant application.

Provides SQLAlchemy ORM models for:
- Job opportunities and application tracking
- User career profiles and preferences  
- Airtable integration configuration
- Intelligence briefing cache and history
"""
from typing import Optional, Dict, Any, List
from sqlalchemy import Column, String, Text, Integer, Boolean, JSON, DateTime, Float, ForeignKey, Table
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()

# Mixin for timestamp columns
class TimestampMixin:
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False)

# User model with career profile relationship
class User(Base, TimestampMixin):
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    full_name = Column(String, nullable=True)
    role = Column(String, default="user")
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    career_profile = relationship("CareerProfile", back_populates="user", uselist=False)
    job_search_config = relationship("JobSearchConfig", back_populates="user", uselist=False)

# Career profile for users
class CareerProfile(Base, TimestampMixin):
    __tablename__ = "career_profiles"
    
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"))
    
    # Career details
    job_title = Column(String, nullable=True)
    skills = Column(JSON, nullable=True)  # JSON array of skills
    experience_years = Column(Float, nullable=True)
    education = Column(JSON, nullable=True)  # JSON object with education details
    preferred_locations = Column(JSON, nullable=True)  # JSON array of locations
    resume_text = Column(Text, nullable=True)  # Full text of latest resume
    
    # Relationship
    user = relationship("User", back_populates="career_profile")

# Job search configuration
class JobSearchConfig(Base, TimestampMixin):
    __tablename__ = "job_search_configs"
    
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"))
    
    # Search preferences
    preferred_job_types = Column(JSON, nullable=True)  # Full-time, contract, etc.
    min_salary = Column(Integer, nullable=True)
    max_commute_distance = Column(Integer, nullable=True)  # in miles/km
    industries = Column(JSON, nullable=True)  # Preferred industries
    exclude_keywords = Column(JSON, nullable=True)  # Keywords to avoid
    
    # Integration settings
    airtable_api_key = Column(String, nullable=True)
    airtable_base_id = Column(String, nullable=True)
    airtable_table_name = Column(String, nullable=True)
    
    # Relationship
    user = relationship("User", back_populates="job_search_config")

# Job opportunities discovered by the system
class JobOpportunity(Base, TimestampMixin):
    __tablename__ = "job_opportunities"
    
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    
    # Job details
    title = Column(String, nullable=False)
    company = Column(String, nullable=False)
    location = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    url = Column(String, nullable=True)
    salary_range = Column(String, nullable=True)
    employment_type = Column(String, nullable=True)  # Full-time, part-time, contract
    source = Column(String, nullable=True)  # LinkedIn, Indeed, etc.
    
    # AI analysis
    relevance_score = Column(Float, default=0.0)  # 0.0 to 1.0 match score
    ai_insights = Column(JSON, nullable=True)  # JSON with AI analysis
    
    # Application tracking
    status = Column(String, default="discovered")  # discovered, saved, applied, interviewing, etc.
    date_applied = Column(DateTime(timezone=True), nullable=True)
    airtable_record_id = Column(String, nullable=True)  # ID in Airtable if synced
    
    # Relationship
    user = relationship("User")

# Email processing history
class EmailProcessingHistory(Base, TimestampMixin):
    __tablename__ = "email_processing_history"
    
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"))
    
    # Processing details
    email_count = Column(Integer, default=0)
    important_count = Column(Integer, default=0)
    processed_at = Column(DateTime(timezone=True), default=func.now())
    summary = Column(Text, nullable=True)
    
    # Relationship
    user = relationship("User")

# Intelligence briefing history
class IntelligenceBriefing(Base, TimestampMixin):
    __tablename__ = "intelligence_briefings"
    
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"))
    
    # Briefing content
    title = Column(String, nullable=False)
    date = Column(DateTime(timezone=True), default=func.now())
    content = Column(JSON, nullable=False)  # Structured briefing content
    read_status = Column(Boolean, default=False)
    
    # Relationship
    user = relationship("User")


# Simple model to track processed job URLs to avoid duplicates
class ProcessedJobUrl(Base, TimestampMixin):
    __tablename__ = "processed_job_urls"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    url = Column(String, unique=True, index=True, nullable=False)  # Job URL
    job_title = Column(String, nullable=True)  # Optional: store job title for reference
    company = Column(String, nullable=True)    # Optional: store company for reference
    
    def __repr__(self):
        return f"<ProcessedJobUrl(url='{self.url}', title='{self.job_title}')>"

# --- GraphRAG models (SQLite fallback) ---
class GraphNode(Base, TimestampMixin):
    __tablename__ = "graphrag_nodes"

    id = Column(String, primary_key=True, index=True)
    label = Column(String, index=True)  # e.g., Person, Organization, Concept
    name = Column(String, index=True)   # human-readable name
    # Use MutableDict wrapper so in-place mutation (e.g., adding layout coordinates) is detected
    properties = Column(MutableDict.as_mutable(JSON), nullable=True)  # arbitrary properties
    source_ids = Column(JSON, nullable=True)  # list of source document IDs
    embedding = Column(JSON, nullable=True)   # optional: store local embedding vector
    # Phase 3: explicit namespace column (denormalized copy for fast filtering)
    namespace = Column(String, index=True, nullable=True)

class GraphEdge(Base, TimestampMixin):
    __tablename__ = "graphrag_edges"

    id = Column(String, primary_key=True, index=True)
    source_id = Column(String, ForeignKey("graphrag_nodes.id"), index=True)
    target_id = Column(String, ForeignKey("graphrag_nodes.id"), index=True)
    relation = Column(String, index=True)  # e.g., WORKS_AT, RELATED_TO
    confidence = Column(Float, default=0.5)
    properties = Column(MutableDict.as_mutable(JSON), nullable=True)

class GraphClusterMembership(Base, TimestampMixin):
    """Phase 3: Cluster membership mapping (namespace + algorithm scope)."""
    __tablename__ = "graphrag_cluster_memberships"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    node_id = Column(String, ForeignKey("graphrag_nodes.id"), index=True, nullable=False)
    cluster_id = Column(String, index=True, nullable=False)  # e.g. c1, c2
    namespace = Column(String, index=True, nullable=False)
    algorithm = Column(String, index=True, default="louvain")
    # Optional score / modularity contribution placeholder
    score = Column(Float, nullable=True)

class GraphClusterSummary(Base, TimestampMixin):
    """Cached LLM summaries for clusters (Phase 3)."""
    __tablename__ = "graphrag_cluster_summaries"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    cluster_id = Column(String, index=True, nullable=False)
    namespace = Column(String, index=True, nullable=False)
    algorithm = Column(String, index=True, default="louvain")
    top_terms_hash = Column(String, index=True, nullable=True)
    label = Column(String, nullable=True)
    summary = Column(Text, nullable=True)
    token_count = Column(Integer, nullable=True)
    # Simple freshness TTL enforcement could rely on updated_at

class GraphSnapshot(Base, TimestampMixin):
    """Graph snapshot metadata (Phase >=11) capturing high-level state for diff & time-travel views."""
    __tablename__ = "graphrag_snapshots"

    id = Column(String, primary_key=True, index=True)
    namespace = Column(String, index=True, nullable=False)
    node_count = Column(Integer, nullable=False)
    edge_count = Column(Integer, nullable=False)
    modularity = Column(Float, nullable=True)
    metadata_json = Column(JSON, nullable=True)  # store extra metrics (degree histogram, cluster sizes)


class IngestLog(Base, TimestampMixin):
        """Phase 5: Track document ingestion & indexing state to enable delta indexing.

        Status values:
            - ingested: raw ingest done (graph nodes/edges present)
            - indexed: included in last successful batch index
            - stale: content changed since last index run
        """
        __tablename__ = "graphrag_ingest_log"

        id = Column(String, primary_key=True, index=True)  # doc_id
        namespace = Column(String, index=True, nullable=False)
        content_hash = Column(String, index=True, nullable=False)
        first_seen_at = Column(DateTime(timezone=True), server_default=func.now())
        last_ingest_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
        last_indexed_at = Column(DateTime(timezone=True), nullable=True)
        status = Column(String, index=True, default="ingested")
        meta = Column(JSON, nullable=True)

