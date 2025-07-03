from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.models import get_db
from app.models.models import User
from app.models.schemas import GoogleDriveAuth, GoogleDriveCallback
from app.services.google_drive_service import google_drive_service
from app.routes.auth import get_current_user_dependency

router = APIRouter(prefix="/google-drive", tags=["google-drive"])

@router.get("/auth", response_model=GoogleDriveAuth)
def get_google_drive_auth_url(
    current_user: User = Depends(get_current_user_dependency)
):
    """Get Google Drive authorization URL."""
    auth_url = google_drive_service.get_authorization_url(current_user.id)
    return {"authorization_url": auth_url}

@router.get("/callback")
def google_drive_callback(
    code: str = Query(..., description="Authorization code from Google"),
    state: str = Query(None, description="State parameter"),
    error: str = Query(None, description="Error from OAuth"),
    db: Session = Depends(get_db)
):
    """Handle Google Drive OAuth callback."""
    from fastapi.responses import HTMLResponse
    
    if error:
        return HTMLResponse(content=f"""
        <html>
            <head><title>Google Drive Authentication</title></head>
            <body>
                <h2>Authentication Failed</h2>
                <p>Error: {error}</p>
                <script>
                    setTimeout(() => {{
                        window.close();
                    }}, 3000);
                </script>
            </body>
        </html>
        """)
    
    if not code:
        return HTMLResponse(content="""
        <html>
            <head><title>Google Drive Authentication</title></head>
            <body>
                <h2>Authentication Failed</h2>
                <p>No authorization code received</p>
                <script>
                    setTimeout(() => {{
                        window.close();
                    }}, 3000);
                </script>
            </body>
        </html>
        """)
    
    try:
        # Parse user ID from state parameter
        user_id = None
        if state:
            try:
                user_id = int(state)
            except ValueError:
                pass
        
        if not user_id:
            return HTMLResponse(content="""
            <html>
                <head><title>Google Drive Authentication</title></head>
                <body>
                    <h2>Authentication Failed</h2>
                    <p>Invalid state parameter</p>
                    <script>
                        setTimeout(() => {{
                            window.close();
                        }}, 3000);
                    </script>
                </body>
            </html>
            """)
        
        # Exchange code for tokens
        tokens = google_drive_service.exchange_code_for_tokens(code)
        
        # Save tokens to database
        success = google_drive_service.save_user_tokens(db, user_id, tokens)
        
        if not success:
            return HTMLResponse(content="""
            <html>
                <head><title>Google Drive Authentication</title></head>
                <body>
                    <h2>Authentication Failed</h2>
                    <p>Failed to save Google Drive tokens</p>
                    <script>
                        setTimeout(() => {{
                            window.close();
                        }}, 3000);
                    </script>
                </body>
            </html>
            """)
        
        return HTMLResponse(content="""
        <html>
            <head><title>Google Drive Authentication</title></head>
            <body>
                <h2>Authentication Successful!</h2>
                <p>Google Drive has been connected successfully. You can close this window.</p>
                <script>
                    // Notify parent window of success
                    if (window.opener) {{
                        window.opener.postMessage({{type: 'GOOGLE_AUTH_SUCCESS'}}, '*');
                    }}
                    setTimeout(() => {{
                        window.close();
                    }}, 2000);
                </script>
            </body>
        </html>
        """)
    
    except Exception as e:
        return HTMLResponse(content=f"""
        <html>
            <head><title>Google Drive Authentication</title></head>
            <body>
                <h2>Authentication Failed</h2>
                <p>Error: {str(e)}</p>
                <script>
                    if (window.opener) {{
                        window.opener.postMessage({{type: 'GOOGLE_AUTH_ERROR', error: '{str(e)}'}}, '*');
                    }}
                    setTimeout(() => {{
                        window.close();
                    }}, 3000);
                </script>
            </body>
        </html>
        """)

@router.get("/status")
def get_google_drive_status(
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """Check Google Drive connection status."""
    credentials = google_drive_service.get_user_credentials(db, current_user.id)
    is_connected = credentials is not None
    
    return {
        "is_connected": is_connected,
        "message": "Google Drive connected" if is_connected else "Google Drive not connected"
    }

@router.get("/folders/{folder_name}/files")
def list_files_in_folder(
    folder_name: str,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """List files in a specific Google Drive folder."""
    files = google_drive_service.list_files_in_folder(db, current_user.id, folder_name)
    
    return {
        "folder_name": folder_name,
        "files_count": len(files),
        "files": files
    }

@router.get("/debug")
def debug_google_drive_integration(
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """Debug Google Drive integration - check all aspects."""
    from app.models.models import UserConfig
    
    # Get user config
    user_config = db.query(UserConfig).filter(UserConfig.user_id == current_user.id).first()
    
    debug_info = {
        "user_id": current_user.id,
        "user_config_exists": user_config is not None,
        "google_drive_token_encrypted": None,
        "google_drive_token_exists": False,
        "credentials_valid": False,
        "cv_folder_name": "cvs",
        "folder_exists": False,
        "files_in_folder": [],
        "error_messages": []
    }
    
    if user_config:
        debug_info["google_drive_token_exists"] = user_config.google_drive_token is not None
        debug_info["google_drive_token_encrypted"] = user_config.google_drive_token[:50] + "..." if user_config.google_drive_token else None
        debug_info["cv_folder_name"] = user_config.cv_folder_name or "cvs"
        
        # Test credentials
        credentials = google_drive_service.get_user_credentials(db, current_user.id)
        debug_info["credentials_valid"] = credentials is not None
        
        if credentials:
            # Test folder search
            folder_name = debug_info["cv_folder_name"]
            folder_id = google_drive_service.find_folder_by_name(db, current_user.id, folder_name)
            debug_info["folder_exists"] = folder_id is not None
            debug_info["folder_id"] = folder_id
            
            if folder_id:
                # Test file listing
                files = google_drive_service.list_files_in_folder(db, current_user.id, folder_name)
                debug_info["files_in_folder"] = files
                debug_info["files_count"] = len(files)
            else:
                debug_info["error_messages"].append(f"Folder '{folder_name}' not found in Google Drive")
        else:
            debug_info["error_messages"].append("Invalid or expired Google Drive credentials")
    else:
        debug_info["error_messages"].append("No user configuration found")
    
    return debug_info

@router.post("/disconnect")
def disconnect_google_drive(
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """Disconnect Google Drive by removing stored tokens."""
    from app.models.models import UserConfig
    
    user_config = db.query(UserConfig).filter(UserConfig.user_id == current_user.id).first()
    if user_config:
        user_config.google_drive_token = None
        user_config.google_drive_refresh_token = None
        user_config.is_setup_complete = False
        db.commit()
    
    return {"message": "Google Drive disconnected successfully"}
