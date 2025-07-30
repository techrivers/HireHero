# Complete CV Matcher Agent - AI-Powered Resume Matching System

```
You are an expert full-stack developer. Build a production-ready CV Matcher Agent web application with the following comprehensive specifications:

## 🎯 APPLICATION OVERVIEW
Create a full-stack AI-powered recruitment assistant that integrates with Google Drive and uses OpenAI GPT-3.5/4 to intelligently match Resume with job requirements through natural language conversations. The application must support real-time chat capabilities, background CV processing, and semantic candidate matching with detailed analytics.

## 🏗️ TECHNICAL STACK REQUIREMENTS

### Backend (Python + FastAPI)
- **Framework**: FastAPI with async/await patterns
- **Database**: PostgreSQL with SQLAlchemy ORM
- **AI Integration**: OpenAI GPT-3.5/GPT-4 API
- **Authentication**: JWT-based token authentication
- **Cloud Storage**: Google Drive API integration
- **Real-time**: WebSocket support for instant messaging
- **Environment**: Dockerized with health checks

### Frontend (React + Vite)
- **Framework**: React 18+ with modern hooks
- **Styling**: Tailwind CSS with modern UI components
- **Icons**: Lucide React icons
- **HTTP Client**: Axios with WebSocket integration
- **Real-time**: WebSocket client for chat

### Infrastructure
- **Containerization**: Docker + Docker Compose
- **Database**: PostgreSQL 15 with persistent volumes
- **Reverse Proxy**: Built-in FastAPI CORS handling

## 📊 GOOGLE DRIVE INTEGRATION

### OAuth 2.0 Configuration
Set up Google Drive API credentials:
```env
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=http://localhost:9000/api/google-drive/callback
GOOGLE_SCOPES=https://www.googleapis.com/auth/drive.readonly
```

### OAuth 2.0 Flow Implementation
1. **Authorization Route** (`/api/google-drive/auth`): Generate OAuth URL for Google Drive access
2. **Callback Handler** (`/api/google-drive/callback`): Exchange authorization code for access/refresh tokens
3. **Token Management**: Automatic token refresh with encrypted storage
4. **Security**: State parameter validation and CSRF protection
5. **File Access**: Read-only access to specified CV folders

### Supported Document Types
- **PDF Files**: Full text extraction with pdfplumber
- **Word Documents**: DOCX and DOC format support
- **Text Files**: Plain text CV parsing
- **Excel Files**: Resume data in spreadsheet format
- **PowerPoint**: Presentation-style resumes

## 🤖 AI INTEGRATION ARCHITECTURE

### Message Processing Pipeline
1. **Intent Analysis**: Use GPT-4 to determine search requirements from natural language
2. **CV Processing**: Background extraction and semantic analysis of resume content
3. **Matching Algorithm**: Semantic similarity scoring with 50%+ threshold
4. **Context Building**: Combine user query + CV data + conversation history
5. **Response Generation**: Use GPT-3.5/4 to create detailed candidate recommendations

### OpenAI Service Implementation
```python
# Intent analysis for Resume matching
async def analyze_search_intent(message: str) -> Dict[str, Any]:
    analysis_prompt = f"""
    Analyze this recruitment query and extract search criteria:
    User message: "{message}"
    
    Extract and respond with JSON:
    {{
        "intent": "search_request|general_query|refinement",
        "search_criteria": {{
            "job_title": "extracted job title or null",
            "skills": ["list", "of", "required", "skills"],
            "experience_min": number_or_null,
            "experience_max": number_or_null,
            "education": "degree requirements or null",
            "location": "location preference or null"
        }},
        "search_type": "specific|broad|exploratory"
    }}
    """

# CV content analysis and summarization
async def generate_cv_summary(cv_content: str, filename: str) -> Dict[str, Any]:
    summary_prompt = f"""
    Analyze this CV content and extract key information:
    
    CV Content: {cv_content[:4000]}
    Filename: {filename}
    
    Provide structured analysis in JSON format:
    {{
        "candidate_name": "full name",
        "contact_info": {{"email": "", "phone": "", "location": ""}},
        "summary": "professional summary",
        "experience": {{
            "years_total": number,
            "current_role": "title",
            "previous_roles": ["list of roles"]
        }},
        "skills": {{
            "technical": ["programming", "languages", "tools"],
            "soft": ["communication", "leadership", "etc"]
        }},
        "education": ["degrees and certifications"],
        "key_achievements": ["notable accomplishments"]
    }}
    """
