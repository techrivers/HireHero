from __future__ import annotations
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime

# User Schemas
class UserBase(BaseModel):
    username: str
    email: EmailStr

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class UserLogin(BaseModel):
    username: str
    password: str

# Token Schemas
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

# User Configuration Schemas
class UserConfigBase(BaseModel):
    cv_folder_name: str = "cvs"

class UserConfigCreate(UserConfigBase):
    openai_api_key: Optional[str] = None

class UserConfigUpdate(BaseModel):
    cv_folder_name: Optional[str] = None
    openai_api_key: Optional[str] = None

class UserConfigResponse(UserConfigBase):
    id: int
    user_id: int
    openai_api_key: Optional[str] = None
    google_drive_connected: bool = False
    is_setup_complete: bool
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True

# Google Drive Schemas
class GoogleDriveAuth(BaseModel):
    authorization_url: str

class GoogleDriveCallback(BaseModel):
    code: str

# Resume Matching Schemas
class MatchRequest(BaseModel):
    job_description: str

class CVMatch(BaseModel):
    cv_filename: str
    candidate_name: Optional[str]
    candidate_summary: Optional[str]
    relevance_score: float
    match_status: str
    download_url: Optional[str] = None
    google_drive_file_id: Optional[str] = None
    key_skills: Optional[List[str]] = None
    match_analysis: Optional[str] = None
    experience_years: Optional[int] = None

class EnhancedCVMatch(BaseModel):
    cv_filename: str
    candidate_name: str
    professional_summary: str
    relevance_score: float
    match_category: str
    technical_skills: List[str]
    experience_years: Optional[int] = None
    education: List[str]
    strengths: List[str]
    gaps: List[str]
    recommendation: str
    key_selling_points: List[str]
    concerns: List[str]
    google_drive_file_id: str
    download_url: Optional[str] = None

class MatchDistribution(BaseModel):
    excellent_matches: int
    good_matches: int
    average_matches: int
    total_relevant: int
    total_reviewed: int

class JobAnalysis(BaseModel):
    position: str
    required_skills: List[str]
    seniority_level: str

class MatchResponse(BaseModel):
    results: List[CVMatch]
    match_id: Optional[int] = None
    total_cvs_processed: int
    top_matches_count: Optional[int] = None
    status: Optional[str] = "success"
    message: Optional[str] = None
    folder_name: Optional[str] = None

class EnhancedMatchResponse(BaseModel):
    summary: str
    search_effectiveness: str
    results: List[EnhancedCVMatch]
    total_cvs_reviewed: int
    total_relevant_matches: int
    match_distribution: MatchDistribution
    recommendations: List[str]
    top_candidate_summary: Optional[str] = None
    job_analysis: JobAnalysis
    match_id: int
    processing_time: str

# Match History Schemas
class MatchLogResponse(BaseModel):
    id: int
    job_description: str
    total_cvs_processed: int
    top_matches_count: int
    created_at: datetime
    results: Optional[List[MatchResultResponse]] = None
    
    class Config:
        from_attributes = True

class MatchResultResponse(BaseModel):
    id: int
    cv_filename: str
    candidate_name: Optional[str]
    candidate_summary: Optional[str]
    relevance_score: float
    is_top_match: bool
    download_url: Optional[str]
    google_drive_file_id: Optional[str]
    
    class Config:
        from_attributes = True

# Chat Schemas
class ChatMessageRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class ChatMessageResponse(BaseModel):
    message: str
    action: str  # continue, search, show_results, configure
    suggestions: List[str] = []
    results: Optional[Dict[str, Any]] = None
    session_id: str
    timestamp: str

class ChatConversationResponse(BaseModel):
    id: int
    session_id: str
    created_at: datetime
    updated_at: datetime
    is_active: bool
    message_count: int
    
    class Config:
        from_attributes = True

class ChatMessageHistoryResponse(BaseModel):
    id: int
    role: str
    content: str
    message_metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

# Search Execution Schema
class SearchExecutionRequest(BaseModel):
    session_id: str

# Enhanced Candidate Module Schemas

# Job Schemas
class JobBase(BaseModel):
    title: str
    company: str
    description: str
    required_skills: List[str]
    experience_level: Optional[str] = None
    salary_range: Optional[str] = None
    location: Optional[str] = None
    remote_friendly: bool = False

class JobCreate(JobBase):
    url: Optional[str] = None
    posted_date: Optional[datetime] = None
    expiry_date: Optional[datetime] = None
    scrape_source: Optional[str] = None

class JobUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    required_skills: Optional[List[str]] = None
    experience_level: Optional[str] = None
    salary_range: Optional[str] = None
    location: Optional[str] = None
    remote_friendly: Optional[bool] = None
    status: Optional[str] = None

class JobResponse(JobBase):
    id: int
    url: Optional[str]
    posted_date: Optional[datetime]
    expiry_date: Optional[datetime]
    status: str
    scrape_source: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    match_count: Optional[int] = 0
    
    class Config:
        from_attributes = True

