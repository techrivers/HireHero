# CV Matcher Agent - Requirements Document

## 📋 Project Overview

**Project Name:** CV Matcher Agent  
**Version:** 1.0.0  
**Document Date:** July 2025  
**Type:** AI-Powered Recruitment Assistant  

The CV Matcher Agent is a comprehensive full-stack web application that intelligently matches CVs to job descriptions using OpenAI's AI capabilities and Google Drive integration. The system provides recruiters and HR professionals with AI-powered candidate analysis, scoring, and recommendations.

## 🎯 Business Objectives

### Primary Goals
- **Intelligent CV Matching**: Automatically match CVs to job descriptions using AI analysis
- **Streamlined Recruitment**: Reduce manual CV screening time by 80%
- **Enhanced Decision Making**: Provide detailed AI-driven candidate analysis and recommendations
- **Seamless Integration**: Connect with existing Google Drive workflows
- **Scalable Solution**: Support multiple users and concurrent matching sessions

### Success Metrics
- Process 100+ CVs per job description in under 2 minutes
- Achieve 90%+ user satisfaction with match accuracy
- Reduce CV screening time from hours to minutes
- Support 50+ concurrent users

## 🏗️ System Architecture

### Architecture Pattern
- **Frontend**: Single Page Application (SPA) with React
- **Backend**: RESTful API with FastAPI
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Authentication**: JWT-based authentication
- **Integration**: Google Drive OAuth 2.0
- **AI Services**: OpenAI API for embeddings and analysis
- **Deployment**: Docker containerization

### Technology Stack

#### Backend Technologies
- **Framework**: FastAPI 0.104.1
- **Runtime**: Python 3.11+ with Uvicorn
- **Database**: PostgreSQL with psycopg2-binary 2.9.9
- **ORM**: SQLAlchemy 2.0.23
- **Authentication**: JWT with python-jose 3.3.0
- **Password Security**: bcrypt with passlib 1.7.4
- **AI Integration**: OpenAI API 1.50.0
- **Google Integration**: Google API Python Client 2.108.0
- **Document Processing**: PyPDF2, python-docx, pdfminer.six
- **Data Encryption**: cryptography 42.0.8
- **Environment Management**: python-dotenv 1.0.0

#### Frontend Technologies
- **Framework**: React 18.2.0
- **Routing**: React Router DOM 6.20.1
- **State Management**: React Query 3.39.3, React Context API
- **Forms**: React Hook Form 7.48.2
- **HTTP Client**: Axios 1.6.2
- **UI Components**: Lucide React 0.295.0
- **Notifications**: React Toastify 9.1.3
- **Styling**: CSS3 with CSS Grid and Flexbox
- **Build Tool**: Create React App 5.0.1

#### Infrastructure
- **Containerization**: Docker with Docker Compose
- **Database**: PostgreSQL 15
- **Web Server**: Nginx (production)
- **Process Management**: Uvicorn with auto-reload

## 🔧 Functional Requirements

### 1. User Management System

#### 1.1 User Registration
- **Requirement**: Users must be able to create accounts with username, email, and password
- **Validation**: 
  - Username: minimum 3 characters, unique
  - Email: valid email format, unique
  - Password: minimum 6 characters
- **Security**: Password hashing with bcrypt
- **Response**: User profile without sensitive data

#### 1.2 User Authentication
- **Requirement**: Secure login with JWT token generation
- **Session Management**: Configurable token expiration
- **Token Validation**: Automatic token verification on app load
- **Logout**: Complete session termination

#### 1.3 User Profile Management
- **Requirement**: Users can view and update their profile information
- **Authorization**: Users can only access their own data
- **Data Isolation**: Complete user data segregation

### 2. Configuration Management

#### 2.1 OpenAI API Configuration
- **Requirement**: Users must configure OpenAI API key for AI functionality
- **Security**: API keys encrypted at rest
- **Validation**: API key connectivity testing
- **UI**: Masked display of API keys (show as "••••••••••••••••")
- **Management**: Add, update, and remove API keys

#### 2.2 Google Drive Configuration
- **Requirement**: Users must connect Google Drive for CV access
- **OAuth Flow**: Complete OAuth 2.0 implementation
- **Token Management**: Automatic refresh token handling
- **Folder Configuration**: Specify CV folder name (default: "cvs")
- **Connection Status**: Real-time connection verification

