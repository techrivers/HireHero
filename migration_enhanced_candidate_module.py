#!/usr/bin/env python3
"""
Database Migration Script for Enhanced Candidate Module
This script creates the new tables needed for the enhanced candidate module.
Run this script to add the new tables to your existing database.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.models.database import engine, Base
from app.models.models import (
    User, UserConfig, MatchLog, MatchResult, ChatConversation, ChatMessage,
    # New models
    Job, Candidate, JobMatch, CareerPageConfig, RefreshSchedule
)
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_new_tables():
    """Create only the new tables for the enhanced candidate module"""
    try:
        logger.info("Creating new tables for enhanced candidate module...")
        
        # Create all tables - SQLAlchemy will only create tables that don't exist
        Base.metadata.create_all(bind=engine)
        
        logger.info("Successfully created new tables:")
        logger.info("- jobs")
        logger.info("- candidates") 
        logger.info("- job_matches")
        logger.info("- career_page_configs")
        logger.info("- refresh_schedules")
        
        return True
        
    except Exception as e:
        logger.error(f"Error creating tables: {str(e)}")
        return False

def verify_tables_exist():
    """Verify that all new tables were created successfully"""
    from sqlalchemy import inspect
    
    try:
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        
        required_tables = [
            'jobs',
            'candidates', 
            'job_matches',
            'career_page_configs',
            'refresh_schedules'
        ]
        
        missing_tables = [table for table in required_tables if table not in existing_tables]
        
        if missing_tables:
            logger.error(f"Missing tables: {missing_tables}")
            return False
        else:
            logger.info("All required tables exist!")
            logger.info(f"Current tables: {existing_tables}")
            return True
            
    except Exception as e:
        logger.error(f"Error verifying tables: {str(e)}")
        return False

def add_sample_data():
    """Add some sample data for testing (optional)"""
    from sqlalchemy.orm import sessionmaker
    
    try:
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Add a sample job
        sample_job = Job(
            title="Senior Software Engineer",
            company="Tech Corp",
            description="We are looking for an experienced software engineer...",
            required_skills=["Python", "FastAPI", "PostgreSQL", "React"],
            experience_level="senior",
            location="Remote",
            remote_friendly=True,
            status="active"
        )
        
        session.add(sample_job)
        session.commit()
        
        logger.info("Added sample job data")
        session.close()
        
        return True
        
    except Exception as e:
        logger.error(f"Error adding sample data: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info("Starting Enhanced Candidate Module Migration")
    
    # Step 1: Create new tables
    if not create_new_tables():
        logger.error("Failed to create new tables. Exiting.")
        sys.exit(1)
    
    # Step 2: Verify tables exist
    if not verify_tables_exist():
        logger.error("Table verification failed. Exiting.")
        sys.exit(1)
    
    # Step 3: Add sample data for testing
    logger.info("Adding sample data for testing...")
    add_sample_data()
    
    logger.info("Migration completed successfully!")
    logger.info("The enhanced candidate module database schema is now ready.")