# Resume Matcher Agent

A full-stack AI-powered web application for matching Resumes to job descriptions using OpenAI and Google Drive integration.

## 🚀 Features

- **React Frontend** with modern, responsive UI
- **Multi-user authentication** with secure JWT tokens
- **Google Drive integration** for Resume storage and access
- **OpenAI-powered Resume matching** using embeddings and LLM analysis
- **Interactive Dashboard** with real-time status monitoring
- **Resume Matching Interface** with detailed results and scoring
- **Configuration Management** for API keys and settings
- **Matching History** with export capabilities
- **Encrypted data storage** for API keys and tokens
- **PostgreSQL database** for persistent data
- **Docker containerization** for easy deployment
- **RESTful API** with comprehensive documentation

## 🏗️ Architecture

```
resume-matcher-agent/
├── frontend/                # React Frontend Application
│   ├── public/
│   │   └── index.html
│   ├── src/
│   │   ├── components/      # Reusable UI components
│   │   │   ├── Navbar.js
│   │   │   └── LoadingSpinner.js
│   │   ├── contexts/        # React Context (Auth, etc.)
│   │   │   └── AuthContext.js
│   │   ├── pages/           # Main application pages
│   │   │   ├── Login.js
│   │   │   ├── Register.js
│   │   │   ├── Dashboard.js
│   │   │   ├── CVMatching.js
│   │   │   ├── Configuration.js
│   │   │   ├── GoogleDriveSetup.js
│   │   │   └── History.js
│   │   ├── App.js           # Main App component
│   │   ├── index.js         # App entry point
│   │   └── index.css        # Global styles
│   ├── Dockerfile           # Frontend Docker configuration
│   ├── nginx.conf           # Nginx configuration for production
│   └── package.json         # Frontend dependencies
├── app/                     # FastAPI Backend Application
│   ├── main.py              # FastAPI application
│   ├── models/              # Database models and schemas
│   │   ├── database.py      # Database configuration
│   │   ├── models.py        # SQLAlchemy models
│   │   └── schemas.py       # Pydantic schemas
│   ├── routes/              # API routes (prefixed with /api)
│   │   ├── auth.py          # Authentication endpoints
│   │   ├── config.py        # User configuration
│   │   ├── google_drive.py  # Google Drive integration
│   │   └── cv_matching.py   # Resume matching endpoints
│   ├── services/            # Business logic
│   │   ├── auth_service.py
│   │   ├── google_drive_service.py
│   │   ├── cv_matching_service.py
│   │   └── user_config_service.py
│   └── utils/               # Utility functions
│       ├── auth.py          # JWT and password handling
│       ├── encryption.py    # Data encryption
│       └── document_parser.py # Resume text extraction
├── Dockerfile               # Backend Docker configuration
├── docker-compose.yml       # Full-stack orchestration
├── requirements.txt         # Backend dependencies
├── .env.example             # Environment variables template
└── .gitignore               # Git ignore rules
```

## 🛠️ Setup Instructions

### 1. Clone and Navigate

```bash
cd /Users/sanaalishah/Desktop/AI-projects/cv-matcher-agent
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` file with your credentials:

```env
# Google OAuth2 (Get from Google Cloud Console)
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback

# JWT Secret (Generate a secure random string)
SECRET_KEY=your-super-secret-jwt-key-change-this-in-production

# Database (Docker will handle this)
DATABASE_URL=postgresql://cvmatcher:securepassword@db:5432/cvmatcher_db
```

### 3. Google Cloud Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable Google Drive API
4. Create OAuth2 credentials:
   - Go to "Credentials" → "Create Credentials" → "OAuth 2.0 Client IDs"
   - Application type: Web application
   - Authorized redirect URIs: `http://localhost:8000/auth/google/callback`
5. Copy Client ID and Client Secret to `.env`

### 4. Run with Docker

```bash
# Build and start all services
docker-compose up --build

# Or run in background
docker-compose up -d --build
```

### 5. Access the Application

- **Frontend Application:** http://localhost:3002
- **API Documentation:** http://localhost:9000/docs
- **Alternative Docs:** http://localhost:9000/redoc
- **Database Admin:** http://localhost:8080 (Adminer)
- **Backend API:** http://localhost:9000

## 🖥️ Frontend Usage

### Getting Started
1. Open http://localhost:3002 in your browser
2. Register a new account or login with existing credentials
3. Complete the setup process:
   - Connect your Google Drive account
   - Configure your OpenAI API key
   - Set your Resume folder name
4. Start matching Resume to job descriptions!

### Key Features
- **Dashboard**: View system status and quick actions
- **Resume Matching**: Upload job descriptions and get AI-powered matches
- **Configuration**: Manage API keys and folder settings
- **Google Drive Setup**: Connect and manage your Google Drive integration
- **History**: View and export previous matching sessions

## 📖 API Usage (Optional)

The application provides a full frontend interface, but you can also use the API directly:

### 1. Register User

```bash
curl -X POST "http://localhost:9000/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "securepassword123"
  }'
```

### 2. Login

```bash
curl -X POST "http://localhost:9000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "securepassword123"
  }'
```

### 3. Match Resume

```bash
curl -X POST "http://localhost:9000/api/cv-matching/match" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "job_description": "Looking for a senior Python developer with FastAPI experience, machine learning knowledge, and 5+ years of backend development experience."
  }'
```

## 🔧 Development

### Local Development (without Docker)

1. Install PostgreSQL locally
2. Create virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. Update `.env` with local database URL
4. Run application:
   ```bash
   uvicorn app.main:app --reload --port 9000
   ```

### Adding Features

The project is designed to be modular and extensible:

- **New endpoints:** Add to `app/routes/`
- **Business logic:** Add to `app/services/`
- **Database models:** Update `app/models/models.py`
- **API schemas:** Update `app/models/schemas.py`

## 🔒 Security Features

- **Password hashing** using bcrypt
- **JWT authentication** with configurable expiration
- **Data encryption** for sensitive information (API keys, tokens)
- **Input validation** using Pydantic
- **SQL injection protection** via SQLAlchemy ORM

## 📊 Database Schema

- **Users:** Store user accounts and authentication
- **UserConfig:** Store encrypted API keys and configuration
- **MatchLog:** Track Resume matching sessions
- **MatchResult:** Store individual Resume match results

## 🚦 Monitoring

- **Health endpoint:** `/health`
- **Database admin:** Adminer at http://localhost:8080
- **API docs:** Built-in Swagger UI at `/docs`

## 🔄 Future Enhancements

- Job description to candidate matching
- Advanced filtering and search
- Email notifications
- Batch processing
- Analytics dashboard
- Integration with job boards

## 🐛 Troubleshooting

### Common Issues

1. **Google Drive Auth Issues:**
   - Verify OAuth2 credentials in Google Cloud Console
   - Check redirect URI matches exactly
   - Ensure Google Drive API is enabled

2. **Database Connection:**
   - Check Docker containers are running: `docker-compose ps`
   - Verify database credentials in `.env`

3. **OpenAI API Issues:**
   - Verify API key is valid
   - Check OpenAI account has credits
   - Ensure model access permissions

### Logs

```bash
# View application logs
docker-compose logs web

# View database logs
docker-compose logs db

# Follow logs in real-time
docker-compose logs -f
```

## 📝 License

This project is for educational and development purposes. Ensure compliance with OpenAI and Google APIs terms of service.