#### 2.3 Setup Validation
- **Requirement**: Multi-step setup process validation
- **Checks**: 
  - Google Drive connection status
  - OpenAI API key configuration
  - CV folder existence verification
- **UI**: Setup completion indicators and guided workflow

### 3. Google Drive Integration

#### 3.1 OAuth 2.0 Authentication
- **Requirement**: Secure Google Drive access via OAuth 2.0
- **Flow**: Authorization code flow with PKCE
- **Scopes**: Read-only access to Google Drive files
- **Token Storage**: Encrypted token storage with refresh capability
- **Error Handling**: Graceful handling of expired or invalid tokens

#### 3.2 File Management
- **Requirement**: List and access CV files from specified Google Drive folder
- **Supported Formats**: PDF, DOC, DOCX, TXT
- **File Operations**: 
  - List files in folder
  - Download file content
  - Extract text from documents
- **Performance**: Efficient file processing with streaming

#### 3.3 Debug and Status Monitoring
- **Requirement**: Comprehensive Google Drive integration debugging
- **Features**:
  - Connection status verification
  - Token validity checking
  - Folder accessibility testing
  - File listing capabilities
- **UI**: Debug information display for troubleshooting

### 4. AI-Powered CV Matching

#### 4.1 Job Description Processing
- **Requirement**: Accept job descriptions for CV matching
- **Input Validation**: Required text field with minimum content
- **Processing**: Extract job requirements, skills, and criteria
- **Analysis**: Use OpenAI for job description analysis and categorization

#### 4.2 CV Analysis and Scoring
- **Requirement**: Intelligent CV analysis against job requirements
- **AI Processing**: 
  - Generate embeddings for semantic similarity
  - Extract candidate information (name, skills, experience)
  - Analyze relevance and compatibility
  - Generate detailed match analysis
- **Scoring System**: 
  - Relevance scores (0-1 scale)
  - Color-coded match categories (Excellent, Good, Average)
  - Detailed analysis with strengths and gaps

#### 4.3 Enhanced Matching Results
- **Requirement**: Comprehensive match results with detailed analysis
- **Data Extraction**:
  - Candidate name and professional summary
  - Technical skills and experience years
  - Education background
  - Key selling points and concerns
- **Analysis Features**:
  - Strengths and weaknesses identification
  - Gap analysis with recommendations
  - Match category classification
  - Detailed hiring recommendations

#### 4.4 Progress Tracking
- **Requirement**: Real-time progress updates during matching process
- **Features**:
  - 10-step progress animation
  - Status messages for each processing stage
  - Professional UI with gradient backgrounds
  - Error handling and recovery

### 5. Results Management

#### 5.1 Match History
- **Requirement**: Complete history of all CV matching sessions
- **Storage**: Persistent storage of match logs and results
- **Retrieval**: Paginated history with search capabilities
- **Display**: Summary view with key metrics

#### 5.2 Detailed Results Viewing
- **Requirement**: View complete match results for any historical session
- **Features**:
  - Full job description display
  - All candidate results with scores
  - Detailed analysis and recommendations
  - Export capabilities

#### 5.3 File Download and Export
- **Requirement**: Direct CV download from Google Drive
- **Features**:
  - Individual CV downloads
  - Batch CV downloads for top matches
  - Results export as JSON
  - Secure file streaming

#### 5.4 Data Management
- **Requirement**: Users can manage their match history
- **Operations**:
  - Delete individual match sessions
  - Export match results
  - View match statistics

### 6. User Interface Requirements

#### 6.1 Dashboard
- **Requirement**: Central hub showing system status and quick actions
- **Features**:
  - System status indicators
  - Recent matches display
  - Quick navigation to key features
  - Setup completion tracking

#### 6.2 Navigation
- **Requirement**: Intuitive navigation system
- **Features**:
  - Top navigation bar with active states
  - Icon-based menu items
  - Breadcrumb navigation
  - Mobile-responsive design

#### 6.3 Forms and Validation
- **Requirement**: Comprehensive form handling with validation
- **Features**:
  - Real-time validation feedback
  - Error message display
  - Loading states during submission
  - Success/failure notifications