```

### Context Management
- **Chat History**: Maintain conversation context with last 10 messages
- **Session Persistence**: PostgreSQL storage for conversation continuity
- **CV Cache**: In-memory caching with threading locks for performance
- **Background Processing**: Async CV analysis without blocking chat responses

## 🗄️ DATABASE SCHEMA

### SQLAlchemy Models Definition
```python
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    configs = relationship("UserConfig", back_populates="user")
    match_logs = relationship("MatchLog", back_populates="user")
    conversations = relationship("ChatConversation", back_populates="user")

class UserConfig(Base):
    __tablename__ = "user_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    openai_api_key = Column(Text)  # Encrypted storage
    google_drive_token = Column(Text)  # Encrypted OAuth tokens
    cv_folder_name = Column(String(255), default="cvs")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="configs")

class ChatConversation(Base):
    __tablename__ = "chat_conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    session_id = Column(String(255), unique=True, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="conversations")
    messages = relationship("ChatMessage", back_populates="conversation")

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("chat_conversations.id"), nullable=False)
    role = Column(String(20), nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    message_metadata = Column(Text)  # JSON string for additional data
    created_at = Column(DateTime, default=datetime.utcnow)
    
    conversation = relationship("ChatConversation", back_populates="messages")

class MatchLog(Base):
    __tablename__ = "match_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    job_description = Column(Text, nullable=False)
    total_cvs_processed = Column(Integer, default=0)
    matches_found = Column(Integer, default=0)
    processing_time = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="match_logs")
    results = relationship("MatchResult", back_populates="match_log")

class MatchResult(Base):
    __tablename__ = "match_results"
    
    id = Column(Integer, primary_key=True, index=True)
    match_log_id = Column(Integer, ForeignKey("match_logs.id"), nullable=False)
    cv_filename = Column(String(255), nullable=False)
    candidate_name = Column(String(255))
    relevance_score = Column(Float, nullable=False)
    candidate_summary = Column(Text)
    key_skills = Column(Text)  # JSON string
    match_analysis = Column(Text)
    google_drive_file_id = Column(String(255))
    download_url = Column(String(500))
    
    match_log = relationship("MatchLog", back_populates="results")
