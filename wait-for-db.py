#!/usr/bin/env python3
"""
Wait for database to be ready before starting the application
"""

import time
import sys
import os
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from dotenv import load_dotenv

load_dotenv()

def wait_for_db():
    """Wait for database to be ready."""
    database_url = os.getenv("DATABASE_URL", "postgresql://cvmatcher:securepassword@db:5432/cvmatcher_db")
    
    print("🔄 Waiting for database to be ready...")
    
    max_retries = 30
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            engine = create_engine(database_url)
            # Try to connect
            with engine.connect() as conn:
                print("✅ Database is ready!")
                return True
        except OperationalError as e:
            retry_count += 1
            print(f"⏳ Database not ready yet (attempt {retry_count}/{max_retries}). Waiting...")
            time.sleep(2)
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            retry_count += 1
            time.sleep(2)
    
    print("❌ Database connection timeout!")
    return False

if __name__ == "__main__":
    if wait_for_db():
        sys.exit(0)
    else:
        sys.exit(1)