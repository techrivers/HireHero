# CV Matcher Agent - Project Structure

```
cv-matcher-agent/
├── README.md                    # Main documentation
├── Makefile                     # Development commands
├── setup.sh                     # Automated setup script
├── init_db.py                   # Database initialization
├── test_api.py                  # API testing script
├── .env.example                 # Environment template
├── .gitignore                   # Git ignore rules
├── requirements.txt             # Python dependencies
├── Dockerfile                   # Container configuration
├── docker-compose.yml           # Main compose file
├── docker-compose.override.yml  # Development overrides
└── app/                         # Main application
    ├── __init__.py
    ├── main.py                  # FastAPI application
    ├── models/                  # Database layer
    │   ├── __init__.py
    │   ├── database.py          # DB connection
    │   ├── models.py            # SQLAlchemy models
    │   └── schemas.py           # Pydantic schemas
    ├── routes/                  # API endpoints
    │   ├── __init__.py
    │   ├── auth.py              # Authentication
    │   ├── config.py            # User configuration
    │   ├── google_drive.py      # Google Drive integration
    │   └── cv_matching.py       # CV matching logic
    ├── services/                # Business logic
    │   ├── __init__.py
    │   ├── auth_service.py      # Authentication service
    │   ├── google_drive_service.py # Google Drive service
    │   ├── cv_matching_service.py # CV matching service
    │   └── user_config_service.py # User config service
    └── utils/                   # Utility functions
        ├── __init__.py
        ├── auth.py              # JWT & password utils
        ├── encryption.py        # Data encryption
        └── document_parser.py   # CV text extraction
```

## Key Components

### 🔐 Authentication & Security
- JWT-based authentication with configurable expiration
- Password hashing using bcrypt
- Data encryption for sensitive information (API keys, tokens)
- Input validation using Pydantic schemas

### 📁 Google Drive Integration
- OAuth2 authentication flow
- Automatic token refresh
- File listing and download
- Support for multiple document formats (PDF, DOCX, TXT)

### 🤖 AI-Powered CV Matching
- OpenAI embeddings for semantic similarity
- LLM-based CV analysis and scoring
- Candidate information extraction
- Relevance scoring and ranking

### 🗄️ Database Architecture
- PostgreSQL with SQLAlchemy ORM
- User management and authentication
- Encrypted configuration storage
- Match history and results tracking

### 🐳 Containerization
- Docker containerization for easy deployment
- Docker Compose for multi-service orchestration
- Development and production configurations
- Health checks and monitoring

### 📊 API Features
- RESTful API design
- Comprehensive documentation (Swagger/OpenAPI)
- Error handling and validation
- Pagination and filtering

## Usage Patterns

### Development Workflow
1. `make setup` - Initialize environment
2. Edit `.env` with credentials
3. `make up-build` - Start services
4. `make init-db` - Setup demo data
5. `make test` - Verify functionality

### Production Deployment
1. Configure environment variables
2. Set up Google Cloud OAuth2
3. Deploy with Docker Compose
4. Monitor with health checks

### API Integration
1. Register user account
2. Authenticate with JWT token
3. Setup Google Drive access
4. Configure OpenAI API key
5. Submit job descriptions for matching

## Extension Points

The architecture is designed for extensibility:

- **New document types:** Add parsers in `utils/document_parser.py`
- **Additional AI models:** Extend `services/cv_matching_service.py`
- **More integrations:** Add new services and routes
- **Enhanced analytics:** Extend database models and endpoints
- **UI interfaces:** Frontend can consume the RESTful API

## Security Considerations

- All sensitive data is encrypted at rest
- JWT tokens have configurable expiration
- OAuth2 for secure third-party authentication
- Input validation prevents injection attacks
- CORS configuration for browser security
