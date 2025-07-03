from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from app.models import create_tables
from app.routes import auth_router, google_drive_router, config_router, cv_matching_router
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Create FastAPI app
app = FastAPI(
    title="CV Matcher Agent",
    description="AI-powered CV matching system with Google Drive integration",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3002",  # React frontend
        "http://frontend:3000",   # Docker frontend internal
        "http://127.0.0.1:3002",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Create database tables on startup
@app.on_event("startup")
async def startup_event():
    create_tables()
    print("Database tables created successfully")

# Include routers with /api prefix
app.include_router(auth_router, prefix="/api")
app.include_router(google_drive_router, prefix="/api")
app.include_router(config_router, prefix="/api")
app.include_router(cv_matching_router, prefix="/api")

@app.get("/", response_class=HTMLResponse)
async def root():
    """Root endpoint with API documentation."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>CV Matcher Agent</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .header { color: #2c3e50; }
            .section { margin: 20px 0; }
            .endpoint { background: #f8f9fa; padding: 10px; margin: 5px 0; border-left: 4px solid #007bff; }
            .method { font-weight: bold; color: #007bff; }
            .description { color: #6c757d; }
            a { color: #007bff; text-decoration: none; }
            a:hover { text-decoration: underline; }
        </style>
    </head>
    <body>
        <h1 class="header">🤖 CV Matcher Agent API</h1>
        <p>Welcome to the CV Matcher Agent - an AI-powered system for matching CVs to job descriptions.</p>
        
        <div class="section">
            <h2>📚 API Documentation</h2>
            <p>
                <a href="/docs" target="_blank">Interactive API Documentation (Swagger UI)</a><br>
                <a href="/redoc" target="_blank">Alternative API Documentation (ReDoc)</a>
            </p>
        </div>
        
        <div class="section">
            <h2>🚀 Quick Start</h2>
            <ol>
                <li><strong>Register:</strong> POST /auth/register</li>
                <li><strong>Login:</strong> POST /auth/login</li>
                <li><strong>Setup Google Drive:</strong> GET /google-drive/auth</li>
                <li><strong>Configure OpenAI:</strong> POST /config/</li>
                <li><strong>Match CVs:</strong> POST /cv-matching/match</li>
            </ol>
        </div>
        
        <div class="section">
            <h2>🔗 Main Endpoints</h2>
            
            <div class="endpoint">
                <span class="method">POST</span> /auth/register
                <div class="description">Register a new user account</div>
            </div>
            
            <div class="endpoint">
                <span class="method">POST</span> /auth/login
                <div class="description">Login and receive access token</div>
            </div>
            
            <div class="endpoint">
                <span class="method">GET</span> /google-drive/auth
                <div class="description">Get Google Drive authorization URL</div>
            </div>
            
            <div class="endpoint">
                <span class="method">POST</span> /config/
                <div class="description">Configure OpenAI API key and CV folder</div>
            </div>
            
            <div class="endpoint">
                <span class="method">POST</span> /cv-matching/match
                <div class="description">Match CVs against job description</div>
            </div>
            
            <div class="endpoint">
                <span class="method">GET</span> /cv-matching/history
                <div class="description">Get matching history</div>
            </div>
        </div>
        
        <div class="section">
            <h2>🔐 Authentication</h2>
            <p>Most endpoints require authentication. Include the bearer token in the Authorization header:</p>
            <code>Authorization: Bearer &lt;your-access-token&gt;</code>
        </div>
        
        <div class="section">
            <h2>⚙️ Environment Setup</h2>
            <p>Make sure to configure the following environment variables:</p>
            <ul>
                <li><strong>GOOGLE_CLIENT_ID:</strong> Your Google OAuth2 client ID</li>
                <li><strong>GOOGLE_CLIENT_SECRET:</strong> Your Google OAuth2 client secret</li>
                <li><strong>SECRET_KEY:</strong> JWT secret key</li>
                <li><strong>DATABASE_URL:</strong> PostgreSQL connection string</li>
            </ul>
        </div>
    </body>
    </html>
    """

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "CV Matcher Agent",
        "version": "1.0.0"
    }

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    from fastapi.responses import JSONResponse
    print(f"Global exception: {exc}")
    import traceback
    traceback.print_exc()
    
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}"}
    )

if __name__ == "__main__":
    import uvicorn
    
    host = os.getenv("APP_HOST", "0.0.0.0")
    port = int(os.getenv("APP_PORT", "8000"))
    debug = os.getenv("DEBUG", "True").lower() == "true"
    
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=debug
    )
