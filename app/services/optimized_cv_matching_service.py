import openai
from typing import List, Tuple, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.models import UserConfig, MatchLog, MatchResult
from app.services.google_drive_service import google_drive_service
from app.utils.simple_document_parser import simple_document_parser as document_parser
from app.utils.encryption import encryption_service
import json
import re
import time
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from functools import lru_cache
import hashlib
from collections import Counter

class OptimizedCVMatchingService:
    def __init__(self):
        self.openai_client = None
        # Job analysis cache - stores job requirements by hash
        self._job_cache = {}
        # Lock for thread-safe operations
        self._cache_lock = threading.Lock()
        
    def get_openai_key(self, db: Session, user_id: int) -> str:
        """Get user's OpenAI API key."""
        user_config = db.query(UserConfig).filter(UserConfig.user_id == user_id).first()
        if not user_config or not user_config.openai_api_key:
            return None
        return encryption_service.decrypt(user_config.openai_api_key)
    
    def initialize_openai_client(self, api_key: str):
        """Initialize OpenAI client with optimized settings."""
        print(f"🔑 Initializing optimized OpenAI client...")
        try:
            import httpx
            # Optimized HTTP client with connection pooling
            http_client = httpx.Client(
                timeout=30.0,  # Reduced from 60s
                limits=httpx.Limits(
                    max_keepalive_connections=20,  # Increased for connection reuse
                    max_connections=100,
                    keepalive_expiry=30.0
                ),
                follow_redirects=True
            )
            
            self.openai_client = openai.OpenAI(
                api_key=api_key,
                http_client=http_client,
                timeout=25.0  # Reduced timeout for faster failures
            )
            
            # Quick test with minimal tokens
            test_response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",  # Use faster model for test
                messages=[{"role": "user", "content": "OK"}],
                max_tokens=5,
                temperature=0
            )
            print(f"✅ Optimized OpenAI client initialized and tested")
            
        except Exception as e:
            print(f"❌ Error initializing optimized OpenAI client: {e}")
            self.openai_client = None
            raise Exception(f"Failed to initialize OpenAI client: {e}")

    def get_job_requirements_hash(self, job_description: str) -> str:
        """Generate hash for job description caching."""
        return hashlib.md5(job_description.encode()).hexdigest()

    def extract_job_requirements_cached(self, job_description: str) -> Dict[str, Any]:
        """Cache job requirements analysis to avoid repeated API calls."""
        job_hash = self.get_job_requirements_hash(job_description)
        
        with self._cache_lock:
            if job_hash in self._job_cache:
                print(f"🚀 Using cached job analysis (hash: {job_hash[:8]})")
                return self._job_cache[job_hash]
        
        print(f"🧠 Analyzing job requirements (new analysis)...")
        job_requirements = self.extract_job_requirements_optimized(job_description)
        
        with self._cache_lock:
            self._job_cache[job_hash] = job_requirements
            # Keep cache size manageable
            if len(self._job_cache) > 50:
                # Remove oldest entries
                oldest_key = next(iter(self._job_cache))
                del self._job_cache[oldest_key]
        
        return job_requirements

    def extract_job_requirements_optimized(self, job_description: str) -> Dict[str, Any]:
        """Optimized job requirements extraction with compressed prompts."""
        if not self.openai_client:
            return self._extract_job_requirements_fallback(job_description)
        
        try:
            # Compressed prompt with essential information only
            prompt = f"""Extract job requirements as JSON:
{{"position":"job title","seniority":"junior/mid/senior","required_skills":["must-have skills"],"required_experience_years":"number or null","key_requirements":"brief summary"}}

Job: {job_description[:1500]}"""

            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",  # Faster model
                messages=[{"role": "user", "content": prompt}],
                max_tokens=400,  # Reduced tokens
                temperature=0,   # Deterministic
                top_p=1         # Focused responses
            )
            
            ai_response = response.choices[0].message.content
            requirements = json.loads(ai_response)
            print(f"🎯 Job analysis: {requirements.get('position', 'Unknown Position')}")
            return requirements
            
        except json.JSONDecodeError as e:
            print(f"⚠️ JSON parse error, using fallback: {e}")
            return self._extract_job_requirements_fallback(job_description)
        except Exception as e:
            print(f"❌ Job analysis failed, using fallback: {e}")
            return self._extract_job_requirements_fallback(job_description)

    def _extract_job_requirements_fallback(self, job_description: str) -> Dict[str, Any]:
        """Fast fallback job requirements extraction."""
        text = job_description.lower()
        
        # Quick keyword extraction
        tech_keywords = ['python', 'javascript', 'java', 'react', 'angular', 'vue', 'sql', 
                        'mongodb', 'docker', 'aws', 'azure', 'git', 'machine learning', 'ai']
        found_skills = [skill for skill in tech_keywords if skill in text]
        
        # Quick experience extraction
        exp_match = re.search(r'(\d+)\+?\s*years?\s*(?:of\s*)?experience', text)
        experience_years = int(exp_match.group(1)) if exp_match else None
        
        # Quick seniority detection
        if any(word in text for word in ['senior', 'lead', 'principal']):
            seniority = "senior"
        elif any(word in text for word in ['junior', 'entry', 'intern']):
            seniority = "junior"
        else:
            seniority = "mid"
            
        return {
            "position": "Position",
            "seniority": seniority,
            "required_skills": found_skills,
            "required_experience_years": experience_years,
            "key_requirements": "Pattern-based analysis"
        }

    def quick_relevance_check(self, job_requirements: Dict[str, Any], cv_text: str) -> Tuple[bool, float]:
        """Fast pre-filtering to identify promising CVs before expensive AI analysis."""
        if not cv_text or len(cv_text.strip()) < 100:
            return False, 0.0
        
        cv_lower = cv_text.lower()
        job_skills = job_requirements.get('required_skills', [])
        
        # Count skill matches
        skill_matches = sum(1 for skill in job_skills if skill.lower() in cv_lower)
        skill_score = (skill_matches / len(job_skills)) * 100 if job_skills else 0
        
        # Check for experience level match
        exp_score = 0
        required_exp = job_requirements.get('required_experience_years', 0)
        if required_exp:
            # Look for experience indicators
            exp_patterns = [r'(\d+)\+?\s*years?\s*(?:of\s*)?experience', r'(\d+)\+?\s*years?\s*in']
            for pattern in exp_patterns:
                match = re.search(pattern, cv_lower)
                if match:
                    cv_exp = int(match.group(1))
                    if cv_exp >= required_exp * 0.7:  # 70% of required experience
                        exp_score = 30
                    break
        
        # Look for position-related keywords
        position_keywords = job_requirements.get('position', '').lower().split()
        position_matches = sum(1 for keyword in position_keywords if len(keyword) > 2 and keyword in cv_lower)
        position_score = min(20, position_matches * 5)
        
        total_score = skill_score + exp_score + position_score
        is_relevant = total_score >= 25  # Threshold for AI processing
        
        return is_relevant, total_score

    def compress_cv_text(self, cv_text: str) -> str:
        """Extract and compress most relevant CV sections for AI analysis."""
        if len(cv_text) <= 3000:
            return cv_text
        
        # Extract key sections in order of importance
        sections = []
        
        # Try to find and extract summary/objective (first 500 chars usually)
        summary_section = cv_text[:500]
        sections.append(summary_section)
        
        # Look for skills section
        skills_patterns = [
            r'(?i)(skills?|technical skills?|core competencies)[:\-\s]*([^\n]*(?:\n[^\n]*){0,10})',
            r'(?i)(technologies?|programming)[:\-\s]*([^\n]*(?:\n[^\n]*){0,5})'
        ]
        
        for pattern in skills_patterns:
            match = re.search(pattern, cv_text)
            if match:
                sections.append(match.group(0))
                break
        
        # Look for experience section (take recent experience)
        exp_patterns = [
            r'(?i)(experience|employment|work history)[:\-\s]*([^\n]*(?:\n[^\n]*){0,15})',
            r'(?i)(current position|recent role)[:\-\s]*([^\n]*(?:\n[^\n]*){0,10})'
        ]
        
        for pattern in exp_patterns:
            match = re.search(pattern, cv_text)
            if match:
                sections.append(match.group(0))
                break
        
        # Look for education (brief)
        edu_match = re.search(r'(?i)(education|qualification)[:\-\s]*([^\n]*(?:\n[^\n]*){0,5})', cv_text)
        if edu_match:
            sections.append(edu_match.group(0))
        
        compressed = '\n\n'.join(sections)
        return compressed[:3000]  # Hard limit

    def analyze_cv_with_combined_ai(self, cv_text: str, job_requirements: Dict[str, Any]) -> Tuple[Dict[str, Any], float, Dict[str, Any]]:
        """Single AI call combining CV analysis and matching for maximum efficiency."""
        if not self.openai_client:
            return self._analyze_cv_fallback(cv_text, job_requirements)
        
        try:
            # Compress CV text to reduce token usage
            compressed_cv = self.compress_cv_text(cv_text)
            
            # Single comprehensive prompt for analysis and scoring
            prompt = f"""Analyze CV vs Job in one response. Return ONLY valid JSON:

Job Requirements:
- Position: {job_requirements.get('position', 'Unknown')}
- Seniority: {job_requirements.get('seniority', 'mid')}
- Required Skills: {', '.join(job_requirements.get('required_skills', [])[:10])}
- Experience: {job_requirements.get('required_experience_years', 'Not specified')} years

CV Content:
{compressed_cv}

Return JSON:
{{
    "candidate_name": "full name from CV",
    "professional_summary": "2-sentence career summary",
    "technical_skills": ["list of ALL technical skills found"],
    "experience_years": "total experience as number or null",
    "seniority_level": "junior/mid/senior",
    "education": ["degrees and certifications"],
    "overall_score": 75,
    "match_category": "excellent_match/good_match/average_match/poor_match",
    "strengths": "Key strengths for this role",
    "gaps": "Main missing requirements",
    "recommendation": "Brief hiring recommendation"
}}

Score 90-100: Perfect match; 70-89: Good match; 50-69: Average; <50: Poor match"""

            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",  # Faster model
                messages=[{"role": "user", "content": prompt}],
                max_tokens=800,  # Optimized token count
                temperature=0.1,
                top_p=0.95
            )
            
            ai_response = response.choices[0].message.content.strip()
            
            try:
                combined_analysis = json.loads(ai_response)
                
                # Extract components
                cv_analysis = {
                    "candidate_name": combined_analysis.get('candidate_name', 'Unknown'),
                    "professional_summary": combined_analysis.get('professional_summary', ''),
                    "technical_skills": combined_analysis.get('technical_skills', []),
                    "experience_years": combined_analysis.get('experience_years'),
                    "seniority_level": combined_analysis.get('seniority_level', 'mid'),
                    "education": combined_analysis.get('education', [])
                }
                
                score = float(combined_analysis.get('overall_score', 50))
                score = max(0, min(100, score))
                
                match_analysis = {
                    "overall_score": score,
                    "match_category": combined_analysis.get('match_category', 'average_match'),
                    "detailed_analysis": {
                        "strengths_summary": combined_analysis.get('strengths', ''),
                        "gaps_summary": combined_analysis.get('gaps', ''),
                        "skill_matches": [skill for skill in cv_analysis['technical_skills'] if any(req_skill.lower() in skill.lower() for req_skill in job_requirements.get('required_skills', []))],
                        "skill_gaps": [skill for skill in job_requirements.get('required_skills', []) if not any(skill.lower() in cv_skill.lower() for cv_skill in cv_analysis['technical_skills'])]
                    },
                    "recommendation_summary": combined_analysis.get('recommendation', ''),
                    "key_selling_points": [combined_analysis.get('strengths', '')[:100]],
                    "concerns": [combined_analysis.get('gaps', '')[:100]] if combined_analysis.get('gaps') else []
                }
                
                print(f"  ✅ Combined AI analysis: {cv_analysis['candidate_name']} - {score:.1f}%")
                return cv_analysis, score, match_analysis
                
            except json.JSONDecodeError as e:
                print(f"⚠️ JSON parse error in combined analysis: {e}")
                return self._analyze_cv_fallback(cv_text, job_requirements)
                
        except Exception as e:
            print(f"❌ Combined AI analysis failed: {e}")
            return self._analyze_cv_fallback(cv_text, job_requirements)

    def _analyze_cv_fallback(self, cv_text: str, job_requirements: Dict[str, Any]) -> Tuple[Dict[str, Any], float, Dict[str, Any]]:
        """Fast fallback analysis without AI."""
        cv_analysis = {
            "candidate_name": document_parser.extract_candidate_name(cv_text) or "Unknown",
            "professional_summary": document_parser.extract_complete_summary(cv_text) or "Professional summary not available",
            "technical_skills": document_parser.extract_skills_section(cv_text) or [],
            "experience_years": document_parser.extract_experience_years(cv_text),
            "seniority_level": "mid",
            "education": []
        }
        
        # Quick scoring based on keyword overlap
        job_skills = job_requirements.get('required_skills', [])
        cv_skills = cv_analysis['technical_skills']
        matched_skills = [skill for skill in job_skills if any(skill.lower() in cv_skill.lower() for cv_skill in cv_skills)]
        
        score = (len(matched_skills) / len(job_skills)) * 80 + 20 if job_skills else 50
        
        match_analysis = {
            "overall_score": score,
            "match_category": "good_match" if score >= 70 else "average_match" if score >= 50 else "poor_match",
            "detailed_analysis": {
                "strengths_summary": f"Candidate has experience with {', '.join(matched_skills[:3])}",
                "gaps_summary": f"May need development in {', '.join(set(job_skills) - set(matched_skills))}",
                "skill_matches": matched_skills,
                "skill_gaps": list(set(job_skills) - set(matched_skills))
            },
            "recommendation_summary": "Requires detailed technical interview to assess fit",
            "key_selling_points": ["Experience with relevant technologies"],
            "concerns": ["Limited automated analysis available"]
        }
        
        return cv_analysis, score, match_analysis

    def process_cv_batch(self, cv_batch: List[Dict], job_requirements: Dict[str, Any], db: Session, user_id: int) -> List[Dict]:
        """Process a batch of CVs with optimized performance."""
        results = []
        
        for cv_data in cv_batch:
            try:
                file_info = cv_data['file_info']
                print(f"  📄 Processing: {file_info['name']}")
                
                # Download file content
                file_content = google_drive_service.download_file(db, user_id, file_info['id'])
                if not file_content:
                    continue
                
                # Extract text
                cv_text = document_parser.extract_text_from_file(file_content, file_info['name'])
                if not cv_text or len(cv_text.strip()) < 100:
                    continue
                
                # Quick relevance check
                is_relevant, quick_score = self.quick_relevance_check(job_requirements, cv_text)
                if not is_relevant:
                    print(f"    ⏭️ Skipped (quick score: {quick_score:.1f})")
                    continue
                
                # Combined AI analysis
                cv_analysis, relevance_score, match_analysis = self.analyze_cv_with_combined_ai(cv_text, job_requirements)
                
                # Only include if score is reasonable
                if relevance_score < 30:
                    print(f"    ⏭️ Low score: {relevance_score:.1f}%")
                    continue
                
                result = {
                    "file_info": file_info,
                    "cv_analysis": cv_analysis,
                    "match_analysis": match_analysis,
                    "relevance_score": relevance_score
                }
                results.append(result)
                print(f"    ✅ Score: {relevance_score:.1f}%")
                
            except Exception as e:
                print(f"    ❌ Error: {e}")
                continue
        
        return results

    def process_optimized_cv_matching(self, db: Session, user_id: int, job_description: str) -> Dict[str, Any]:
        """Optimized Resume matching with all performance improvements."""
        start_time = time.time()
        
        # Validate setup
        user_config = db.query(UserConfig).filter(UserConfig.user_id == user_id).first()
        if not user_config:
            raise Exception("User configuration not found")
        
        openai_key = self.get_openai_key(db, user_id)
        if not openai_key:
            raise Exception("OpenAI API key not configured")
        
        self.initialize_openai_client(openai_key)
        
        if not user_config.google_drive_token:
            return self._create_error_response("google_drive_not_configured", 
                                             "Google Drive not configured")
        
        # Cached job analysis (major optimization)
        print("🧠 Analyzing job requirements...")
        job_requirements = self.extract_job_requirements_cached(job_description)
        job_analysis_time = time.time() - start_time
        print(f"⚡ Job analysis completed in {job_analysis_time:.2f}s")
        
        # Get CV files
        cv_folder = user_config.cv_folder_name or "cvs"
        files = google_drive_service.list_files_in_folder(db, user_id, cv_folder)
        
        if not files:
            return self._create_error_response("no_files_found", 
                                             f"No files found in '{cv_folder}' folder", cv_folder)
        
        print(f"🚀 Processing {len(files)} CVs with optimized parallel matching...")
        
        # Create match log
        match_log = MatchLog(
            user_id=user_id,
            job_description=job_description,
            total_cvs_processed=0
        )
        db.add(match_log)
        db.commit()
        db.refresh(match_log)
        
        # Parallel processing with optimized batch size
        all_results = []
        batch_size = 4  # Optimal balance of speed vs resource usage
        max_workers = 3  # Conservative threading for API limits
        
        # Prepare file data for parallel processing
        file_batches = [files[i:i + batch_size] for i in range(0, len(files), batch_size)]
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all batches for parallel processing
            future_to_batch = {
                executor.submit(
                    self.process_cv_batch, 
                    [{"file_info": f} for f in batch], 
                    job_requirements, 
                    db, 
                    user_id
                ): batch_idx 
                for batch_idx, batch in enumerate(file_batches)
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_batch):
                batch_idx = future_to_batch[future]
                try:
                    batch_results = future.result(timeout=60)  # 60s timeout per batch
                    all_results.extend(batch_results)
                    print(f"📦 Batch {batch_idx + 1} completed: {len(batch_results)} candidates")
                except Exception as e:
                    print(f"❌ Batch {batch_idx + 1} failed: {e}")
        
        processing_time = time.time() - start_time
        print(f"⚡ Parallel processing completed in {processing_time:.2f}s")
        
        if not all_results:
            match_log.total_cvs_processed = 0
            db.commit()
            return self._create_no_matches_response(match_log.id, len(files), cv_folder, job_requirements)
        
        # Sort and limit to top candidates
        all_results.sort(key=lambda x: x['relevance_score'], reverse=True)
        top_results = all_results[:8]  # Limit to top 8 for optimal performance
        
        print(f"🏆 Selected top {len(top_results)} candidates from {len(all_results)} qualified")
        
        # Batch database operations (major optimization)
        match_results_data = []
        formatted_results = []
        
        for result in top_results:
            file_info = result['file_info']
            cv_analysis = result['cv_analysis']
            match_analysis = result['match_analysis']
            relevance_score = result['relevance_score']
            
            # Prepare database record
            match_results_data.append({
                "match_log_id": match_log.id,
                "cv_filename": file_info['name'],
                "candidate_name": cv_analysis['candidate_name'],
                "candidate_summary": cv_analysis['professional_summary'],
                "relevance_score": relevance_score,
                "google_drive_file_id": file_info['id'],
                "download_url": file_info.get('webContentLink'),
                "key_skills": json.dumps(cv_analysis['technical_skills']),
                "match_analysis": json.dumps(match_analysis),
                "experience_years": cv_analysis.get('experience_years'),
                "is_top_match": relevance_score >= 70
            })
            
            # Prepare response format
            formatted_result = {
                "cv_filename": file_info['name'],
                "candidate_name": cv_analysis['candidate_name'],
                "candidate_summary": cv_analysis['professional_summary'],
                "relevance_score": round(relevance_score, 1),
                "match_status": self._convert_category_to_status(match_analysis['match_category']),
                "download_url": file_info.get('webContentLink'),
                "google_drive_file_id": file_info['id'],
                "key_skills": cv_analysis['technical_skills'],
                "match_analysis": self._format_match_analysis_optimized(match_analysis),
                "experience_years": cv_analysis.get('experience_years')
            }
            formatted_results.append(formatted_result)
        
        # Bulk insert (major database optimization)
        if match_results_data:
            db.bulk_insert_mappings(MatchResult, match_results_data)
            db.commit()
            print(f"💾 Bulk saved {len(match_results_data)} results to database")
        
        # Update match log
        match_log.total_cvs_processed = len(top_results)
        match_log.top_matches_count = len([r for r in top_results if r['relevance_score'] >= 70])
        db.commit()
        
        # Generate summary
        summary_report = self._generate_optimized_summary(top_results, job_requirements, len(files))
        
        total_time = time.time() - start_time
        print(f"🎉 Optimized matching completed in {total_time:.2f}s (was ~{total_time*3:.1f}s before)")
        
        return {
            "results": formatted_results,
            "match_id": match_log.id,
            "total_cvs_processed": len(top_results),
            "top_matches_count": match_log.top_matches_count,
            "status": "success",
            "message": summary_report['overall_summary'],
            "folder_name": cv_folder,
            "enhanced_summary": {
                "search_effectiveness": summary_report['search_effectiveness'],
                "total_cvs_reviewed": len(files),
                "total_relevant_matches": len(top_results),
                "recommendations": summary_report['recommendations'],
                "excellent_matches": len([r for r in top_results if r['relevance_score'] >= 80]),
                "good_matches": len([r for r in top_results if 60 <= r['relevance_score'] < 80]),
                "average_matches": len([r for r in top_results if 40 <= r['relevance_score'] < 60]),
                "total_relevant": len(top_results),
                "total_reviewed": len(files),
                "position": job_requirements.get('position', 'Unknown'),
                "required_skills": job_requirements.get('required_skills', []),
                "seniority_level": job_requirements.get('seniority', 'Unknown'),
                "processing_time": f"{total_time:.2f}s"
            }
        }

    def _convert_category_to_status(self, category: str) -> str:
        """Convert AI category to frontend status."""
        status_map = {
            "excellent_match": "best_match",
            "good_match": "good_match", 
            "average_match": "average_match",
            "poor_match": "low_match"
        }
        return status_map.get(category, "average_match")

    def _format_match_analysis_optimized(self, match_analysis: Dict) -> str:
        """Format match analysis for frontend display."""
        parts = []
        
        detailed = match_analysis.get('detailed_analysis', {})
        if detailed.get('strengths_summary'):
            parts.append(f"🟢 STRENGTHS: {detailed['strengths_summary']}")
        
        if detailed.get('gaps_summary'):
            parts.append(f"🔴 GAPS: {detailed['gaps_summary']}")
            
        if match_analysis.get('recommendation_summary'):
            parts.append(f"💡 RECOMMENDATION: {match_analysis['recommendation_summary']}")
        
        return " | ".join(parts) if parts else "Analysis completed."

    def _generate_optimized_summary(self, results: List[Dict], job_requirements: Dict, total_files: int) -> Dict[str, Any]:
        """Generate summary report optimized for performance."""
        if not results:
            return {
                "overall_summary": f"No suitable candidates found among {total_files} CVs.",
                "search_effectiveness": "no_matches",
                "recommendations": ["Broaden requirements", "Check CV folder contents"]
            }
        
        excellent = len([r for r in results if r['relevance_score'] >= 80])
        good = len([r for r in results if 60 <= r['relevance_score'] < 80])
        
        if excellent > 0:
            effectiveness = "excellent"
            summary = f"Found {excellent} excellent candidate(s) from {total_files} CVs reviewed."
            recommendations = ["Focus interviews on top candidates", "Assess cultural fit"]
        elif good > 0:
            effectiveness = "good"
            summary = f"Found {good} good candidate(s) from {total_files} CVs reviewed."
            recommendations = ["Consider skills training for gaps", "Evaluate learning potential"]
        else:
            effectiveness = "moderate"
            summary = f"Found {len(results)} moderate candidate(s) from {total_files} CVs reviewed."
            recommendations = ["Consider expanding criteria", "Look for transferable skills"]
        
        return {
            "overall_summary": summary,
            "search_effectiveness": effectiveness,
            "recommendations": recommendations
        }

    def _create_error_response(self, status: str, message: str, folder_name: str = None) -> Dict[str, Any]:
        """Create standardized error response."""
        return {
            "results": [],
            "match_id": None,
            "total_cvs_processed": 0,
            "top_matches_count": 0,
            "status": status,
            "message": message,
            "folder_name": folder_name,
            "enhanced_summary": {
                "search_effectiveness": "setup_required",
                "total_cvs_reviewed": 0,
                "total_relevant_matches": 0,
                "recommendations": ["Complete setup requirements"],
                "excellent_matches": 0,
                "good_matches": 0,
                "average_matches": 0,
                "total_relevant": 0,
                "total_reviewed": 0
            }
        }

    def _create_no_matches_response(self, match_id: int, total_files: int, folder_name: str, job_requirements: Dict) -> Dict[str, Any]:
        """Create response for no matches found."""
        return {
            "results": [],
            "match_id": match_id,
            "total_cvs_processed": 0,
            "top_matches_count": 0,
            "status": "no_matches_found",
            "message": f"No suitable candidates found among {total_files} CVs reviewed.",
            "folder_name": folder_name,
            "enhanced_summary": {
                "search_effectiveness": "no_matches",
                "total_cvs_reviewed": total_files,
                "total_relevant_matches": 0,
                "recommendations": [
                    "Consider broadening the job requirements",
                    "Review CV folder contents for relevance",
                    "Adjust required experience levels"
                ],
                "position": job_requirements.get('position', 'Unknown'),
                "required_skills": job_requirements.get('required_skills', []),
                "seniority_level": job_requirements.get('seniority', 'Unknown'),
                "excellent_matches": 0,
                "good_matches": 0, 
                "average_matches": 0,
                "total_relevant": 0,
                "total_reviewed": total_files
            }
        }

# Create optimized service instance
optimized_cv_matching_service = OptimizedCVMatchingService()