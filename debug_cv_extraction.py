#!/usr/bin/env python3
"""
Debug CV text extraction to see why OpenAI analysis is failing
"""

import sys
sys.path.append('/Users/sanaalishah/Desktop/AI-projects/cv-matcher-agent')

from app.models.database import SessionLocal
from app.services.google_drive_service import google_drive_service
from app.services.user_config_service import user_config_service

try:
    from app.utils.document_parser import document_parser
except ImportError:
    from app.utils.simple_document_parser import simple_document_parser as document_parser

def debug_cv_extraction():
    """Debug what's happening with CV text extraction."""
    
    db = SessionLocal()
    user_id = 4  # Sana user
    
    try:
        print("🔍 Debugging CV Text Extraction...")
        
        # Get user config
        user_config = user_config_service.get_user_config(db, user_id)
        if not user_config:
            print("❌ No user config found")
            return
            
        # Get CV files from Google Drive
        cv_folder = user_config.cv_folder_name or "cvs"
        print(f"📁 Looking for files in folder: {cv_folder}")
        
        files = google_drive_service.list_files_in_folder(db, user_id, cv_folder)
        print(f"📄 Found {len(files)} files")
        
        if not files:
            print("❌ No CV files found")
            return
            
        # Test first few CV files
        for i, cv_file in enumerate(files[:2]):  # Test first 2 CVs
            print(f"\n📋 Testing CV {i+1}: {cv_file['name']}")
            
            try:
                # Download file content
                print("  📥 Downloading file...")
                file_content = google_drive_service.download_file(db, user_id, cv_file['id'])
                
                if not file_content:
                    print("  ❌ No file content received")
                    continue
                    
                print(f"  ✅ Downloaded {len(file_content)} bytes")
                
                # Extract text
                print("  📝 Extracting text...")
                cv_text = document_parser.extract_text_from_file(file_content, cv_file['name'])
                
                if not cv_text:
                    print("  ❌ No text extracted")
                    continue
                    
                print(f"  ✅ Extracted {len(cv_text)} characters")
                print(f"  📄 First 200 chars: {cv_text[:200]}...")
                
                # Check if text is reasonable
                if len(cv_text) < 100:
                    print("  ⚠️  Text too short - might cause OpenAI to fail")
                elif not any(word in cv_text.lower() for word in ['experience', 'skill', 'work', 'education', 'developer', 'engineer']):
                    print("  ⚠️  Text doesn't look like a CV - might cause OpenAI issues")
                else:
                    print("  ✅ Text looks like a proper CV")
                    
                # Test OpenAI analysis on this text
                print("  🤖 Testing OpenAI analysis...")
                from app.utils.universal_matcher import universal_matcher
                
                cv_profile = universal_matcher.extract_cv_profile_ai(cv_text, db, user_id)
                candidate_name = cv_profile.get('candidate_name', 'Not extracted')
                
                if candidate_name == 'Unknown Candidate':
                    print("  ❌ OpenAI analysis FAILED - falling back to basic extraction")
                    print("  💡 This explains why you see 'Unknown Candidate' in frontend")
                else:
                    print(f"  ✅ OpenAI analysis SUCCESS - extracted: {candidate_name}")
                    
            except Exception as e:
                print(f"  ❌ Error processing {cv_file['name']}: {e}")
                import traceback
                traceback.print_exc()
                
    finally:
        db.close()

if __name__ == "__main__":
    debug_cv_extraction()