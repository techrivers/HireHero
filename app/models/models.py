from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey, Float, JSON
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
    chat_conversations = relationship("ChatConversation", back_populates="user", cascade="all, delete-orphan")

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

class ChatConversation(Base):
    __tablename__ = "chat_conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    session_id = Column(String, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    is_active = Column(Boolean, default=True)
    
    # Relationships
    user = relationship("User", back_populates="chat_conversations")
    messages = relationship("ChatMessage", back_populates="conversation", cascade="all, delete-orphan")

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("chat_conversations.id"), nullable=False)
    role = Column(String, nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    message_metadata = Column(JSON, nullable=True)  # Store additional data like intent, actions, etc.
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    conversation = relationship("ChatConversation", back_populates="messages")

# Enhanced Candidate Module Models

class Job(Base):
    __tablename__ = "jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False, index=True)
    company = Column(String(100), nullable=False)
    url = Column(Text)
    description = Column(Text, nullable=False)
    required_skills = Column(JSON)  # JSON array of required skills
    experience_level = Column(String(50))  # entry, mid, senior, executive
    salary_range = Column(String(100))  # Optional salary information
    location = Column(String(100))  # Job location
    remote_friendly = Column(Boolean, default=False)
    posted_date = Column(DateTime(timezone=True))
    expiry_date = Column(DateTime(timezone=True))  # Optional expiry date
    status = Column(String(20), default="active")  # active, expired, filled
    scrape_source = Column(String(100))  # Which career page this came from
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    job_matches = relationship("JobMatch", back_populates="job", cascade="all, delete-orphan")

class Candidate(Base):
    __tablename__ = "candidates"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    email = Column(String(100), index=True)
    phone = Column(String(20))
    cv_filename = Column(String(255), nullable=False)
    skills_json = Column(JSON)  # Comprehensive skills with proficiency levels
    experience_years = Column(Integer, default=0)
    education = Column(JSON)  # Education history as JSON
    certifications = Column(JSON)  # Certifications as JSON
    professional_summary = Column(Text)
    current_role = Column(String(100))
    current_company = Column(String(100))
    preferred_locations = Column(JSON)  # Preferred work locations
    remote_preference = Column(Boolean, default=True)
    availability_status = Column(String(20), default="available")  # available, employed, interviewing
    salary_expectation = Column(String(100))
    google_drive_file_id = Column(String(100), index=True)
    last_updated = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    job_matches = relationship("JobMatch", back_populates="candidate", cascade="all, delete-orphan")

class JobMatch(Base):
    __tablename__ = "job_matches"
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False)
    match_score = Column(Float, nullable=False, index=True)  # 0.0 to 1.0
    explanation = Column(Text)  # AI-generated explanation for the match
    extra_skills = Column(JSON)  # Skills beyond job requirements
    alternative_roles = Column(JSON)  # Alternative job suggestions
    strengths = Column(JSON)  # Key strengths for this match
    gaps = Column(JSON)  # Skill/experience gaps
    recommendation = Column(String(20), default="consider")  # strong, consider, weak
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    job = relationship("Job", back_populates="job_matches")
    candidate = relationship("Candidate", back_populates="job_matches")

class CareerPageConfig(Base):
    __tablename__ = "career_page_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    company_name = Column(String(100), nullable=False)
    career_url = Column(Text, nullable=False)
    scrape_frequency = Column(Integer, default=24)  # Hours between scrapes
    is_active = Column(Boolean, default=True)
    scraping_rules = Column(JSON)  # Custom scraping configuration
    authentication_data = Column(Text)  # Encrypted login credentials if needed
    last_scraped = Column(DateTime(timezone=True))
    last_success = Column(Boolean, default=True)
    error_message = Column(Text)  # Last error if scraping failed
    jobs_found_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="career_page_configs")

class RefreshSchedule(Base):
    __tablename__ = "refresh_schedules"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    job_refresh_interval = Column(Integer, default=24)  # Hours
    cv_refresh_interval = Column(Integer, default=6)  # Hours
    auto_matching_enabled = Column(Boolean, default=True)
    last_job_refresh = Column(DateTime(timezone=True))
    last_cv_refresh = Column(DateTime(timezone=True))
    last_matching_run = Column(DateTime(timezone=True))
    refresh_status = Column(String(20), default="idle")  # idle, running, error
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="refresh_schedule")

# Enhanced existing models relationships
User.career_page_configs = relationship("CareerPageConfig", back_populates="user", cascade="all, delete-orphan")
User.refresh_schedule = relationship("RefreshSchedule", back_populates="user", cascade="all, delete-orphan")