#### 6.4 Responsive Design
- **Requirement**: Mobile-first responsive design
- **Features**:
  - Flexible grid layouts
  - Touch-friendly interactions
  - Consistent experience across devices
  - Optimized performance

## 🔒 Non-Functional Requirements

### 1. Security Requirements

#### 1.1 Authentication Security
- **JWT Implementation**: Secure token generation and validation
- **Password Security**: bcrypt hashing with proper salt rounds
- **Session Management**: Configurable token expiration
- **Authorization**: Role-based access control per user

#### 1.2 Data Protection
- **Encryption**: Sensitive data encrypted at rest (API keys, tokens)
- **Input Validation**: Comprehensive input sanitization
- **SQL Injection Prevention**: Parameterized queries via ORM
- **CORS Configuration**: Proper cross-origin resource sharing

#### 1.3 API Security
- **Rate Limiting**: Protection against abuse
- **Input Validation**: Pydantic schema validation
- **Error Handling**: Secure error messages without sensitive information
- **HTTPS**: Encrypted communication in production

### 2. Performance Requirements

#### 2.1 Response Times
- **API Endpoints**: < 200ms for standard operations
- **CV Matching**: < 2 minutes for 100+ CVs
- **File Downloads**: < 5 seconds for typical CV files
- **Authentication**: < 100ms for login/logout

#### 2.2 Scalability
- **Concurrent Users**: Support 50+ simultaneous users
- **Database Performance**: Optimized queries with proper indexing
- **Memory Usage**: Efficient memory management for large file processing
- **Caching**: Strategic caching for frequently accessed data

#### 2.3 Reliability
- **Uptime**: 99.9% availability target
- **Error Recovery**: Graceful handling of failures
- **Data Consistency**: ACID compliance for database operations
- **Backup Strategy**: Regular automated backups

### 3. Usability Requirements

#### 3.1 User Experience
- **Learning Curve**: Intuitive interface requiring minimal training
- **Error Messages**: Clear, actionable error messages
- **Loading States**: Visual feedback for all operations
- **Help System**: Contextual help and guidance

#### 3.2 Accessibility
- **Keyboard Navigation**: Full keyboard accessibility
- **Screen Reader Support**: Proper ARIA labels and semantic HTML
- **Color Contrast**: WCAG compliance for visual elements
- **Responsive Design**: Consistent experience across devices

### 4. Compatibility Requirements

#### 4.1 Browser Support
- **Modern Browsers**: Chrome, Firefox, Safari, Edge (latest 2 versions)
- **JavaScript**: ES6+ features with polyfills
- **Mobile Browsers**: iOS Safari, Chrome Mobile
- **Progressive Enhancement**: Graceful degradation for older browsers

#### 4.2 Integration Compatibility
- **Google Drive API**: v3 compatibility
- **OpenAI API**: GPT-4 and embedding models
- **Database**: PostgreSQL 12+
- **Docker**: Compatible with Docker Compose v2

## 🚀 Implementation Guidelines

### 1. Development Approach

#### 1.1 Architecture Patterns
- **Clean Architecture**: Separation of concerns between layers
- **RESTful API**: Standard HTTP methods and status codes
- **Component-Based UI**: Reusable React components
- **State Management**: Centralized state with React Context

#### 1.2 Code Quality
- **Type Safety**: TypeScript for frontend (future enhancement)
- **Code Standards**: PEP 8 for Python, ESLint for JavaScript
- **Documentation**: Comprehensive API documentation with OpenAPI
- **Testing**: Unit tests for critical business logic

#### 1.3 Security Implementation
- **Input Validation**: Server-side validation for all inputs
- **Authentication**: JWT implementation with proper expiration
- **Authorization**: Resource-level access control
- **Encryption**: Industry-standard encryption for sensitive data

### 2. Deployment Requirements

#### 2.1 Containerization
- **Docker Images**: Optimized multi-stage builds
- **Container Orchestration**: Docker Compose for development
- **Environment Configuration**: Environment-specific settings
- **Health Checks**: Container health monitoring

#### 2.2 Production Deployment
- **Reverse Proxy**: Nginx for static file serving
- **SSL/TLS**: Certificate management and renewal
- **Environment Variables**: Secure configuration management
- **Monitoring**: Application performance monitoring

