from sqlalchemy.orm import Session
from app.models.models import UserConfig
from app.models.schemas import UserConfigCreate, UserConfigUpdate
from app.utils.encryption import encryption_service
from typing import Optional

class UserConfigService:
    @staticmethod
    def get_user_config(db: Session, user_id: int) -> Optional[UserConfig]:
        """Get user configuration."""
        return db.query(UserConfig).filter(UserConfig.user_id == user_id).first()
    
    @staticmethod
    def create_or_update_config(db: Session, user_id: int, config_data: UserConfigCreate) -> UserConfig:
        """Create or update user configuration."""
        user_config = db.query(UserConfig).filter(UserConfig.user_id == user_id).first()
        
        if not user_config:
            user_config = UserConfig(user_id=user_id)
            db.add(user_config)
        
        # Update config fields
        user_config.cv_folder_name = config_data.cv_folder_name
        
        # Encrypt and store OpenAI API key
        if config_data.openai_api_key:
            user_config.openai_api_key = encryption_service.encrypt(config_data.openai_api_key)
        
        # Check if setup is complete
        user_config.is_setup_complete = (
            user_config.google_drive_token is not None and 
            user_config.openai_api_key is not None
        )
        
        db.commit()
        db.refresh(user_config)
        return user_config
    
    @staticmethod
    def update_config(db: Session, user_id: int, config_update: UserConfigUpdate) -> Optional[UserConfig]:
        """Update user configuration."""
        user_config = db.query(UserConfig).filter(UserConfig.user_id == user_id).first()
        if not user_config:
            return None
        
        # Update fields if provided
        if config_update.cv_folder_name is not None:
            user_config.cv_folder_name = config_update.cv_folder_name
        
        if config_update.openai_api_key is not None:
            user_config.openai_api_key = encryption_service.encrypt(config_update.openai_api_key)
        
        # Check if setup is complete
        user_config.is_setup_complete = (
            user_config.google_drive_token is not None and 
            user_config.openai_api_key is not None
        )
        
        db.commit()
        db.refresh(user_config)
        return user_config
    
    @staticmethod
    def is_setup_complete(db: Session, user_id: int) -> bool:
        """Check if user setup is complete."""
        user_config = db.query(UserConfig).filter(UserConfig.user_id == user_id).first()
        return user_config and user_config.is_setup_complete
    
    @staticmethod
    def get_decrypted_openai_key(db: Session, user_id: int) -> Optional[str]:
        """Get decrypted OpenAI API key for user."""
        user_config = db.query(UserConfig).filter(UserConfig.user_id == user_id).first()
        if not user_config or not user_config.openai_api_key:
            return None
        
        return encryption_service.decrypt(user_config.openai_api_key)

user_config_service = UserConfigService()
