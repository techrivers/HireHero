import openai
from typing import List, Tuple, Dict, Any
from sqlalchemy.orm import Session
from app.models.models import UserConfig, MatchLog, MatchResult
from app.services.google_drive_service import google_drive_service
from app.utils.document_parser import document_parser
from app.utils.encryption import encryption_service
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import json
import re

class CVMatchingService:
    def __init__(self):
        self.openai_client = None
    
    def get_openai_key(self, db: Session, user_id: int) -> str:
        """Get user's OpenAI API key."""
        user_config = db.query(UserConfig).filter(UserConfig.user_id == user_id).first()
        if not user_config or not user_config.openai_api_key:
            return None
        
        return encryption_service.decrypt(user_config.openai_api_key)
    
    def initialize_openai_client(self, api_key: str):
        """Initialize OpenAI client with user's API key."""
        try:
            print(f"Attempting to initialize OpenAI client...")
            print(f"OpenAI version: {openai.__version__}")
            
            # Check if api_key is properly formatted
            if not api_key or not api_key.startswith('sk-'):
                print(f"Warning: API key doesn't look valid: {api_key[:10]}...")
            
            # Import httpx and create a custom client without proxies parameter
            import httpx
            
            # Create httpx client without conflicting parameters
            http_client = httpx.Client(
                timeout=60.0,
                limits=httpx.Limits(
                    max_keepalive_connections=10,
                    max_connections=100
                ),
                follow_redirects=True
            )
            
            # Initialize OpenAI with custom http client and shorter timeouts
            self.openai_client = openai.OpenAI(
                api_key=api_key,
                http_client=http_client,
                timeout=30.0  # 30 second timeout
            )
            print("✅ OpenAI client initialized successfully with custom http client")
            
        except Exception as e:
            print(f"❌ Error initializing OpenAI client: {e}")
            print(f"Error type: {type(e)}")
            import traceback
            traceback.print_exc()
            
            # Try fallback method without custom http client
            try:
                print("Trying fallback initialization...")
                # Just set the API key globally for older OpenAI versions
                openai.api_key = api_key
                self.openai_client = "legacy"  # Flag to use legacy methods
                print("✅ Fallback OpenAI client setup successful")
            except Exception as e2:
                print(f"❌ Fallback also failed: {e2}")
                # Set client to None to prevent usage
                self.openai_client = None
                raise Exception(f"Failed to initialize OpenAI client: {e}")
    
    def extract_job_requirements(self, job_description: str) -> Dict[str, Any]:
        """Extract key requirements from job description using intelligent parsing."""
        requirements = {
            "technical_skills": [],
            "soft_skills": [],
            "experience_years": None,
            "role_type": "",
            "industry": "",
            "keywords": []
        }
        
        text = job_description.lower()
        
        # Technical skills patterns
        tech_patterns = {
            'python': ['python'],
            'javascript': ['javascript', 'js', 'node.js', 'nodejs'],
            'java': ['java'],
            'react': ['react', 'reactjs'],
            'angular': ['angular'],
            'vue': ['vue', 'vuejs'],
            'django': ['django'],
            'flask': ['flask'],
            'fastapi': ['fastapi'],
            'sql': ['sql', 'mysql', 'postgresql', 'postgres'],
            'mongodb': ['mongodb', 'mongo'],
            'docker': ['docker'],
            'kubernetes': ['kubernetes', 'k8s'],
            'aws': ['aws', 'amazon web services'],
            'azure': ['azure'],
            'gcp': ['google cloud', 'gcp'],
            'machine learning': ['machine learning', 'ml', 'ai', 'artificial intelligence'],
            'data science': ['data science', 'data scientist'],
            'project management': ['project management', 'project manager', 'pm'],
            'agile': ['agile', 'scrum'],
            'devops': ['devops', 'ci/cd'],
            'git': ['git', 'github', 'gitlab']
        }
        
        # Find technical skills
        for skill, patterns in tech_patterns.items():
            for pattern in patterns:
                if pattern in text:
                    requirements["technical_skills"].append(skill)
                    break
        
        # Remove duplicates
        requirements["technical_skills"] = list(set(requirements["technical_skills"]))
        
        # Extract experience years
        exp_patterns = [
            r'(\d+)\+?\s*years?\s*(?:of\s*)?experience',
            r'(\d+)\+?\s*years?\s*in',
            r'minimum\s*(\d+)\s*years?',
            r'at\s*least\s*(\d+)\s*years?'
        ]
        
        for pattern in exp_patterns:
            match = re.search(pattern, text)
            if match:
                requirements["experience_years"] = int(match.group(1))
                break
        
        # Determine role type
        if any(word in text for word in ['senior', 'lead', 'principal', 'architect']):
            requirements["role_type"] = "senior"
        elif any(word in text for word in ['junior', 'entry', 'graduate', 'intern']):
            requirements["role_type"] = "junior"
        else:
            requirements["role_type"] = "mid"
        
        # Extract all significant keywords
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text)
        requirements["keywords"] = [w for w in set(words) if w not in ['the', 'and', 'for', 'with', 'are', 'you', 'will', 'have', 'been', 'this', 'that', 'from', 'they', 'were', 'been']]
        
        return requirements
    
    def analyze_cv_content(self, cv_text: str) -> Dict[str, Any]:
        """Analyze CV content and extract comprehensive information using OpenAI."""
        analysis = {
            "summary": "",
            "skills": [],
            "experience_years": None,
            "technologies": [],
            "role_level": "",
            "keywords": []
        }
        
        # Extract complete professional summary
        analysis["summary"] = document_parser.extract_complete_summary(cv_text)
        
        # Extract skills from proper skill sections
        analysis["skills"] = document_parser.extract_skills_section(cv_text)
        
        # Extract experience years
        analysis["experience_years"] = document_parser.extract_experience_years(cv_text)
        
        # Use OpenAI for intelligent analysis if available
        if self.openai_client:
            try:
                print("🧠 Using OpenAI for intelligent CV analysis...")
                
                # Create a prompt for extracting comprehensive skills and technologies
                analysis_prompt = f"""
Analyze this CV and extract the following information. Return ONLY a JSON object with these fields:
{{
    "all_technical_skills": ["list of ALL technical skills, tools, programming languages, frameworks, databases, platforms mentioned"],
    "experience_level": "junior/mid/senior based on experience and role titles",
    "years_of_experience": "number only if mentioned, null if not found",
    "key_technologies": ["main technologies and tools this person has strong experience with"]
}}

CV TEXT:
{cv_text[:4000]}  # Limit to avoid token limits

Be thorough - include ALL technical skills mentioned anywhere in the CV, not just in skill sections.
"""
                
                # Make OpenAI call for analysis
                if self.openai_client == "legacy":
                    # Use legacy openai approach
                    import openai
                    response = openai.ChatCompletion.create(
                        model="gpt-3.5-turbo",
                        messages=[{"role": "user", "content": analysis_prompt}],
                        max_tokens=500,
                        temperature=0.1
                    )
                    ai_analysis = response.choices[0].message.content
                else:
                    # Use new OpenAI client
                    response = self.openai_client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[{"role": "user", "content": analysis_prompt}],
                        max_tokens=500,
                        temperature=0.1
                    )
                    ai_analysis = response.choices[0].message.content
                
                # Parse the JSON response
                import json
                try:
                    ai_data = json.loads(ai_analysis)
                    
                    # Enhance our analysis with OpenAI results
                    if ai_data.get("all_technical_skills"):
                        # Combine extracted skills with AI-found skills
                        all_skills = analysis["skills"] + ai_data["all_technical_skills"]
                        analysis["skills"] = list(set(all_skills))  # Remove duplicates
                    
                    if ai_data.get("key_technologies"):
                        analysis["technologies"] = ai_data["key_technologies"]
                    
                    if ai_data.get("experience_level"):
                        analysis["role_level"] = ai_data["experience_level"]
                    
                    if ai_data.get("years_of_experience") and not analysis["experience_years"]:
                        try:
                            analysis["experience_years"] = int(ai_data["years_of_experience"])
                        except:
                            pass
                    
                    print(f"🧠 OpenAI enhanced analysis: {len(analysis['skills'])} skills, {len(analysis['technologies'])} technologies")
                    
                except json.JSONDecodeError:
                    print(f"⚠️ Could not parse OpenAI response as JSON: {ai_analysis}")
                    
            except Exception as e:
                print(f"⚠️ OpenAI analysis failed: {e}, falling back to pattern matching")
        
        # Fallback: Extract technologies mentioned anywhere in CV if not found by OpenAI
        if not analysis["technologies"]:
            tech_keywords = [
                'python', 'javascript', 'java', 'react', 'angular', 'vue', 'django', 'flask',
                'sql', 'mongodb', 'docker', 'kubernetes', 'aws', 'azure', 'git', 'linux',
                'machine learning', 'data science', 'agile', 'scrum', 'project management'
            ]
            
            cv_lower = cv_text.lower()
            analysis["technologies"] = [tech for tech in tech_keywords if tech in cv_lower]
        
        # Fallback: Determine role level from CV content if not found by OpenAI
        if not analysis["role_level"]:
            cv_lower = cv_text.lower()
            if any(word in cv_lower for word in ['senior', 'lead', 'principal', 'architect', 'manager']):
                analysis["role_level"] = "senior"
            elif any(word in cv_lower for word in ['junior', 'entry', 'graduate', 'intern', 'assistant']):
                analysis["role_level"] = "junior"
            else:
                analysis["role_level"] = "mid"
        
        # Extract keywords from CV
        words = re.findall(r'\b[a-zA-Z]{3,}\b', cv_text.lower())
        analysis["keywords"] = list(set(words))
        
        return analysis
    
    def calculate_openai_relevance_score(self, job_description: str, cv_text: str, cv_analysis: Dict[str, Any]) -> Tuple[float, str]:
        """Use OpenAI to intelligently score CV relevance against job description."""
        
        if not self.openai_client:
            print("⚠️ OpenAI not available, falling back to basic scoring")
            return 50.0, "OpenAI analysis not available"
        
        try:
            print("🧠 Using OpenAI for intelligent CV-Job matching...")
            
            # Create comprehensive matching prompt
            matching_prompt = f"""
You are an expert HR recruiter. Analyze how well this candidate's CV matches the job description.

JOB DESCRIPTION:
{job_description}

CANDIDATE CV:
{cv_text[:6000]}  # Limit to avoid token limits

ANALYSIS INSTRUCTIONS:
1. Identify ALL requirements explicitly mentioned in the job description
2. Check which requirements the candidate meets (STRENGTHS)
3. Check which requirements the candidate lacks (GAPS)
4. Additional skills not mentioned in job description = bonus STRENGTHS
5. Score based on how many stated requirements are met

SCORING GUIDELINES:
- 95-100%: Meets ALL stated requirements + has bonus skills
- 85-94%: Meets ALL key requirements, minor gaps in secondary requirements  
- 75-84%: Meets most stated requirements, some gaps in important areas
- 60-74%: Meets basic requirements, notable gaps in key areas
- 40-59%: Missing several explicitly stated requirements
- 0-39%: Lacks most fundamental requirements mentioned in job description

IMPORTANT: You MUST identify gaps where the CV lacks skills/experience that are specifically mentioned in the job description. Don't ignore missing requirements.

Return ONLY a JSON object with this exact format:
{{
    "relevance_score": 75,
    "match_analysis": "🟢 STRENGTHS: The candidate has experience in manual testing, test case design, and bug tracking which align with the job requirements. They also have additional experience with API testing, regression testing, and JIRA which are valuable bonus skills for the role.

🔴 GAPS: The candidate lacks specific experience in automation testing which was mentioned as a requirement in the job description. They also don't show experience with Python programming which was listed as a key requirement.",
    "key_strengths": ["manual testing experience", "test case design", "bug tracking", "API testing knowledge"],
    "potential_gaps": ["automation testing experience", "Python programming"],
    "recommendation": "good_match" or "partial_match" or "poor_match"
}}

CRITICAL: Always include GAPS section when requirements from job description are missing in the CV. Don't ignore missing requirements.
"""

            # Make OpenAI call for intelligent matching
            if self.openai_client == "legacy":
                # Use legacy openai approach
                import openai
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": matching_prompt}],
                    max_tokens=800,
                    temperature=0.1
                )
                ai_response = response.choices[0].message.content
            else:
                # Use new OpenAI client
                response = self.openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": matching_prompt}],
                    max_tokens=800,
                    temperature=0.1
                )
                ai_response = response.choices[0].message.content
            
            # Parse the JSON response
            import json
            try:
                ai_analysis = json.loads(ai_response)
                
                relevance_score = float(ai_analysis.get("relevance_score", 50))
                match_analysis = ai_analysis.get("match_analysis", "AI analysis completed")
                
                # Ensure score is within valid range
                relevance_score = max(0, min(100, relevance_score))
                
                print(f"🧠 OpenAI Analysis Complete - Score: {relevance_score}%")
                print(f"🔍 Match Analysis: {match_analysis[:100]}...")
                
                return relevance_score, match_analysis
                
            except json.JSONDecodeError:
                print(f"⚠️ Could not parse OpenAI response as JSON: {ai_response[:200]}...")
                # Try to extract score using regex as fallback
                import re
                score_match = re.search(r'"relevance_score":\s*(\d+)', ai_response)
                if score_match:
                    score = float(score_match.group(1))
                    return max(0, min(100, score)), ai_response[:500]
                else:
                    return 50.0, ai_response[:500]
                    
        except Exception as e:
            print(f"❌ OpenAI matching failed: {e}")
            # Fallback to basic pattern matching
            return self.calculate_fallback_score(job_description, cv_analysis), "OpenAI analysis failed, used fallback scoring"
    
    def calculate_fallback_score(self, job_description: str, cv_analysis: Dict[str, Any]) -> float:
        """Fallback scoring when OpenAI is not available."""
        score = 0.0
        
        # Basic keyword matching
        job_words = set(job_description.lower().split())
        cv_words = set(' '.join(cv_analysis['keywords']).lower().split())
        
        if job_words:
            overlap = len(job_words.intersection(cv_words))
            score = (overlap / len(job_words)) * 70  # Max 70% for basic matching
        
        # Bonus for having skills
        if cv_analysis['skills']:
            score += 20
        
        # Bonus for having technologies
        if cv_analysis['technologies']:
            score += 10
        
        return min(100, score)
    
    def process_cv_matching(self, db: Session, user_id: int, job_description: str) -> Dict[str, Any]:
        """Process CV matching with intelligent algorithm."""
        import time
        
        # Get user config
        user_config = db.query(UserConfig).filter(UserConfig.user_id == user_id).first()
        if not user_config:
            raise Exception("User configuration not found")
        
        # Get OpenAI API key
        openai_key = self.get_openai_key(db, user_id)
        if not openai_key:
            raise Exception("OpenAI API key not found")
        
        # Initialize OpenAI client
        self.initialize_openai_client(openai_key)
        
        # Check if Google Drive is set up
        if not user_config.google_drive_token:
            return {
                "results": [],
                "match_id": None,
                "total_cvs_processed": 0,
                "message": "Google Drive not configured. Please set up Google Drive to access CV files.",
                "status": "google_drive_not_configured"
            }
        
        # Test Google Drive connectivity (this will auto-refresh tokens if needed)
        print(f"🔄 Testing Google Drive connectivity for user {user_id}")
        test_credentials = google_drive_service.get_user_credentials(db, user_id)
        if not test_credentials:
            return {
                "results": [],
                "match_id": None,
                "total_cvs_processed": 0,
                "message": "Failed to access Google Drive. Please reconnect your Google Drive account.",
                "status": "google_drive_access_failed"
            }
        
        # Get files from Google Drive with fresh tokens
        cv_folder = user_config.cv_folder_name or "cvs"
        files = google_drive_service.list_files_in_folder(db, user_id, cv_folder)
        
        if not files:
            return {
                "results": [],
                "match_id": None,
                "total_cvs_processed": 0,
                "message": f"No files found in '{cv_folder}' folder. Please upload CV files to your Google Drive folder.",
                "status": "no_files_found",
                "folder_name": cv_folder
            }
        
        # Create match log
        match_log = MatchLog(
            user_id=user_id,
            job_description=job_description,
            total_cvs_processed=0
        )
        db.add(match_log)
        db.commit()
        db.refresh(match_log)
        
        # Log job description for processing
        print(f"🎯 Analyzing job description with OpenAI...")
        print(f"📝 Job description length: {len(job_description)} characters")
        print(f"📄 Job preview: {job_description[:200]}...")
        
        processed_cvs = []
        total_start_time = time.time()
        
        print(f"🚀 Processing all {len(files)} CVs with intelligent matching")
        
        for i, file_info in enumerate(files, 1):
            try:
                cv_start_time = time.time()
                print(f"🔄 Processing CV {i}/{len(files)}: {file_info['name']}")
                
                # Download file content
                file_content = google_drive_service.download_file(db, user_id, file_info['id'])
                if not file_content:
                    print(f"  ❌ Could not download {file_info['name']}")
                    continue
                
                # Extract text
                cv_text = document_parser.extract_text_from_file(file_content, file_info['name'])
                if not cv_text:
                    print(f"  ❌ No text extracted from {file_info['name']}")
                    continue
                
                # Analyze CV content
                cv_analysis = self.analyze_cv_content(cv_text)
                print(f"  📋 Found {len(cv_analysis['skills'])} skills, {len(cv_analysis['technologies'])} technologies")
                
                # Use OpenAI for intelligent CV-Job matching
                relevance_score, ai_match_analysis = self.calculate_openai_relevance_score(
                    job_description, cv_text, cv_analysis
                )
                print(f"  🎯 OpenAI Relevance score: {relevance_score:.1f}%")
                
                # Only include CVs with meaningful relevance (>15%)
                if relevance_score < 15.0:
                    print(f"  ⏭️ Skipping CV with low relevance: {relevance_score:.1f}%")
                    continue
                
                # Extract candidate name
                candidate_name = document_parser.extract_candidate_name(cv_text)
                if not candidate_name:
                    candidate_name = file_info['name'].replace('.pdf', '').replace('CV', '').strip()
                
                # Create match result
                match_result = MatchResult(
                    match_log_id=match_log.id,
                    cv_filename=file_info['name'],
                    candidate_name=candidate_name,
                    candidate_summary=cv_analysis["summary"],
                    relevance_score=relevance_score,
                    google_drive_file_id=file_info['id'],
                    download_url=file_info.get('webContentLink') or file_info.get('webViewLink'),
                    key_skills=json.dumps(cv_analysis["skills"]),
                    match_analysis=ai_match_analysis,  # Use OpenAI analysis instead of summary
                    experience_years=cv_analysis["experience_years"]
                )
                
                db.add(match_result)
                processed_cvs.append(match_result)
                
                cv_time = time.time() - cv_start_time
                print(f"  ✅ CV processed in {cv_time:.2f}s")
                
            except Exception as e:
                print(f"❌ Error processing {file_info['name']}: {e}")
                continue
        
        # Commit all results
        db.commit()
        
        # Update match log
        match_log.total_cvs_processed = len(processed_cvs)
        
        # Reload results from database to get all fields
        processed_cvs = db.query(MatchResult).filter(
            MatchResult.match_log_id == match_log.id
        ).order_by(MatchResult.relevance_score.desc()).all()
        
        # Mark top 3 as top matches
        top_matches = processed_cvs[:3]
        for match in top_matches:
            match.is_top_match = True
        
        match_log.top_matches_count = len(top_matches)
        db.commit()
        
        # Format results
        def format_match(match_result):
            score = match_result.relevance_score
            if score >= 80:
                match_status = "best_match"
            elif score >= 60:
                match_status = "average_match"
            else:
                match_status = "low_match"
            
            # Parse skills from JSON
            skills = []
            if match_result.key_skills:
                try:
                    skills = json.loads(match_result.key_skills)
                except:
                    skills = []
            
            return {
                "cv_filename": match_result.cv_filename,
                "candidate_name": match_result.candidate_name,
                "candidate_summary": match_result.candidate_summary,
                "relevance_score": round(match_result.relevance_score, 2),
                "match_status": match_status,
                "download_url": match_result.download_url,
                "google_drive_file_id": match_result.google_drive_file_id,  # Add file ID for proper downloads
                "key_skills": skills,
                "match_analysis": match_result.match_analysis,
                "experience_years": match_result.experience_years
            }
        
        all_results = [format_match(match) for match in processed_cvs]
        
        total_time = time.time() - total_start_time
        print(f"🎉 Completed processing in {total_time:.2f}s - Found {len(all_results)} relevant matches")
        
        return {
            "results": all_results,
            "match_id": match_log.id,
            "total_cvs_processed": len(processed_cvs),
            "top_matches_count": len(top_matches),
            "status": "success",
            "message": f"Successfully processed {len(processed_cvs)} relevant CVs out of {len(files)} total"
        }

cv_matching_service = CVMatchingService()