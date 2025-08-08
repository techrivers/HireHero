#!/usr/bin/env python3
"""
Setup script for Enhanced Candidate Module
Runs database migration and basic validation
"""

import sys
import os
import subprocess
import asyncio
from datetime import datetime

# Add the app directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def print_header(text):
    """Print a formatted header"""
    print(f"\n{'='*60}")
    print(f"🚀 {text}")
    print(f"{'='*60}\n")

def print_step(step_num, total_steps, description):
    """Print a formatted step"""
    print(f"📋 Step {step_num}/{total_steps}: {description}")

def run_migration():
    """Run the database migration"""
    print_step(1, 4, "Running Database Migration")
    
    try:
        # Import and run migration
        from migration_enhanced_candidate_module import (
            create_new_tables, verify_tables_exist, add_sample_data
        )
        
        print("🔧 Creating new database tables...")
        if create_new_tables():
            print("✅ Tables created successfully")
        else:
            print("❌ Failed to create tables")
            return False
        
        print("🔍 Verifying tables exist...")
        if verify_tables_exist():
            print("✅ All tables verified")
        else:
            print("❌ Table verification failed")
            return False
        
        print("📊 Adding sample data...")
        if add_sample_data():
            print("✅ Sample data added")
        else:
            print("⚠️  Failed to add sample data (this is optional)")
        
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        return False

def validate_dependencies():
    """Validate that all required dependencies are installed"""
    print_step(2, 4, "Validating Dependencies")
    
    required_packages = [
        'fastapi', 'sqlalchemy', 'aiohttp', 'bs4', 
        'openai', 'asyncio', 'pydantic'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} - MISSING")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n⚠️  Missing packages: {', '.join(missing_packages)}")
        print("💡 Install missing packages with: pip install -r requirements.txt")
        return False
    
    print("✅ All dependencies satisfied")
    return True

def test_service_imports():
    """Test that all new services can be imported"""
    print_step(3, 4, "Testing Service Imports")
    
    services = [
        ('JobManagementService', 'app.services.job_management_service'),
        ('EnhancedCandidateService', 'app.services.enhanced_candidate_service'),
        ('IntelligentMatchingService', 'app.services.intelligent_matching_service'),
        ('CareerPageScrapingService', 'app.services.career_page_scraping_service')
    ]
    
    for service_name, module_path in services:
        try:
            module = __import__(module_path, fromlist=[service_name])
            service_class = getattr(module, service_name)
            # Try to instantiate
            service_instance = service_class()
            print(f"✅ {service_name}")
        except Exception as e:
            print(f"❌ {service_name} - Error: {str(e)}")
            return False
    
    print("✅ All services imported successfully")
    return True

def validate_api_routes():
    """Validate that all new API routes are properly configured"""
    print_step(4, 4, "Validating API Routes")
    
    try:
        from app.main import app
        
        # Get all routes
        routes = []
        for route in app.routes:
            if hasattr(route, 'path'):
                routes.append(route.path)
        
        expected_routes = [
            '/api/jobs/',
            '/api/candidates/',
            '/api/career-pages/',
            '/api/matching/'
        ]
        
        for expected_route in expected_routes:
            if any(expected_route in route for route in routes):
                print(f"✅ {expected_route}")
            else:
                print(f"❌ {expected_route} - MISSING")
                return False
        
        print("✅ All API routes configured")
        return True
        
    except Exception as e:
        print(f"❌ Route validation failed: {str(e)}")
        return False

def display_next_steps():
    """Display next steps for the user"""
    print_header("🎉 Setup Complete!")
    
    print("📋 Next Steps:")
    print("1. 🚀 Start the FastAPI server:")
    print("   python -m app.main")
    print()
    print("2. 🌐 Access the API documentation:")
    print("   http://localhost:8000/docs")
    print()
    print("3. 🧪 Run comprehensive tests:")
    print("   python test_enhanced_candidate_module.py")
    print()
    print("4. 💡 Key new endpoints to try:")
    print("   - POST /api/jobs/ - Create job postings")
    print("   - GET /api/candidates/ - List candidates")
    print("   - POST /api/career-pages/ - Add career page configs")
    print("   - POST /api/matching/candidate/{id}/jobs - Match candidates to jobs")
    print()
    print("5. 🎯 Features now available:")
    print("   - AI-powered job posting management")
    print("   - Advanced candidate profiling")
    print("   - Intelligent job-candidate matching")
    print("   - Career page scraping")
    print("   - Natural language candidate search")
    print()
    print("🔗 Documentation:")
    print("   - API Docs: http://localhost:8000/docs")
    print("   - Alternative Docs: http://localhost:8000/redoc")

async def main():
    """Main setup function"""
    print_header("Enhanced Candidate Module Setup")
    print(f"🕒 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    steps = [
        ("Database Migration", run_migration),
        ("Dependencies Validation", validate_dependencies),
        ("Service Imports", test_service_imports),
        ("API Routes", validate_api_routes)
    ]
    
    all_passed = True
    
    for step_name, step_function in steps:
        try:
            if not step_function():
                print(f"❌ {step_name} failed")
                all_passed = False
                break
        except Exception as e:
            print(f"❌ {step_name} failed with exception: {str(e)}")
            all_passed = False
            break
    
    if all_passed:
        display_next_steps()
        print("🏆 Enhanced Candidate Module is ready to use!")
        return 0
    else:
        print("\n❌ Setup failed. Please resolve the issues above.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)