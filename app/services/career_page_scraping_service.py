import aiohttp
import asyncio
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
import json
import logging
from urllib.parse import urljoin, urlparse
import re
from datetime import datetime, timedelta
import time
from sqlalchemy.orm import Session
from ..models.models import Job, CareerPageConfig
from ..models.database import get_db

logger = logging.getLogger(__name__)

# Import Selenium for JavaScript-heavy pages
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.webdriver.chrome.service import Service
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    logger.warning("Selenium not available - JavaScript-heavy pages may not work properly")

class CareerPageScrapingService:
    """
    Service for scraping job postings from company career pages.
    Supports multiple common career page formats and can be configured
    with custom scraping rules.
    """
    
    def __init__(self):
        self.session_timeout = aiohttp.ClientTimeout(total=30)
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        # Create SSL context that's more permissive for development
        import ssl
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE
    
    def _create_selenium_driver(self):
        """Create a WebDriver for JavaScript-heavy pages (Chrome first, then Safari)"""
        if not SELENIUM_AVAILABLE:
            return None
        
        # Try Chrome first as it's more reliable
        try:
            logger.info("Attempting to use Chrome WebDriver...")
            options = Options()
            options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--disable-web-security")
            options.add_argument("--disable-features=VizDisplayCompositor")
            options.add_argument("--window-size=1920,1080")
            options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            
            # Check if running in Docker container (use system chromium)
            import os
            import subprocess
            
            # First try to use system chromium-driver if available
            try:
                chromium_path = subprocess.check_output(['which', 'chromium'], text=True).strip()
                chromedriver_path = subprocess.check_output(['which', 'chromedriver'], text=True).strip()
                options.binary_location = chromium_path
                service = Service(chromedriver_path)
                logger.info(f"Using system Chromium: {chromium_path} with driver: {chromedriver_path}")
            except (subprocess.CalledProcessError, FileNotFoundError):
                # Fallback to environment variables if set
                if os.environ.get('CHROME_BIN'):
                    options.binary_location = os.environ.get('CHROME_BIN')
                    service = Service(os.environ.get('CHROMEDRIVER_PATH', '/usr/bin/chromedriver'))
                    logger.info("Using environment variable Chrome/Chromium")
                else:
                    # Final fallback to webdriver-manager
                    service = Service(ChromeDriverManager().install())
                    logger.info("Using webdriver-manager for Chrome")
            
            driver = webdriver.Chrome(service=service, options=options)
            driver.set_page_load_timeout(30)
            return driver
        except Exception as e:
            logger.warning(f"Chrome WebDriver failed: {str(e)}")
        
        # Fallback to Safari (if properly configured)
        try:
            logger.info("Attempting to use Safari WebDriver...")
            driver = webdriver.Safari()
            driver.set_page_load_timeout(30)
            return driver
        except Exception as e:
            logger.warning(f"Safari WebDriver not available: {str(e)}")
            
        return None
    
    async def scrape_career_page(self, config: CareerPageConfig) -> Dict[str, Any]:
        """
        Scrape jobs from a career page based on configuration.
        
        Args:
            config: CareerPageConfig object with scraping details
            
        Returns:
            Dict with scraping results and statistics
        """
        try:
            connector = aiohttp.TCPConnector(ssl=self.ssl_context)
            async with aiohttp.ClientSession(
                timeout=self.session_timeout,
                headers=self.headers,
                connector=connector
            ) as session:
                # Fetch the career page
                async with session.get(config.career_url) as response:
                    if response.status != 200:
                        raise Exception(f"HTTP {response.status}: {await response.text()}")
                    
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Extract jobs using configuration rules or default patterns
                    jobs = await self._extract_jobs_from_soup(
                        soup, config.career_url, config.scraping_rules or {}
                    )
                    
                    return {
                        'success': True,
                        'jobs_found': len(jobs),
                        'jobs': jobs,
                        'scraped_at': datetime.utcnow().isoformat(),
                        'source_url': config.career_url
                    }
                    
        except Exception as e:
            logger.error(f"Error scraping {config.career_url}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'jobs_found': 0,
                'jobs': [],
                'scraped_at': datetime.utcnow().isoformat()
            }
    
    async def _extract_jobs_from_soup(self, soup: BeautifulSoup, base_url: str, rules: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract job listings from BeautifulSoup object using rules or default patterns"""
        jobs = []
        
        # Try custom rules first
        if rules and 'job_selector' in rules:
            jobs = await self._extract_with_custom_rules(soup, base_url, rules)
        
        # Fallback to common patterns if no custom rules or no results
        if not jobs:
            jobs = await self._extract_with_common_patterns(soup, base_url)
            
        return jobs
    
    async def _extract_with_custom_rules(self, soup: BeautifulSoup, base_url: str, rules: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract jobs using custom scraping rules"""
        jobs = []
        
        try:
            job_elements = soup.select(rules['job_selector'])
            logger.info(f"Found {len(job_elements)} job elements using custom rules")
            
            for element in job_elements:
                job_data = {
                    'source_url': base_url,
                    'scraped_at': datetime.utcnow()
                }
                
                # Extract title
                if 'title_selector' in rules:
                    title_elem = element.select_one(rules['title_selector'])
                    job_data['title'] = title_elem.get_text(strip=True) if title_elem else 'Unknown Title'
                
                # Extract description/summary
                if 'description_selector' in rules:
                    desc_elem = element.select_one(rules['description_selector'])
                    job_data['description'] = desc_elem.get_text(strip=True) if desc_elem else ''
                
                # Extract location
                if 'location_selector' in rules:
                    loc_elem = element.select_one(rules['location_selector'])
                    job_data['location'] = loc_elem.get_text(strip=True) if loc_elem else ''
                
                # Extract job URL
                if 'url_selector' in rules:
                    url_elem = element.select_one(rules['url_selector'])
                    if url_elem:
                        href = url_elem.get('href')
                        job_data['url'] = urljoin(base_url, href) if href else ''
                
                # Extract posted date
                if 'date_selector' in rules:
                    date_elem = element.select_one(rules['date_selector'])
                    if date_elem:
                        job_data['posted_date'] = self._parse_date(date_elem.get_text(strip=True))
                
                # **NEW: Fetch full job description from individual job page**
                if job_data.get('url') and job_data['url'] != base_url:
                    try:
                        full_description = await self._fetch_full_job_description(job_data['url'])
                        if full_description:
                            job_data['full_description'] = full_description
                            job_data['description'] = full_description[:500] + "..." if len(full_description) > 500 else full_description
                    except Exception as e:
                        logger.warning(f"Could not fetch full description for {job_data['url']}: {str(e)}")
                
                # Only add job if we have at least a title
                if job_data.get('title') and job_data['title'] != 'Unknown Title':
                    jobs.append(job_data)
                    
        except Exception as e:
            logger.error(f"Error with custom rules: {str(e)}")
            
        return jobs
    
    async def _extract_with_common_patterns(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, Any]]:
        """Extract jobs using common career page patterns"""
        jobs = []
        
        # First, check if this is a dynamic content page (Zoho, Workday, etc.)
        if self._is_dynamic_content_page(soup):
            logger.info("Detected dynamic content page, using intelligent extraction")
            jobs = await self._extract_from_dynamic_page(base_url)
        
        # If dynamic extraction didn't work, try common patterns
        if not jobs:
            # Common selectors for different career page platforms
            common_patterns = [
                # Zoho Recruit patterns (after JS load)
                {
                    'job_selector': 'ul.rec-job-info li, .job-listing-item, .rec-job-item',
                    'title_selector': '.zrsite_Job_Title, .job-title, h3, h4',
                    'location_selector': '.zrsite_City, .location, .job-location',
                    'url_selector': 'a'
                },
                # Lever.co patterns
                {
                    'job_selector': '.posting',
                    'title_selector': '.posting-title h5',
                    'location_selector': '.posting-categories .location',
                    'url_selector': 'a'
                },
                # Greenhouse patterns
                {
                    'job_selector': '.opening',
                    'title_selector': '.opening-title a',
                    'location_selector': '.opening-location',
                    'url_selector': '.opening-title a'
                },
                # Workday patterns
                {
                    'job_selector': '[data-automation-id="jobTitle"]',
                    'title_selector': 'a',
                    'location_selector': '[data-automation-id="locations"]',
                    'url_selector': 'a'
                },
                # Generic patterns
                {
                    'job_selector': '.job, .position, .opening, .career-item',
                    'title_selector': 'h1, h2, h3, h4, .title, .job-title',
                    'location_selector': '.location, .job-location',
                    'url_selector': 'a'
                }
            ]
            
            for pattern in common_patterns:
                try:
                    extracted = await self._extract_with_custom_rules(soup, base_url, pattern)
                    if extracted:
                        jobs.extend(extracted)
                        break  # Stop at first successful pattern
                except:
                    continue
        
        # Additional fallback: look for any links that might be job postings
        if not jobs:
            jobs = await self._extract_job_links_fallback(soup, base_url)
            
        return jobs
    
    async def _extract_job_links_fallback(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, Any]]:
        """Fallback method to find job-related links"""
        jobs = []
        job_keywords = ['job', 'position', 'career', 'opening', 'role', 'opportunity']
        
        # Find links that might be job postings
        for link in soup.find_all('a', href=True):
            link_text = link.get_text(strip=True).lower()
            href = link.get('href')
            
            # Check if link text contains job-related keywords
            if any(keyword in link_text for keyword in job_keywords):
                jobs.append({
                    'title': link.get_text(strip=True),
                    'url': urljoin(base_url, href),
                    'description': '',
                    'location': '',
                    'source_url': base_url,
                    'scraped_at': datetime.utcnow()
                })
        
        return jobs[:20]  # Limit to 20 to avoid spam
    
    def _parse_date(self, date_string: str) -> Optional[datetime]:
        """Parse various date formats commonly found on career pages"""
        if not date_string:
            return None
            
        date_string = date_string.lower().strip()
        
        try:
            # Handle relative dates
            if 'ago' in date_string:
                if 'day' in date_string:
                    days = int(re.search(r'(\d+)', date_string).group(1))
                    return datetime.utcnow() - timedelta(days=days)
                elif 'week' in date_string:
                    weeks = int(re.search(r'(\d+)', date_string).group(1))
                    return datetime.utcnow() - timedelta(weeks=weeks)
                elif 'month' in date_string:
                    months = int(re.search(r'(\d+)', date_string).group(1))
                    return datetime.utcnow() - timedelta(days=months*30)
            
            # Handle absolute dates (you can extend this with more formats)
            date_formats = [
                '%Y-%m-%d',
                '%m/%d/%Y',
                '%d/%m/%Y',
                '%B %d, %Y',
                '%b %d, %Y',
            ]
            
            for fmt in date_formats:
                try:
                    return datetime.strptime(date_string, fmt)
                except ValueError:
                    continue
                    
        except Exception as e:
            logger.debug(f"Could not parse date '{date_string}': {str(e)}")
            
        return None
    
    async def save_jobs_to_database(self, jobs: List[Dict[str, Any]], company_name: str, db: Session) -> Dict[str, int]:
        """Save scraped jobs to the database with AI analysis"""
        stats = {
            'created': 0,
            'updated': 0,
            'skipped': 0
        }
        
        try:
            # First enhance jobs with AI analysis
            enhanced_jobs = await self._analyze_jobs_with_ai(jobs, db)
            
            for job_data in enhanced_jobs:
                # Check if job already exists (by title and company)
                existing_job = db.query(Job).filter(
                    Job.title == job_data.get('title'),
                    Job.company == company_name
                ).first()
                
                if existing_job:
                    # Update existing job with enhanced data
                    existing_job.description = job_data.get('full_description') or job_data.get('description', existing_job.description)
                    existing_job.location = job_data.get('location', existing_job.location)
                    existing_job.url = job_data.get('url', existing_job.url)
                    existing_job.experience_level = job_data.get('experience_level', existing_job.experience_level)
                    existing_job.remote_friendly = job_data.get('remote_friendly', existing_job.remote_friendly)
                    existing_job.required_skills = job_data.get('ai_parsed_requirements', existing_job.required_skills or [])
                    existing_job.updated_at = datetime.utcnow()
                    stats['updated'] += 1
                else:
                    # Create new job with enhanced data
                    new_job = Job(
                        title=job_data.get('title', 'Unknown Title'),
                        company=company_name,
                        description=job_data.get('full_description') or job_data.get('description', ''),
                        url=job_data.get('url', ''),
                        location=job_data.get('location', ''),
                        posted_date=job_data.get('posted_date'),
                        scrape_source=job_data.get('source_url'),
                        required_skills=job_data.get('ai_parsed_requirements', []),
                        experience_level=job_data.get('experience_level', 'Mid-Level'),
                        remote_friendly=job_data.get('remote_friendly', False),
                        status='active'
                    )
                    db.add(new_job)
                    stats['created'] += 1
            
            db.commit()
            logger.info(f"Saved jobs to database: {stats}")
            
        except Exception as e:
            logger.error(f"Error saving jobs to database: {str(e)}")
            db.rollback()
            
        return stats
    
    async def scrape_and_save_all_configured_pages(self, user_id: int, db: Session) -> Dict[str, Any]:
        """Scrape all active career pages for a user and save results"""
        configs = db.query(CareerPageConfig).filter(
            CareerPageConfig.user_id == user_id,
            CareerPageConfig.is_active == True
        ).all()
        
        results = {
            'total_configs': len(configs),
            'successful_scrapes': 0,
            'failed_scrapes': 0,
            'total_jobs_found': 0,
            'details': []
        }
        
        for config in configs:
            scrape_result = await self.scrape_career_page(config)
            
            if scrape_result['success']:
                # Save jobs to database
                save_stats = await self.save_jobs_to_database(
                    scrape_result['jobs'], config.company_name, db
                )
                
                # Update config
                config.last_scraped = datetime.utcnow()
                config.last_success = True
                config.jobs_found_count = scrape_result['jobs_found']
                config.error_message = None
                
                results['successful_scrapes'] += 1
                results['total_jobs_found'] += scrape_result['jobs_found']
                
                results['details'].append({
                    'company': config.company_name,
                    'status': 'success',
                    'jobs_found': scrape_result['jobs_found'],
                    'save_stats': save_stats
                })
                
            else:
                # Update config with error
                config.last_scraped = datetime.utcnow()
                config.last_success = False
                config.error_message = scrape_result['error']
                
                results['failed_scrapes'] += 1
                
                results['details'].append({
                    'company': config.company_name,
                    'status': 'failed',
                    'error': scrape_result['error']
                })
        
        db.commit()
        return results
    
    async def _fetch_full_job_description(self, job_url: str) -> Optional[str]:
        """Fetch full job description from individual job posting page"""
        try:
            connector = aiohttp.TCPConnector(ssl=self.ssl_context)
            async with aiohttp.ClientSession(
                timeout=self.session_timeout,
                headers=self.headers,
                connector=connector
            ) as session:
                async with session.get(job_url) as response:
                    if response.status != 200:
                        return None
                    
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Try multiple selectors to find job description
                    description_selectors = [
                        '.job-description',
                        '.job-content',
                        '.position-description',
                        '.job-details',
                        '[class*="description"]',
                        '[class*="content"]',
                        'main',
                        '.content',
                        'article'
                    ]
                    
                    for selector in description_selectors:
                        desc_elem = soup.select_one(selector)
                        if desc_elem:
                            # Clean up the text
                            description = desc_elem.get_text(separator=' ', strip=True)
                            if len(description) > 100:  # Must be substantial
                                return description
                    
                    # Fallback: get main content from body
                    body = soup.find('body')
                    if body:
                        description = body.get_text(separator=' ', strip=True)
                        if len(description) > 100:
                            return description[:2000]  # Limit length
                    
                    return None
                    
        except Exception as e:
            logger.warning(f"Error fetching job description from {job_url}: {str(e)}")
            return None
    
    async def _analyze_jobs_with_ai(self, jobs: List[Dict[str, Any]], db: Session) -> List[Dict[str, Any]]:
        """Analyze and enhance job data with AI"""
        try:
            # This would require OpenAI integration
            # For now, return jobs as-is but add some basic parsing
            enhanced_jobs = []
            
            for job in jobs:
                enhanced_job = job.copy()
                
                # Extract basic requirements from description
                description = job.get('full_description') or job.get('description', '')
                enhanced_job['ai_parsed_requirements'] = self._extract_requirements(description)
                enhanced_job['experience_level'] = self._determine_experience_level(description)
                enhanced_job['remote_friendly'] = self._check_remote_work(description)
                
                enhanced_jobs.append(enhanced_job)
            
            return enhanced_jobs
            
        except Exception as e:
            logger.error(f"Error analyzing jobs with AI: {str(e)}")
            return jobs
    
    def _extract_requirements(self, text: str) -> List[str]:
        """Basic extraction of job requirements"""
        requirements = []
        text_lower = text.lower()
        
        # Common skill patterns
        skill_patterns = [
            r'python', r'java', r'javascript', r'react', r'angular', r'vue',
            r'node\.?js', r'django', r'flask', r'spring', r'sql', r'mysql',
            r'postgresql', r'mongodb', r'aws', r'azure', r'docker', r'kubernetes',
            r'git', r'linux', r'html', r'css', r'typescript', r'php', r'c\+\+',
            r'machine learning', r'ai', r'data science', r'tensorflow', r'pytorch'
        ]
        
        for pattern in skill_patterns:
            if re.search(pattern, text_lower):
                # Capitalize first letter for display
                skill = pattern.replace(r'\.?\+', '+').replace('\\', '')
                requirements.append(skill.title())
        
        return list(set(requirements))[:10]  # Remove duplicates, limit to 10
    
    def _determine_experience_level(self, text: str) -> str:
        """Determine experience level from job description"""
        text_lower = text.lower()
        
        if any(term in text_lower for term in ['senior', 'lead', 'principal', '5+ years', '6+ years']):
            return 'Senior'
        elif any(term in text_lower for term in ['junior', 'entry level', '0-2 years', 'fresh graduate']):
            return 'Junior'
        elif any(term in text_lower for term in ['mid level', 'intermediate', '2-4 years', '3-5 years']):
            return 'Mid-Level'
        
        return 'Mid-Level'  # Default
    
    def _check_remote_work(self, text: str) -> bool:
        """Check if job allows remote work"""
        text_lower = text.lower()
        return any(term in text_lower for term in [
            'remote', 'work from home', 'distributed', 'anywhere', 'location independent'
        ])
    
    def _is_dynamic_content_page(self, soup: BeautifulSoup) -> bool:
        """Detect if this is a dynamic content page (Zoho, Workday, etc.)"""
        # Check for Zoho Recruit indicators
        zoho_indicators = [
            '#rec_job_listing_div',
            'rec_embed_js',
            'zoho',
            'recruit'
        ]
        
        # Check for Workday indicators
        workday_indicators = [
            'workday',
            '[data-automation-id',
            'wd-'
        ]
        
        # Check for other dynamic indicators
        dynamic_indicators = [
            'data-react',
            'ng-app',
            'vue-',
            'ember-'
        ]
        
        page_html = str(soup).lower()
        
        return any(indicator.lower() in page_html for indicator in 
                  zoho_indicators + workday_indicators + dynamic_indicators)
    
    async def _extract_from_dynamic_page(self, base_url: str) -> List[Dict[str, Any]]:
        """Extract jobs from dynamic content pages using intelligent approaches"""
        jobs = []
        
        # For Zoho Recruit, try to find the direct API or RSS feed
        if 'zoho' in base_url.lower() or await self._has_zoho_recruit(base_url):
            jobs = await self._extract_from_zoho_recruit(base_url)
        
        # If no jobs found, try to find any text that looks like job postings
        if not jobs:
            jobs = await self._extract_job_info_from_text(base_url)
        
        return jobs
    
    async def _has_zoho_recruit(self, url: str) -> bool:
        """Check if page uses Zoho Recruit"""
        try:
            connector = aiohttp.TCPConnector(ssl=self.ssl_context)
            async with aiohttp.ClientSession(
                timeout=self.session_timeout,
                headers=self.headers,
                connector=connector
            ) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        html = await response.text()
                        return any(term in html.lower() for term in [
                            'zoho', 'recruit', 'rec_embed_js', 'rec_job_listing'
                        ])
        except:
            pass
        return False
    
    async def _extract_from_zoho_recruit(self, base_url: str) -> List[Dict[str, Any]]:
        """Extract jobs from Zoho Recruit pages using Selenium for JavaScript content"""
        jobs = []
        
        try:
            logger.info("Attempting to extract from Zoho Recruit page using Selenium")
            
            # Try Selenium first for JavaScript content
            if SELENIUM_AVAILABLE:
                selenium_jobs = await self._extract_zoho_with_selenium(base_url)
                if selenium_jobs:
                    logger.info(f"Found {len(selenium_jobs)} jobs using Selenium")
                    return selenium_jobs
            
            # Fallback to regular HTTP request
            logger.info("Selenium extraction failed or unavailable, trying regular HTTP request")
            connector = aiohttp.TCPConnector(ssl=self.ssl_context)
            async with aiohttp.ClientSession(
                timeout=self.session_timeout,
                headers=self.headers,
                connector=connector
            ) as session:
                async with session.get(base_url) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        # Check for "no openings" message
                        if any(phrase in html.lower() for phrase in [
                            'no current openings', 'no openings', 'no positions', 
                            'no jobs available', 'no vacancies', 'currently no openings'
                        ]):
                            logger.info("No job openings currently available")
                            return []
                        
                        # Try to find any job-related content in the initial HTML
                        potential_jobs = await self._extract_zoho_static_content(soup, base_url)
                        if potential_jobs:
                            jobs.extend(potential_jobs)
                            logger.info(f"Found {len(potential_jobs)} jobs from static content")
                            return jobs
                        
                        # Try alternative approaches for dynamic content
                        logger.info("Zoho Recruit page detected - trying alternative extraction methods")
                        
                        # Try to find any text that looks like job titles
                        page_text = soup.get_text()
                        job_keywords = [
                            'software engineer', 'developer', 'analyst', 'manager',
                            'coordinator', 'specialist', 'consultant', 'architect',
                            'designer', 'intern', 'associate', 'director', 'lead'
                        ]
                        
                        # Look for patterns that might be job titles
                        import re
                        potential_jobs = []
                        lines = page_text.split('\n')
                        for line in lines:
                            line = line.strip()
                            if len(line) > 10 and len(line) < 100:
                                for keyword in job_keywords:
                                    if keyword.lower() in line.lower():
                                        potential_jobs.append({
                                            'title': line,
                                            'description': f'Position involving {keyword} responsibilities',
                                            'location': 'Location TBD',
                                            'url': base_url,
                                            'source_url': base_url,
                                            'scraped_at': datetime.utcnow(),
                                            'full_description': f'Job opportunity: {line}. Please visit the career page for full details.'
                                        })
                                        break
                        
                        if potential_jobs:
                            jobs.extend(potential_jobs[:10])  # Limit to 10 jobs
                            logger.info(f"Found {len(potential_jobs)} potential jobs from text analysis")
                        else:
                            # Fallback entry
                            jobs.append({
                                'title': 'Career Opportunities Available',
                                'description': 'Multiple job openings detected on this career page.',
                                'location': 'Various Locations',
                                'url': base_url,
                                'source_url': base_url,
                                'scraped_at': datetime.utcnow(),
                                'full_description': 'This career page contains job opportunities. Please visit the page directly for current openings.'
                            })
                        
        except Exception as e:
            logger.error(f"Error extracting from Zoho Recruit: {str(e)}")
        
        return jobs
    
    async def _extract_zoho_with_selenium(self, base_url: str) -> List[Dict[str, Any]]:
        """Extract jobs from Zoho Recruit using proven working Selenium approach"""
        jobs = []
        driver = None
        
        try:
            driver = self._create_selenium_driver()
            if not driver:
                logger.error("Failed to create Selenium driver")
                return []
            
            logger.info(f"Loading page with Selenium: {base_url}")
            driver.get(base_url)
            
            # Wait for JavaScript to load - exactly as in your working code
            time.sleep(5)
            
            # Get the page source after JavaScript execution
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # Use your exact working selectors
            job_elements = soup.select('.cw-filter-joblist')
            logger.info(f"🟢 Found {len(job_elements)} job(s)")
            
            for job_el in job_elements:
                try:
                    # Extract using your exact working selectors
                    title_el = job_el.select_one('a.cw-3-title')
                    location_el = job_el.select_one('p.filter-subhead')
                    summary_el = job_el.select('p.cw-bw')
                    job_type_el = job_el.select_one('.cw-full-time')
                    date_el = job_el.select_one('.search-date-opened')
                    
                    if not title_el:
                        continue
                    
                    job_title = title_el.get_text(strip=True)
                    job_url = title_el.get('href', '')
                    location = location_el.get_text(strip=True) if location_el else ""
                    summary = summary_el[1].get_text(strip=True) if len(summary_el) > 1 else ""
                    job_type = job_type_el.get_text(strip=True) if job_type_el else ""
                    date_posted = date_el.get_text(strip=True) if date_el else ""
                    
                    # Get full job details using the working approach
                    full_description = await self._get_job_details_with_selenium(job_url) if job_url else summary
                    
                    # Parse the posted date
                    posted_date = self._parse_date(date_posted) if date_posted else None
                    
                    job_data = {
                        'title': job_title,
                        'url': job_url,
                        'location': location,
                        'description': summary,
                        'full_description': full_description,
                        'job_type': job_type,
                        'posted_date': posted_date,
                        'posted_date_str': date_posted,
                        'source_url': base_url,
                        'scraped_at': datetime.utcnow()
                    }
                    
                    jobs.append(job_data)
                    logger.info(f"Extracted job: {job_title} at {location}")
                    
                except Exception as e:
                    logger.error(f"Error extracting individual job: {str(e)}")
                    continue
            
        except Exception as e:
            logger.error(f"Error in Selenium extraction: {str(e)}")
        finally:
            if driver:
                driver.quit()
        
        return jobs
    
    async def _get_job_details_with_selenium(self, job_url: str) -> str:
        """Get detailed job description from individual job page - your exact working code"""
        driver = None
        try:
            driver = self._create_selenium_driver()
            if not driver:
                return "No description found."
            
            driver.get(job_url)
            time.sleep(3)  # Your exact timing
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            description_el = soup.select_one('.cw-job-desc')
            
            return description_el.get_text(separator='\n', strip=True) if description_el else "No description found."
            
        except Exception as e:
            logger.debug(f"Error getting job details for {job_url}: {str(e)}")
            return "No description found."
        finally:
            if driver:
                driver.quit()
    
    async def _extract_zoho_static_content(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, Any]]:
        """Extract job info from Zoho Recruit HTML using the specific structure"""
        jobs = []
        
        # Look for the specific Zoho Recruit job listing structure
        job_elements = soup.select('.cw-filter-joblist')
        logger.info(f"Found {len(job_elements)} job elements with .cw-filter-joblist selector")
        
        # Log the HTML content for debugging if no jobs found
        if len(job_elements) == 0:
            logger.info("No .cw-filter-joblist elements found, checking page content...")
            # Log a sample of the HTML to see what's actually there
            html_sample = str(soup)[:2000].replace('\n', ' ')
            logger.info(f"HTML sample: {html_sample}")
            
            # Check for common "no jobs" indicators
            page_text = soup.get_text().lower()
            if any(phrase in page_text for phrase in [
                'no current openings', 'no openings', 'no positions available', 
                'no jobs available', 'no vacancies', 'currently no openings',
                'no open positions', 'we are not hiring'
            ]):
                logger.info("Page indicates no current job openings")
                return []
            
            # Check if there are any job-related elements with different selectors
            alternative_selectors = [
                '.job-item', '.job-listing', '.position', '.opening',
                '.rec-job-item', '.zr-job', '[data-job]', '.career-item'
            ]
            
            for selector in alternative_selectors:
                alt_elements = soup.select(selector)
                if alt_elements:
                    logger.info(f"Found {len(alt_elements)} elements with alternative selector: {selector}")
                    break
        
        for job_element in job_elements:
            try:
                job_data = {
                    'source_url': base_url,
                    'scraped_at': datetime.utcnow()
                }
                
                # Extract job title and URL from the link
                title_link = job_element.select_one('.cw-filter-joblist-left h3 a.cw-3-title')
                if title_link:
                    job_data['title'] = title_link.get_text(strip=True)
                    job_data['url'] = title_link.get('href', base_url)
                    logger.info(f"Found job: {job_data['title']}")
                else:
                    continue  # Skip if no title found
                
                # Extract location from the filter-subhead paragraph
                location_elem = job_element.select_one('.cw-filter-joblist-left p.filter-subhead')
                if location_elem:
                    job_data['location'] = location_elem.get_text(strip=True)
                else:
                    job_data['location'] = ''
                
                # Extract job description from the third paragraph
                desc_paragraphs = job_element.select('.cw-filter-joblist-left p')
                if len(desc_paragraphs) >= 2:
                    # The description is usually the second or third paragraph
                    for p in desc_paragraphs:
                        if not p.has_attr('class') or 'filter-subhead' not in p.get('class', []):
                            desc_text = p.get_text(strip=True)
                            if len(desc_text) > 20:  # Must be substantial
                                job_data['description'] = desc_text
                                break
                    
                    if 'description' not in job_data:
                        job_data['description'] = ''
                else:
                    job_data['description'] = ''
                
                # Extract job type and posted date from the right section
                job_type_elem = job_element.select_one('.cw-filter-joblist-right .cw-full-time')
                posted_date_elem = job_element.select_one('.cw-filter-joblist-right .search-date-opened')
                
                job_data['job_type'] = job_type_elem.get_text(strip=True) if job_type_elem else 'Not specified'
                job_data['posted_date_str'] = posted_date_elem.get_text(strip=True) if posted_date_elem else ''
                
                # Parse the posted date
                if job_data['posted_date_str']:
                    job_data['posted_date'] = self._parse_date(job_data['posted_date_str'])
                
                # Add to jobs list
                jobs.append(job_data)
                logger.info(f"Successfully extracted job: {job_data['title']} at {job_data['location']}")
                
            except Exception as e:
                logger.error(f"Error extracting individual job: {str(e)}")
                continue
        
        # If no jobs found with specific selectors, try fallback selectors
        if not jobs:
            logger.info("No jobs found with specific selectors, trying fallback")
            fallback_selectors = [
                '.zr-job-title', '.job-title', '.rec-job-title',
                '.zr-position', '.position-title', '.job-position',
                '.zr-listing', '.job-listing', '.career-listing'
            ]
            
            for selector in fallback_selectors:
                elements = soup.select(selector)
                for element in elements:
                    job_title = element.get_text(strip=True)
                    if job_title and len(job_title) > 2:
                        # Try to find associated details
                        parent = element.find_parent()
                        location = ""
                        description = ""
                        job_url = base_url
                        
                        if parent:
                            # Look for location
                            location_elem = parent.select_one('.location, .zr-location, .job-location, .filter-subhead')
                            if location_elem:
                                location = location_elem.get_text(strip=True)
                            
                            # Look for description
                            desc_elem = parent.select_one('.description, .zr-description, .job-desc')
                            if desc_elem:
                                description = desc_elem.get_text(strip=True)
                            
                            # Look for job link
                            link_elem = parent.select_one('a[href]')
                            if link_elem and link_elem.get('href'):
                                job_url = urljoin(base_url, link_elem.get('href'))
                        
                        jobs.append({
                            'title': job_title,
                            'description': description,
                            'location': location,
                            'url': job_url,
                            'source_url': base_url,
                            'scraped_at': datetime.utcnow()
                        })
        
        logger.info(f"Total jobs extracted: {len(jobs)}")
        return jobs
    
    async def _try_zoho_alternatives(self, base_url: str, session) -> List[Dict[str, Any]]:
        """Try alternative Zoho Recruit endpoints"""
        jobs = []
        
        # Extract domain for alternative URLs
        from urllib.parse import urlparse
        parsed = urlparse(base_url)
        domain = f"{parsed.scheme}://{parsed.netloc}"
        
        # Try common alternative endpoints
        alternative_urls = [
            f"{domain}/jobs",
            f"{domain}/careers",
            f"{domain}/positions",
            f"{domain}/jobs",
            f"{domain}/feed/jobs",
            f"{domain}/jobs.xml",
            f"{domain}/jobs.json"
        ]
        
        for alt_url in alternative_urls:
            try:
                async with session.get(alt_url) as response:
                    if response.status == 200:
                        content_type = response.headers.get('content-type', '').lower()
                        
                        if 'json' in content_type:
                            data = await response.json()
                            jobs_from_json = self._parse_json_jobs(data, alt_url)
                            if jobs_from_json:
                                logger.info(f"Found jobs from JSON endpoint: {alt_url}")
                                jobs.extend(jobs_from_json)
                                break
                                
                        elif 'xml' in content_type:
                            text = await response.text()
                            jobs_from_xml = self._parse_xml_jobs(text, alt_url)
                            if jobs_from_xml:
                                logger.info(f"Found jobs from XML endpoint: {alt_url}")
                                jobs.extend(jobs_from_xml)
                                break
                                
                        else:
                            # Try HTML parsing on alternative page
                            html = await response.text()
                            soup = BeautifulSoup(html, 'html.parser')
                            alt_jobs = await self._extract_zoho_static_content(soup, alt_url)
                            if alt_jobs:
                                logger.info(f"Found jobs from alternative page: {alt_url}")
                                jobs.extend(alt_jobs)
                                break
                                
            except Exception as e:
                logger.debug(f"Alternative URL {alt_url} failed: {str(e)}")
                continue
        
        return jobs
    
    def _parse_json_jobs(self, data: dict, source_url: str) -> List[Dict[str, Any]]:
        """Parse jobs from JSON data"""
        jobs = []
        
        # Handle different JSON structures
        job_list = []
        if isinstance(data, list):
            job_list = data
        elif isinstance(data, dict):
            # Try common job array keys
            for key in ['jobs', 'positions', 'openings', 'careers', 'listings']:
                if key in data and isinstance(data[key], list):
                    job_list = data[key]
                    break
        
        for job_data in job_list:
            if isinstance(job_data, dict):
                jobs.append({
                    'title': job_data.get('title') or job_data.get('position') or job_data.get('name', 'Unknown Position'),
                    'description': job_data.get('description') or job_data.get('summary', ''),
                    'location': job_data.get('location') or job_data.get('city', ''),
                    'url': job_data.get('url') or job_data.get('link') or source_url,
                    'source_url': source_url,
                    'scraped_at': datetime.utcnow()
                })
        
        return jobs
    
    def _parse_xml_jobs(self, xml_content: str, source_url: str) -> List[Dict[str, Any]]:
        """Parse jobs from XML/RSS feed"""
        jobs = []
        
        try:
            from xml.etree import ElementTree as ET
            root = ET.fromstring(xml_content)
            
            # Handle RSS format
            for item in root.findall('.//item'):
                title = item.find('title')
                description = item.find('description')
                link = item.find('link')
                
                jobs.append({
                    'title': title.text if title is not None else 'Unknown Position',
                    'description': description.text if description is not None else '',
                    'location': '',
                    'url': link.text if link is not None else source_url,
                    'source_url': source_url,
                    'scraped_at': datetime.utcnow()
                })
            
            # Handle other XML formats
            if not jobs:
                for job_elem in root.findall('.//job'):
                    title = job_elem.find('title') or job_elem.find('position')
                    desc = job_elem.find('description')
                    location = job_elem.find('location')
                    
                    jobs.append({
                        'title': title.text if title is not None else 'Unknown Position',
                        'description': desc.text if desc is not None else '',
                        'location': location.text if location is not None else '',
                        'url': source_url,
                        'source_url': source_url,
                        'scraped_at': datetime.utcnow()
                    })
                    
        except Exception as e:
            logger.debug(f"Error parsing XML: {str(e)}")
        
        return jobs
    
    async def _extract_job_info_from_text(self, url: str) -> List[Dict[str, Any]]:
        """Extract job information from any available text content"""
        jobs = []
        
        try:
            connector = aiohttp.TCPConnector(ssl=self.ssl_context)
            async with aiohttp.ClientSession(
                timeout=self.session_timeout,
                headers=self.headers,
                connector=connector
            ) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        # Remove script and style tags
                        for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
                            tag.decompose()
                        
                        # Get all text content
                        text_content = soup.get_text(separator=' ', strip=True)
                        
                        # Look for job-related keywords in the text
                        job_keywords = [
                            'software engineer', 'developer', 'programmer', 'analyst',
                            'manager', 'director', 'coordinator', 'specialist',
                            'consultant', 'administrator', 'technician', 'architect',
                            'designer', 'marketing', 'sales', 'hr', 'human resources',
                            'project manager', 'product manager', 'data scientist',
                            'devops', 'qa', 'tester', 'support', 'intern'
                        ]
                        
                        # Check if any job keywords are present
                        text_lower = text_content.lower()
                        found_keywords = [kw for kw in job_keywords if kw in text_lower]
                        
                        if found_keywords:
                            # Create a job entry with found information
                            jobs.append({
                                'title': f'Careers Available - {", ".join(found_keywords[:3]).title()}',
                                'description': 'Job opportunities detected on career page',
                                'location': 'Not specified',
                                'url': url,
                                'source_url': url,
                                'scraped_at': datetime.utcnow(),
                                'full_description': f'Career page contains opportunities related to: {", ".join(found_keywords)}'
                            })
                        
        except Exception as e:
            logger.error(f"Error extracting job info from text: {str(e)}")
        
        return jobs