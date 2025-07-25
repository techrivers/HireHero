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

# CV Matching Schemas
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
    results: Optional[List['MatchResultResponse']] = None
    
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

# Rebuild models to resolve forward references
MatchLogResponse.model_rebuild()
