from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.models import User, UserConfig
from app.models.schemas import UserCreate, UserLogin
from app.utils import verify_password, get_password_hash, create_access_token
from typing import Optional

class AuthService:
    @staticmethod
    def create_user(db: Session, user: UserCreate) -> User:
        """Create a new user."""
        # Check if user already exists
        db_user = db.query(User).filter(
            (User.username == user.username) | (User.email == user.email)
        ).first()
        
        if db_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username or email already registered"
            )
        
        # Create new user
        hashed_password = get_password_hash(user.password)
        db_user = User(
            username=user.username,
            email=user.email,
            hashed_password=hashed_password
        )
        
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        # Create user config
        user_config = UserConfig(user_id=db_user.id)
        db.add(user_config)
        db.commit()
        
        return db_user
    
    @staticmethod
    def authenticate_user(db: Session, user_login: UserLogin) -> Optional[User]:
        """Authenticate user login."""
        user = db.query(User).filter(User.username == user_login.username).first()
        if not user or not verify_password(user_login.password, user.hashed_password):
            return None
        return user
    
    @staticmethod
    def get_user_by_username(db: Session, username: str) -> Optional[User]:
        """Get user by username."""
        return db.query(User).filter(User.username == username).first()
    
    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
        """Get user by ID."""
        return db.query(User).filter(User.id == user_id).first()
    
    @staticmethod
    def create_access_token_for_user(user: User) -> str:
        """Create access token for user."""
        return create_access_token(data={"sub": user.username})

auth_service = AuthService()
