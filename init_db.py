#!/usr/bin/env python3
"""
Database initialization and seeding script for Resume Matcher Agent
"""

import os
import sys
from pathlib import Path

# Add the app directory to Python path
app_dir = Path(__file__).parent / "app"
sys.path.insert(0, str(app_dir))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.database import Base
from app.models.models import User, UserConfig
from app.utils.auth import get_password_hash
from dotenv import load_dotenv

load_dotenv()

def create_database():
    """Create database tables."""
    database_url = os.getenv("DATABASE_URL", "postgresql://cvmatcher:securepassword@localhost:5432/cvmatcher_db")
    engine = create_engine(database_url)
    
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully")
    
    return engine

def seed_users(engine):
    """Seed database with initial users."""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # Check if users already exist
        if db.query(User).first():
            print("ℹ️  Users already exist, skipping seeding")
            return
        
        print("Seeding initial users...")
        
        # Create demo users
        demo_users = [
            {
                "username": "admin",
                "email": "admin@cvmatcher.com",
                "password": "admin123"
            },
            {
                "username": "demo",
                "email": "demo@cvmatcher.com", 
                "password": "demo123"
            },
            {
                "username": "testuser",
                "email": "test@cvmatcher.com",
                "password": "test123"
            }
        ]
        
        for user_data in demo_users:
            # Create user
            user = User(
                username=user_data["username"],
                email=user_data["email"],
                hashed_password=get_password_hash(user_data["password"])
            )
            db.add(user)
            db.flush()  # Get the user ID
            
            # Create user config
            user_config = UserConfig(
                user_id=user.id,
                cv_folder_name="cvs"
            )
            db.add(user_config)
            
            print(f"✅ Created user: {user_data['username']} (password: {user_data['password']})")
        
        db.commit()
        print("✅ Database seeded successfully")
        
    except Exception as e:
        print(f"❌ Error seeding database: {e}")
        db.rollback()
    finally:
        db.close()

def main():
    """Main function."""
    print("🚀 Resume Matcher Agent Database Setup")
    print("==================================")
    
    try:
        engine = create_database()
        seed_users(engine)
        
        print("\n🎉 Database setup completed!")
        print("\nDemo user accounts:")
        print("- Username: admin, Password: admin123")
        print("- Username: demo, Password: demo123") 
        print("- Username: testuser, Password: test123")
        print("\nYou can now start the application and login with these credentials.")
        
    except Exception as e:
        print(f"❌ Database setup failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
