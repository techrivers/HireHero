#!/usr/bin/env python3
"""
Simple test using your exact working code
"""
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import time

BASE_URL = "https://technologyrivers.zohorecruit.com/jobs/Careers"

def create_driver():
    options = Options()
    options.add_argument("--headless")  
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    return webdriver.Chrome(options=options)

def test_scraping():
    print("🧪 Testing your exact working scraping code...")
    
    try:
        driver = create_driver()
        print("✅ Chrome driver created successfully")
        
        print(f"📡 Loading: {BASE_URL}")
        driver.get(BASE_URL)
        time.sleep(5)  # wait for JS to load
        print("✅ Page loaded")

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        driver.quit()

        job_elements = soup.select('.cw-filter-joblist')
        print(f"🟢 Found {len(job_elements)} job(s)")

        for i, job_el in enumerate(job_elements, 1):
            title_el = job_el.select_one('a.cw-3-title')
            if title_el:
                print(f"Job {i}: {title_el.get_text(strip=True)}")
            else:
                print(f"Job {i}: No title found")

        return len(job_elements)
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return 0

if __name__ == "__main__":
    job_count = test_scraping()
    print(f"\n🎯 Final result: {job_count} jobs found")
    
    if job_count == 0:
        print("❌ PROBLEM: No jobs found - something is broken")
    elif job_count < 5:
        print("⚠️  WARNING: Few jobs found - may not be working properly") 
    else:
        print("✅ SUCCESS: Found multiple jobs - scraping is working!")