from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models import get_db
from app.models.models import User
from app.models.schemas import UserConfigCreate, UserConfigUpdate, UserConfigResponse
from app.services.user_config_service import user_config_service
from app.routes.auth import get_current_user_dependency

router = APIRouter(prefix="/config", tags=["user-configuration"])

@router.get("/", response_model=UserConfigResponse)
def get_user_configuration(
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """Get current user configuration."""
    config = user_config_service.get_user_config(db, current_user.id)
    if not config:
        raise HTTPException(status_code=404, detail="User configuration not found")
    
    # Return masked API key if exists
    response_data = {
        "id": config.id,
        "user_id": config.user_id,
        "cv_folder_name": config.cv_folder_name,
        "openai_api_key": "••••••••••••••••" if config.openai_api_key else None,
        "google_drive_connected": config.google_drive_token is not None,
        "is_setup_complete": config.is_setup_complete,
        "created_at": config.created_at,
        "updated_at": config.updated_at
    }
    
    return response_data

@router.post("/", response_model=UserConfigResponse)
def create_user_configuration(
    config_data: UserConfigCreate,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """Create or update user configuration."""
    config = user_config_service.create_or_update_config(db, current_user.id, config_data)
    
    # Return masked API key if exists
    response_data = {
        "id": config.id,
        "user_id": config.user_id,
        "cv_folder_name": config.cv_folder_name,
        "openai_api_key": "••••••••••••••••" if config.openai_api_key else None,
        "google_drive_connected": config.google_drive_token is not None,
        "is_setup_complete": config.is_setup_complete,
        "created_at": config.created_at,
        "updated_at": config.updated_at
    }
    
    return response_data

@router.put("/", response_model=UserConfigResponse)
def update_user_configuration(
    config_update: UserConfigUpdate,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """Update user configuration."""
    config = user_config_service.update_config(db, current_user.id, config_update)
    if not config:
        raise HTTPException(status_code=404, detail="User configuration not found")
    
    # Return masked API key if exists
    response_data = {
        "id": config.id,
        "user_id": config.user_id,
        "cv_folder_name": config.cv_folder_name,
        "openai_api_key": "••••••••••••••••" if config.openai_api_key else None,
        "google_drive_connected": config.google_drive_token is not None,
        "is_setup_complete": config.is_setup_complete,
        "created_at": config.created_at,
        "updated_at": config.updated_at
    }
    
    return response_data

@router.get("/setup-status")
def get_setup_status(
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """Check if user setup is complete."""
    is_complete = user_config_service.is_setup_complete(db, current_user.id)
    config = user_config_service.get_user_config(db, current_user.id)
    
    setup_status = {
        "is_setup_complete": is_complete,
        "google_drive_connected": config and config.google_drive_token is not None,
        "openai_key_configured": config and config.openai_api_key is not None,
        "cv_folder_name": config.cv_folder_name if config else "cvs"
    }
    
    return setup_status

@router.delete("/openai-key")
def remove_openai_key(
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """Remove stored OpenAI API key."""
    config = user_config_service.get_user_config(db, current_user.id)
    if not config:
        raise HTTPException(status_code=404, detail="User configuration not found")
    
    config.openai_api_key = None
    config.is_setup_complete = False
    db.commit()
    
    return {"message": "OpenAI API key removed successfully"}
