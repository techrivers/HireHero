from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user_configs = relationship("UserConfig", back_populates="user", cascade="all, delete-orphan")
    match_logs = relationship("MatchLog", back_populates="user", cascade="all, delete-orphan")

class UserConfig(Base):
    __tablename__ = "user_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    google_drive_token = Column(Text)  # Encrypted JSON token
    google_drive_refresh_token = Column(Text)  # Encrypted refresh token
    cv_folder_name = Column(String(100), default="cvs")
    openai_api_key = Column(Text)  # Encrypted API key
    is_setup_complete = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="user_configs")

class MatchLog(Base):
    __tablename__ = "match_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    job_description = Column(Text, nullable=False)
    total_cvs_processed = Column(Integer, default=0)
    top_matches_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="match_logs")
    match_results = relationship("MatchResult", back_populates="match_log", cascade="all, delete-orphan")

class MatchResult(Base):
    __tablename__ = "match_results"
    
    id = Column(Integer, primary_key=True, index=True)
    match_log_id = Column(Integer, ForeignKey("match_logs.id"), nullable=False)
    cv_filename = Column(String(255), nullable=False)
    candidate_name = Column(String(100))
    candidate_summary = Column(Text)
    relevance_score = Column(Float, nullable=False)
    is_top_match = Column(Boolean, default=False)
    google_drive_file_id = Column(String(100))
    download_url = Column(Text)
    key_skills = Column(Text)  # JSON array of skills
    match_analysis = Column(Text)  # Detailed analysis from LLM
    experience_years = Column(Integer)  # Years of experience
    
    # Relationships
    match_log = relationship("MatchLog", back_populates="match_results")