```

## 🎨 FRONTEND DESIGN SPECIFICATIONS

### Authentication & Configuration Screen
- **Multi-step Setup**: User registration → Google Drive connection → OpenAI API key
- **Visual Wizard**: Progressive disclosure with clear step indicators
- **Connection Status**: Real-time validation of API credentials
- **Setup Guidance**: Helpful tooltips and documentation links

### Main Chat Interface Design
- **Header Section**:
  - CV Matcher Agent branding with professional color scheme
  - Connection indicators (Google Drive: green, OpenAI: blue)
  - CV count display with processing status
  - Settings and logout options
- **Chat Area**:
  - User messages: Blue bubbles with right alignment
  - AI responses: Gray bubbles with CV match cards
  - Typing indicators during AI processing
  - Message timestamps and status indicators
- **Input Section**:
  - Auto-expanding textarea with smart suggestions
  - Quick action buttons for common queries
  - File upload option for job descriptions
  - Voice input support (future enhancement)

### CV Match Results Display
- **Match Cards Layout**:
  - Candidate photo placeholder with professional styling
  - Relevance score with color-coded indicators (90%+ green, 70-89% yellow, 50-69% orange)
  - Key skills tags with matching highlights
  - Experience summary with role progression
  - Download and contact action buttons
- **Detailed View Modal**:
  - Full candidate profile with formatted resume content
  - Match analysis explanation with highlighted sections
  - Skills comparison matrix against job requirements
  - Contact information and availability status

### Responsive Design Standards
- **Mobile-first approach** with touch-friendly interactions
- **Tablet optimization** for recruiter dashboard usage
- **Desktop power-user** features with keyboard shortcuts
- **Accessibility compliance** with WCAG 2.1 standards

## 🔌 COMPREHENSIVE API STRUCTURE

### Authentication Routes (`/api/auth/*`)
```python
POST /api/auth/register          # User registration with validation
POST /api/auth/login             # JWT token generation
GET  /api/auth/me                # Current user profile
POST /api/auth/refresh           # Token refresh mechanism
POST /api/auth/logout            # Token invalidation
```

### Configuration Routes (`/api/config/*`)
```python
GET  /api/config                 # Get user configuration
PUT  /api/config                 # Update OpenAI/Google Drive settings
POST /api/config/test-openai     # Validate OpenAI API key
POST /api/config/test-gdrive     # Test Google Drive connection
```

### Google Drive Routes (`/api/google-drive/*`)
```python
GET  /api/google-drive/auth              # Get OAuth authorization URL
GET  /api/google-drive/callback          # Handle OAuth callback
GET  /api/google-drive/folders           # List available folders
GET  /api/google-drive/files             # List CV files in folder
GET  /api/google-drive/download/:fileId  # Download specific CV file
POST /api/google-drive/disconnect        # Revoke access tokens
```

### Chat API Routes (`/api/chat/*`)
```python
POST /api/chat                           # Send message and get AI response
GET  /api/chat/conversations             # List user conversations
GET  /api/chat/conversation/:sessionId/messages  # Get conversation history
DELETE /api/chat/conversation/:sessionId  # Delete conversation
POST /api/chat/search                     # Execute CV search
GET  /api/chat/suggestions               # Get query suggestions
GET  /api/chat/status                    # Get processing status
```

### Resume Matching Routes (`/api/cv-matching/*`)
```python
POST /api/cv-matching/match              # Execute CV matching
GET  /api/cv-matching/history            # Get matching history
GET  /api/cv-matching/results/:logId     # Get detailed match results
POST /api/cv-matching/feedback           # Submit result feedback
GET  /api/cv-matching/analytics          # Matching analytics data
```

### WebSocket Routes (`/api/chat/ws/*`)
```python
WS /api/chat/ws/:userId                  # Real-time chat connection
# Messages: status, processing, response, error, timeout
# Connection manager for multiple concurrent users
```

### Response Format Standards
```json
// Successful chat response with CV matches
{
  "userMessage": {
    "id": "uuid",
    "content": "Find me senior Python developers",
    "sender": "user",
    "createdAt": "2024-01-20T10:30:00Z"
  },
  "botMessage": {
    "id": "uuid",
    "content": "I found 5 senior Python developers matching your criteria...",
    "sender": "assistant", 
    "createdAt": "2024-01-20T10:30:05Z",
    "action": "show_results|continue|configure",
    "suggestions": ["Show more details", "Refine search", "Find similar candidates"]
  },
  "results": {
    "total_cvs_processed": 25,
    "matches": [
      {
        "cv_filename": "john_smith_cv.pdf",
        "candidate_name": "John Smith",
        "relevance_score": 92.5,
        "candidate_summary": "Senior Python developer with 7 years experience...",
        "key_skills": "[\"Python\", \"Django\", \"PostgreSQL\", \"AWS\"]",
        "match_analysis": "Strong match with all required skills...",
        "download_url": "https://drive.google.com/file/d/...",
        "experience_years": 7
      }
    ],
    "processing_time": "3.2 seconds"
  }
}
```

## 🚀 DOCKER CONFIGURATION

### Backend Dockerfile (`Dockerfile`)
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for CV processing
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    poppler-utils \
    tesseract-ocr \
    libtesseract-dev \
    antiword \
    unrtf \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Health check endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:9000/health || exit 1

EXPOSE 9000

# Start application with proper async handling
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "9000", "--workers", "1"]
```

### Frontend Dockerfile (`frontend/Dockerfile`)
```dockerfile
# Build stage
FROM node:18-alpine as build

WORKDIR /app
COPY package*.json ./
RUN npm install

COPY . .
RUN npm run build

# Production stage  
FROM nginx:alpine

# Copy built assets
COPY --from=build /app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf

# Health check for nginx
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:3002/health || exit 1

EXPOSE 3002

CMD ["nginx", "-g", "daemon off;"]
```

### Docker Compose Configuration (`docker-compose.yml`)
```yaml
services:
  db:
    image: postgres:15
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-username}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-password}
      POSTGRES_DB: ${POSTGRES_DB:-cv_matcher_db}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    networks:
      - cv-matcher-network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-username}"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 10s

  backend:
    build: .
    ports:
      - "9000:9000"
    environment:
      - DATABASE_URL=postgresql://${POSTGRES_USER:-username}:${POSTGRES_PASSWORD:-password}@db/${POSTGRES_DB:-cv_matcher_db}
      - SECRET_KEY=${SECRET_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - GOOGLE_CLIENT_ID=${GOOGLE_CLIENT_ID}
      - GOOGLE_CLIENT_SECRET=${GOOGLE_CLIENT_SECRET}
      - GOOGLE_REDIRECT_URI=${GOOGLE_REDIRECT_URI}
    depends_on:
      db:
        condition: service_healthy
    volumes:
      - ./app:/app/app
    networks:
      - cv-matcher-network
    restart: unless-stopped

  frontend:
    build: ./frontend
    ports:
      - "3002:3002"
    depends_on:
      - backend
    networks:
      - cv-matcher-network
    restart: unless-stopped

volumes:
  postgres_data:

networks:
  cv-matcher-network:
    driver: bridge
```

## 🔧 CORE SERVICE IMPLEMENTATIONS

### Intelligent Chat Agent Service
```python
import asyncio
import openai
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from app.services.google_drive_service import google_drive_service
from app.services.optimized_cv_matching_service import OptimizedCVMatchingService

class IntelligentChatAgentService:
    def __init__(self):
        self.openai_client = None
        self.cv_matching_service = OptimizedCVMatchingService()
        self.conversation_contexts = {}  # User conversation history
        self.cv_cache = {}  # Fast CV data access
        self.cache_lock = threading.Lock()
        self.MATCH_THRESHOLD = 0.50  # 50% relevance threshold
        self.MAX_RESULTS = 6  # Top 6 candidates only
    
    async def process_chat_message(self, user_id: int, message: str, db: Session) -> Dict[str, Any]:
        """Main chat processing pipeline with full async support."""
        try:
            # Get or initialize conversation context
            context = self.get_conversation_context(user_id)
            
            # Add user message to context
            context['messages'].append({
                'role': 'user',
                'content': message,
                'timestamp': datetime.now().isoformat()
            })
            
            # Initialize OpenAI client if needed
            if not self.openai_client:
                api_key = self.get_openai_key(db, user_id)
                if api_key:
                    self.initialize_openai_client(api_key)
            
            # Analyze search intent using AI
            intent_analysis = await self.analyze_search_intent(message)
            
            if intent_analysis['intent'] == 'search_request':
                # Process CV search request
                response = await self.process_search_request(
                    user_id, intent_analysis, db, context
                )
            elif intent_analysis['intent'] == 'refinement':
                # Refine previous search
                response = await self.refine_search(
                    user_id, message, db, context
                )
            else:
                # General conversation
                response = await self.generate_general_response(
                    message, context
                )
            
            # Add AI response to context
            context['messages'].append({
                'role': 'assistant',
                'content': response['message'],
                'timestamp': datetime.now().isoformat(),
                'action': response['action']
            })
            
            # Clean up old messages (keep last 10)
            if len(context['messages']) > 10:
                context['messages'] = context['messages'][-10:]
            
            return response
            
        except Exception as e:
            print(f"❌ Error in chat processing: {e}")
            return {
                'message': "I encountered an error processing your request. Please try again.",
                'action': 'error',
                'suggestions': ['Try a different search', 'Check your configuration']
            }
    
    async def process_search_request(self, user_id: int, analysis: Dict, db: Session, context: Dict) -> Dict[str, Any]:
        """Process CV search with intelligent matching."""
        try:
            # Get CV summaries (cached or fresh)
            cv_summaries = await self.get_cv_summaries(user_id, db)
            
            if not cv_summaries:
                return {
                    'message': """🔄 **I need to process your CVs first!**
                    
I'm analyzing the CVs in your Google Drive folder to build candidate profiles. This usually takes 1-2 minutes for the first time.

✨ **What I'm doing:**
• Extracting candidate information from each CV
• Building searchable profiles with skills and experience
• Creating AI-powered summaries for quick matching

**Please try your search again in a moment!**""",
                    'action': 'processing',
                    'suggestions': [
                        'Check processing status',
                        'Configure Google Drive',
                        'Try again in 30 seconds'
                    ]
                }
            
            # Execute semantic matching
            search_criteria = analysis['search_criteria']
            matches = await self.cv_matching_service.find_matches(
                cv_summaries, search_criteria, self.MATCH_THRESHOLD
            )
            
            if matches:
                # Format successful search response
                top_matches = matches[:self.MAX_RESULTS]
                response_message = f"""🎯 **Found {len(top_matches)} excellent candidates!**

**Your search criteria:**
• Role: {search_criteria.get('job_title', 'Any')}
• Skills: {', '.join(search_criteria.get('skills', [])) or 'Any'}
• Experience: {search_criteria.get('experience_min', 0)}+ years

**Top matches:**
{self.format_candidate_summary(top_matches[:3])}

💡 **Next steps:**
• View detailed candidate profiles
• Download CVs for review
• Refine search criteria
• Contact candidates directly"""

                return {
                    'message': response_message,
                    'action': 'show_results',
                    'suggestions': [
                        'Show more details',
                        'Download CVs',
                        'Refine search',
                        'Find similar candidates'
                    ],
                    'results': self.format_results_for_ui(top_matches)
                }
            else:
                # No matches found
                return {
                    'message': f"""🔍 **No matches found with current criteria**

**Searched for:**
• Role: {search_criteria.get('job_title', 'Any')}
• Skills: {', '.join(search_criteria.get('skills', [])) or 'Any'}
• Experience: {search_criteria.get('experience_min', 0)}+ years

**Try adjusting your search:**
• Use broader skill terms (e.g., "web development" vs "React.js")
• Lower experience requirements
• Try related job titles
• Search for complementary skills

**I can help you refine the search criteria!**""",
                    'action': 'continue',
                    'suggestions': [
                        'Broaden skill requirements',
                        'Lower experience needs',
                        'Try related job titles',
                        'Show all candidates'
                    ]
                }
                
        except Exception as e:
            print(f"❌ Error in search processing: {e}")
            return {
                'message': "I encountered an error during the search. Please try again.",
                'action': 'error',
                'suggestions': ['Try a simpler search', 'Check your configuration']
            }
```

### Optimized Resume Matching Service
```python
import asyncio
import json
from typing import List, Dict, Any, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

class OptimizedCVMatchingService:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(
            max_features=5000,
            stop_words='english',
            ngram_range=(1, 2),
            min_df=1,
            max_df=0.95
        )
        self.skill_weights = {
            'technical': 0.4,
            'experience': 0.3,
            'education': 0.2,
            'achievements': 0.1
        }
    
    async def find_matches(self, cv_summaries: List[Dict], search_criteria: Dict, threshold: float = 0.5) -> List[Dict]:
        """Find CV matches using semantic similarity and weighted scoring."""
        try:
            if not cv_summaries:
                return []
            
            # Build search query from criteria
            search_query = self.build_search_query(search_criteria)
            
            # Prepare CV texts for vectorization
            cv_texts = []
            for cv in cv_summaries:
                cv_text = self.extract_searchable_text(cv)
                cv_texts.append(cv_text)
            
            # Create TF-IDF vectors
            all_texts = cv_texts + [search_query]
            tfidf_matrix = self.vectorizer.fit_transform(all_texts)
            
            # Calculate similarity scores
            query_vector = tfidf_matrix[-1]  # Last item is the search query
            cv_vectors = tfidf_matrix[:-1]   # All except last are CV vectors
            
            similarity_scores = cosine_similarity(query_vector, cv_vectors).flatten()
            
            # Enhanced scoring with criteria matching
            enhanced_scores = []
            for i, (cv, base_score) in enumerate(zip(cv_summaries, similarity_scores)):
                enhanced_score = await self.calculate_enhanced_score(
                    cv, search_criteria, base_score
                )
                enhanced_scores.append(enhanced_score)
            
            # Filter and sort matches
            matches = []
            for i, score in enumerate(enhanced_scores):
                if score >= threshold:
                    match = cv_summaries[i].copy()
                    match['match_score'] = score
                    match['match_details'] = self.generate_match_explanation(
                        cv_summaries[i], search_criteria, score
                    )
                    matches.append(match)
            
            # Sort by score descending
            matches.sort(key=lambda x: x['match_score'], reverse=True)
            
            return matches
            
        except Exception as e:
            print(f"❌ Error in Resume matching: {e}")
            return []
    
    def build_search_query(self, criteria: Dict) -> str:
        """Build comprehensive search query from criteria."""
        query_parts = []
        
        if criteria.get('job_title'):
            query_parts.append(f"Job title: {criteria['job_title']}")
        
        if criteria.get('skills'):
            query_parts.append(f"Required skills: {' '.join(criteria['skills'])}")
        
        if criteria.get('experience_min'):
            query_parts.append(f"Experience: {criteria['experience_min']} years minimum")
        
        if criteria.get('education'):
            query_parts.append(f"Education: {criteria['education']}")
        
        return ' '.join(query_parts)
    
    def extract_searchable_text(self, cv_summary: Dict) -> str:
        """Extract all searchable text from CV summary."""
        text_parts = []
        
        # Add summary content
        if isinstance(cv_summary.get('summary'), dict):
            summary = cv_summary['summary']
            text_parts.extend([
                summary.get('summary', ''),
                ' '.join(summary.get('skills', {}).get('technical', [])),
                ' '.join(summary.get('skills', {}).get('soft', [])),
                ' '.join(summary.get('education', [])),
                ' '.join(summary.get('key_achievements', []))
            ])
        
        # Add extracted skills and role
        text_parts.extend([
            ' '.join(cv_summary.get('skills', [])),
            cv_summary.get('role', ''),
            cv_summary.get('filename', '')
        ])
        
        return ' '.join(filter(None, text_parts))
    
    async def calculate_enhanced_score(self, cv: Dict, criteria: Dict, base_score: float) -> float:
        """Calculate enhanced matching score with weighted criteria."""
        try:
            enhanced_score = base_score * 0.6  # Base semantic similarity (60%)
            
            # Job title matching (20%)
            if criteria.get('job_title'):
                title_score = self.calculate_title_match(cv, criteria['job_title'])
                enhanced_score += title_score * 0.2
            
            # Skills matching (15%)
            if criteria.get('skills'):
                skills_score = self.calculate_skills_match(cv, criteria['skills'])
                enhanced_score += skills_score * 0.15
            
            # Experience matching (5%)
            if criteria.get('experience_min'):
                exp_score = self.calculate_experience_match(cv, criteria['experience_min'])
                enhanced_score += exp_score * 0.05
            
            return min(enhanced_score, 1.0)  # Cap at 1.0
            
        except Exception as e:
            print(f"❌ Error calculating enhanced score: {e}")
            return base_score
    
    def calculate_title_match(self, cv: Dict, target_title: str) -> float:
        """Calculate job title matching score."""
        cv_role = cv.get('role', '').lower()
        target_lower = target_title.lower()
        
        # Exact match
        if target_lower in cv_role or cv_role in target_lower:
            return 1.0
        
        # Partial match with key terms
        title_terms = set(target_lower.split())
        role_terms = set(cv_role.split())
        common_terms = title_terms.intersection(role_terms)
        
        if common_terms:
            return len(common_terms) / len(title_terms)
        
        return 0.0
    
    def calculate_skills_match(self, cv: Dict, required_skills: List[str]) -> float:
        """Calculate skills matching score."""
        cv_skills = cv.get('skills', [])
        if not cv_skills or not required_skills:
            return 0.0
        
        cv_skills_lower = [skill.lower() for skill in cv_skills]
        matched_skills = 0
        
        for required_skill in required_skills:
            required_lower = required_skill.lower()
            for cv_skill in cv_skills_lower:
                if required_lower in cv_skill or cv_skill in required_lower:
                    matched_skills += 1
                    break
        
        return matched_skills / len(required_skills)
    
    def calculate_experience_match(self, cv: Dict, min_experience: int) -> float:
        """Calculate experience matching score."""
        cv_experience = cv.get('experience', 0)
        
        if cv_experience >= min_experience:
            return 1.0
        elif cv_experience >= min_experience * 0.8:  # 80% of required
            return 0.8
        elif cv_experience >= min_experience * 0.6:  # 60% of required
            return 0.6
        else:
            return 0.3  # Some experience is better than none
```

## ✅ SUCCESS CRITERIA & DELIVERABLES

### Functional Requirements Checklist
- [ ] **Authentication System**: JWT-based user registration and login works
- [ ] **Google Drive Integration**: OAuth flow connects and accesses CV files
- [ ] **OpenAI Configuration**: API key validation and AI response generation
- [ ] **CV Processing**: Background extraction and summarization of resume content
- [ ] **Real-time Chat**: WebSocket connection for instant messaging
- [ ] **Semantic Matching**: AI-powered candidate search with relevance scoring
- [ ] **Result Display**: Formatted match results with candidate details
- [ ] **Conversation Persistence**: Chat history stored and retrievable
- [ ] **Error Handling**: Graceful degradation and user-friendly error messages
- [ ] **Performance**: Sub-5-second response times for chat interactions

### User Experience Requirements
- [ ] **Onboarding Flow**: Clear setup wizard for Google Drive and OpenAI
- [ ] **Chat Interface**: Intuitive messaging with typing indicators
- [ ] **Search Results**: Well-formatted candidate cards with key information
- [ ] **Mobile Responsive**: Works on phones, tablets, and desktop
- [ ] **Loading States**: Clear feedback during processing
- [ ] **Error Recovery**: Helpful suggestions when things go wrong
- [ ] **Accessibility**: Keyboard navigation and screen reader support

### Technical Requirements
- [ ] **Docker Deployment**: Full application runs with `docker-compose up --build`
- [ ] **Database Migrations**: Automatic schema creation and updates
- [ ] **Health Checks**: All services monitored and self-healing
- [ ] **Security**: Encrypted token storage and secure API endpoints
- [ ] **Performance**: Efficient CV caching and background processing
- [ ] **Logging**: Comprehensive error tracking and debugging information
- [ ] **Scalability**: Async architecture supports multiple concurrent users

## 🚨 DOCKER TROUBLESHOOTING SECTION

### Common Docker Setup Issues and Solutions

#### Issue 1: Port conflicts
**Error:** `bind: address already in use`
**Fix:** Check for running services and update ports in docker-compose.yml:
```bash
# Check what's using the ports
lsof -i :9000 -i :3002 -i :5432
# Kill processes or change ports in docker-compose.yml
```

#### Issue 2: Database connection failures
**Error:** `could not connect to server: Connection refused`
**Fix:** Ensure proper service dependencies and health checks:
```yaml
backend:
  depends_on:
    db:
      condition: service_healthy
```

#### Issue 3: OpenAI API key not working
**Error:** AI responses fail with authentication errors
**Fix:** Verify environment variable in .env file:
```env
OPENAI_API_KEY=sk-your-actual-openai-api-key-here
```

#### Issue 4: Google Drive OAuth failures
**Error:** `invalid_client` or `redirect_uri_mismatch`
**Fix:** Verify Google Cloud Console settings match .env configuration:
```env
GOOGLE_CLIENT_ID=your-actual-client-id.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-actual-client-secret
GOOGLE_REDIRECT_URI=http://localhost:9000/api/google-drive/callback
```

#### Issue 5: CV processing timeouts
**Error:** CVs not processing or background tasks failing
**Fix:** Increase timeout values and check system resources:
```python
# In docker-compose.yml, add memory limits
services:
  backend:
    deploy:
      resources:
        limits:
          memory: 2G
```

### Quick Reset Commands
```bash
# Complete system reset
docker-compose down -v --remove-orphans
docker system prune -f
docker volume prune -f
docker-compose up --build -d

# Check service health
docker-compose ps
docker-compose logs backend
docker-compose logs frontend
```

### Expected Healthy Output
```
NAME                        STATUS
cv-matcher-agent_backend    Up (healthy)
cv-matcher-agent_db         Up (healthy)  
cv-matcher-agent_frontend   Up (healthy)
```

## 🔗 REAL-TIME CHAT IMPLEMENTATION

### WebSocket Architecture

The chat system implements full WebSocket support for real-time communication between users and the AI assistant.

#### Connection Management
```python
# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()
        self.active_connections[user_id] = websocket
    
    def disconnect(self, user_id: int):
        if user_id in self.active_connections:
            del self.active_connections[user_id]
    
    async def send_json_message(self, data: dict, user_id: int):
        if user_id in self.active_connections:
            try:
                await self.active_connections[user_id].send_json(data)
            except:
                self.disconnect(user_id)
```

#### Message Types
- **status**: Connection status and CV processing updates
- **processing**: Indicates AI is working on request
- **response**: Standard AI response with chat content
- **delayed_response**: Background processed responses
- **timeout**: Fallback when processing takes too long
- **error**: Error handling with user-friendly messages

#### Frontend WebSocket Integration
```javascript
// WebSocket connection with automatic reconnection
const initializeWebSocket = () => {
  const userId = getCurrentUserId();
  const wsUrl = `ws://localhost:9000/api/chat/ws/${userId}`;
  
  const ws = new WebSocket(wsUrl);
  
  ws.onopen = () => setConnectionStatus('connected');
  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    handleWebSocketMessage(data);
  };
  ws.onclose = () => {
    setConnectionStatus('disconnected');
    // Automatic reconnection after 5 seconds
    setTimeout(initializeWebSocket, 5000);
  };
};
```

#### Fallback to REST API
If WebSocket connection fails, the frontend automatically falls back to REST API calls ensuring reliable communication.

## 📝 FINAL IMPLEMENTATION NOTES

### Key Architectural Decisions
1. **Async-First Design**: All CV processing and AI operations use async/await for non-blocking performance
2. **Intelligent Caching**: Multi-level caching (memory + database) for CV data and AI responses
3. **Graceful Degradation**: WebSocket → REST API fallback, OpenAI → fallback responses
4. **Security by Design**: JWT tokens, encrypted API key storage, OAuth state validation
5. **Production Ready**: Health checks, logging, error handling, resource management

### Performance Optimizations
- **Background Processing**: CV analysis doesn't block chat responses
- **Semantic Caching**: Similar queries reuse previous AI analysis
- **Concurrent Processing**: Multiple CVs processed simultaneously with semaphore controls
- **Database Indexing**: Optimized queries for conversation and match history
- **Response Streaming**: Large AI responses sent in chunks for better UX

### Extensibility Features
- **Plugin Architecture**: Easy to add new CV parsing formats
- **Configurable AI Prompts**: Customizable for different industries
- **Multi-language Support**: Ready for internationalization
- **Analytics Integration**: Built-in tracking for usage and performance metrics
- **API-First Design**: RESTful endpoints support future mobile apps

### Production Deployment Considerations
- **Environment Variables**: All sensitive data externalized
- **Container Security**: Non-root users, minimal base images
- **Monitoring**: Health checks, structured logging, error tracking
- **Scalability**: Horizontal scaling support with load balancing
- **Backup Strategy**: Database backups and disaster recovery

## 🏁 FINAL DELIVERABLES

1. **Complete Source Code**: All backend Python services, frontend React components, and configuration files
2. **Docker Configuration**: Multi-service orchestration with health checks and proper networking
3. **Database Schema**: PostgreSQL schema with migrations and seed data
4. **API Documentation**: Complete OpenAPI specification with examples
5. **Environment Setup**: Comprehensive .env templates and configuration guides
6. **README Documentation**: Step-by-step setup instructions with troubleshooting
7. **Working Application**: Fully functional system accessible at http://localhost:3002

The final CV Matcher Agent represents enterprise-grade architecture with production-ready features including real-time chat, intelligent Resume matching, and comprehensive Google Drive integration. The system is designed for scalability, maintainability, and exceptional user experience.
```