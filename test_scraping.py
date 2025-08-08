#!/usr/bin/env python3
"""
Test the scraping service directly to see if it can extract the 9 jobs
"""
import asyncio
import sys
sys.path.append('/Users/sanaalishah/Desktop/AI-projects/cv-matcher-agent')

from app.services.career_page_scraping_service import CareerPageScrapingService
from app.models.models import CareerPageConfig
from datetime import datetime

async def test_scraping():
    print("🧪 Testing scraping service directly...")
    
    # Create a mock config object with your URL
    config = CareerPageConfig(
        id=1,
        user_id=1,
        company_name="Technology Rivers",
        career_url="https://technologyrivers.zohorecruit.com/jobs/Careers",
        scrape_frequency=24,
        scraping_rules=None,
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    # Create scraping service
    service = CareerPageScrapingService()
    
    # Test scraping
    print(f"📡 Scraping: {config.career_url}")
    result = await service.scrape_career_page(config)
    
    # Print results
    print(f"\n✅ Success: {result['success']}")
    print(f"📊 Jobs Found: {result['jobs_found']}")
    
    if result['success'] and result['jobs']:
        print(f"\n🎯 Job Details:")
        for i, job in enumerate(result['jobs'], 1):
            print(f"\n--- Job {i} ---")
            print(f"Title: {job.get('title', 'N/A')}")
            print(f"Location: {job.get('location', 'N/A')}")
            print(f"URL: {job.get('url', 'N/A')}")
            print(f"Type: {job.get('job_type', 'N/A')}")
            print(f"Posted: {job.get('posted_date_str', 'N/A')}")
            print(f"Summary: {job.get('description', 'N/A')[:100]}...")
    else:
        print(f"\n❌ Error: {result.get('error', 'Unknown error')}")
        if result.get('jobs'):
            print(f"Jobs data: {result['jobs']}")

if __name__ == "__main__":
    asyncio.run(test_scraping())