### 3. Maintenance and Support

#### 3.1 Monitoring
- **Health Endpoints**: System health checking
- **Logging**: Comprehensive application logging
- **Error Tracking**: Error monitoring and alerting
- **Performance Metrics**: Key performance indicators

#### 3.2 Updates and Patches
- **Version Control**: Git-based version management
- **Database Migrations**: Automated schema updates
- **Dependency Management**: Regular security updates
- **Backup Procedures**: Automated backup and recovery

## 📊 Data Requirements

### 1. Database Schema

#### 1.1 User Management
- **Users Table**: id, username, email, hashed_password, is_active, created_at
- **Relationships**: One-to-many with user_configs and match_logs
- **Indexes**: username, email (unique indexes)

#### 1.2 Configuration Management
- **UserConfig Table**: id, user_id, google_drive_tokens, cv_folder_name, openai_api_key, is_setup_complete
- **Encryption**: API keys and tokens encrypted at rest
- **Relationships**: Many-to-one with users

#### 1.3 Match History
- **MatchLog Table**: id, user_id, job_description, total_cvs_processed, top_matches_count, created_at
- **MatchResult Table**: id, match_log_id, cv_filename, candidate_data, relevance_score, analysis
- **Relationships**: One-to-many between match_logs and match_results

### 2. Data Flow

#### 2.1 User Registration Flow
1. User submits registration form
2. Server validates input data
3. Password hashed with bcrypt
4. User record created in database
5. Success response returned

#### 2.2 CV Matching Flow
1. User submits job description
2. System validates configuration
3. Google Drive CVs retrieved
4. OpenAI analysis performed
5. Results stored in database
6. Response returned to user

#### 2.3 Configuration Flow
1. User provides API keys/tokens
2. Server encrypts sensitive data
3. Configuration stored in database
4. Validation tests performed
5. Setup status updated

## 🧪 Testing Requirements

### 1. Unit Testing
- **Backend**: FastAPI endpoint testing
- **Frontend**: React component testing
- **Services**: Business logic testing
- **Utilities**: Helper function testing

### 2. Integration Testing
- **API Integration**: End-to-end API testing
- **Database Integration**: Database operation testing
- **External Services**: Google Drive and OpenAI integration testing
- **Authentication**: JWT flow testing

### 3. User Acceptance Testing
- **Workflow Testing**: Complete user journey testing
- **Performance Testing**: Load testing with multiple users
- **Security Testing**: Vulnerability assessment
- **Usability Testing**: User experience validation

## 📈 Future Enhancements

### 1. Advanced Features
- **Batch Processing**: Multiple job descriptions simultaneously
- **Advanced Analytics**: Detailed matching statistics and trends
- **Email Notifications**: Automated match result notifications
- **Integration APIs**: Third-party recruitment tool integration

### 2. AI Improvements
- **Custom Models**: Fine-tuned models for specific industries
- **Multi-language Support**: CV analysis in multiple languages
- **Bias Detection**: AI fairness and bias mitigation
- **Confidence Scoring**: Match confidence indicators

### 3. Platform Expansion
- **Mobile App**: Native mobile application
- **Team Collaboration**: Multi-user collaboration features
- **Advanced Search**: Semantic search across match history
- **Reporting**: Comprehensive analytics dashboard

## 🎯 Success Criteria

### 1. Technical Success
- **Performance**: Process 100+ CVs in under 2 minutes
- **Accuracy**: 90%+ user satisfaction with match results
- **Reliability**: 99.9% uptime with proper error handling
- **Security**: Zero security vulnerabilities in production

### 2. Business Success
- **User Adoption**: 100+ active users within 6 months
- **Efficiency**: 80% reduction in CV screening time
- **Accuracy**: 95% match accuracy compared to manual screening
- **Scalability**: Support for 1000+ CVs per matching session

### 3. User Experience Success
- **Usability**: < 5 minutes to complete initial setup
- **Satisfaction**: 4.5+ star rating from users
- **Adoption**: 80% of users complete the full setup process
- **Retention**: 70% monthly active user retention

---

**Document Version:** 1.0.0  
**Last Updated:** July 2025  
**Next Review:** October 2025  
**Approval:** Pending stakeholder review