# Candidate Schemas
class CandidateBase(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None

class CandidateCreate(CandidateBase):
    cv_filename: str
    google_drive_file_id: Optional[str] = None
    skills_json: Optional[Dict[str, Any]] = None
    experience_years: Optional[int] = None
    education: Optional[List[Dict[str, Any]]] = None
    certifications: Optional[List[Dict[str, Any]]] = None

class CandidateUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    skills_json: Optional[Dict[str, Any]] = None
    experience_years: Optional[int] = None
    education: Optional[List[Dict[str, Any]]] = None
    certifications: Optional[List[Dict[str, Any]]] = None
    professional_summary: Optional[str] = None
    current_role: Optional[str] = None
    current_company: Optional[str] = None
    availability_status: Optional[str] = None
    salary_expectation: Optional[str] = None

class CandidateResponse(CandidateBase):
    id: int
    cv_filename: str
    skills_json: Optional[Dict[str, Any]]
    experience_years: Optional[int]
    education: Optional[List[Dict[str, Any]]]
    certifications: Optional[List[Dict[str, Any]]]
    professional_summary: Optional[str]
    current_role: Optional[str]
    current_company: Optional[str]
    preferred_locations: Optional[List[str]]
    remote_preference: Optional[bool]
    availability_status: Optional[str]
    salary_expectation: Optional[str]
    google_drive_file_id: Optional[str]
    last_updated: datetime
    created_at: datetime
    match_count: Optional[int] = 0
    avg_match_score: Optional[float] = 0.0
    
    class Config:
        from_attributes = True

# Job Match Schemas
class JobMatchCreate(BaseModel):
    job_id: int
    candidate_id: int
    match_score: float
    explanation: Optional[str] = None
    extra_skills: Optional[List[str]] = None
    alternative_roles: Optional[List[str]] = None
    strengths: Optional[List[str]] = None
    gaps: Optional[List[str]] = None
    recommendation: Optional[str] = "consider"

class JobMatchResponse(BaseModel):
    id: int
    job_id: int
    candidate_id: int
    match_score: float
    explanation: Optional[str]
    extra_skills: Optional[List[str]]
    alternative_roles: Optional[List[str]]
    strengths: Optional[List[str]]
    gaps: Optional[List[str]]
    recommendation: str
    created_at: datetime
    updated_at: Optional[datetime]
    
    # Related data
    job: Optional[JobResponse] = None
    candidate: Optional[CandidateResponse] = None
    
    class Config:
        from_attributes = True

# Career Page Config Schemas
class CareerPageConfigBase(BaseModel):
    company_name: str
    career_url: str
    scrape_frequency: int = 24

class CareerPageConfigCreate(CareerPageConfigBase):
    scraping_rules: Optional[Dict[str, Any]] = None
    authentication_data: Optional[str] = None

class CareerPageConfigUpdate(BaseModel):
    company_name: Optional[str] = None
    career_url: Optional[str] = None
    scrape_frequency: Optional[int] = None
    is_active: Optional[bool] = None
    scraping_rules: Optional[Dict[str, Any]] = None
    authentication_data: Optional[str] = None

class CareerPageConfigResponse(CareerPageConfigBase):
    id: int
    user_id: int
    is_active: bool
    last_scraped: Optional[datetime]
    last_success: bool
    error_message: Optional[str]
    jobs_found_count: int
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True

# Refresh Schedule Schemas
class RefreshScheduleBase(BaseModel):
    job_refresh_interval: int = 24
    cv_refresh_interval: int = 6
    auto_matching_enabled: bool = True

class RefreshScheduleUpdate(BaseModel):
    job_refresh_interval: Optional[int] = None
    cv_refresh_interval: Optional[int] = None
    auto_matching_enabled: Optional[bool] = None

class RefreshScheduleResponse(RefreshScheduleBase):
    id: int
    user_id: int
    last_job_refresh: Optional[datetime]
    last_cv_refresh: Optional[datetime]
    last_matching_run: Optional[datetime]
    refresh_status: str
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True

# Search and Query Schemas
class IntelligentSearchRequest(BaseModel):
    query: str
    filters: Optional[Dict[str, Any]] = None
    session_id: Optional[str] = None

class IntelligentSearchResponse(BaseModel):
    query: str
    results: List[CandidateResponse]
    total_results: int
    search_time: float
    suggestions: List[str]
    filters_applied: Dict[str, Any]
    session_id: str

# Bulk Operations Schemas
class BulkMatchRequest(BaseModel):
    job_ids: List[int]
    candidate_ids: Optional[List[int]] = None  # If None, match against all candidates
    force_refresh: bool = False

class BulkMatchResponse(BaseModel):
    matches_created: int
    matches_updated: int
    processing_time: float
    errors: List[str]
    job_results: Dict[int, int]  # job_id -> matches_count

# Analytics Schemas
class JobAnalyticsResponse(BaseModel):
    total_jobs: int
    active_jobs: int
    jobs_by_company: Dict[str, int]
    jobs_by_experience_level: Dict[str, int]
    top_required_skills: List[Dict[str, Any]]
    recent_jobs_trend: List[Dict[str, Any]]

class CandidateAnalyticsResponse(BaseModel):
    total_candidates: int
    candidates_by_experience: Dict[str, int]
    candidates_by_availability: Dict[str, int]
    top_candidate_skills: List[Dict[str, Any]]
    avg_experience_years: float
    skill_distribution: Dict[str, int]

class MatchingAnalyticsResponse(BaseModel):
    total_matches: int
    avg_match_score: float
    matches_by_recommendation: Dict[str, int]
    top_matched_jobs: List[Dict[str, Any]]
    top_matched_candidates: List[Dict[str, Any]]
    skill_gap_analysis: List[Dict[str, Any]]

# Rebuild models to resolve forward references
MatchLogResponse.model_rebuild()
JobMatchResponse.model_rebuild()
