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
from concurrent.futures import ThreadPoolExecutor
import threading

class EnhancedCVMatchingService:
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
        print(f"🔑 Initializing OpenAI client with API key: {api_key[:10]}...")
        try:
            import httpx
            http_client = httpx.Client(
                timeout=60.0,
                limits=httpx.Limits(max_keepalive_connections=10, max_connections=100),
                follow_redirects=True
            )
            
            self.openai_client = openai.OpenAI(
                api_key=api_key,
                http_client=http_client,
                timeout=45.0
            )
            print("✅ Enhanced OpenAI client initialized successfully")
            
            # Test the client with a simple call
            test_response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "Reply with just 'OK' to confirm connection."}],
                max_tokens=5,
                temperature=0
            )
            print(f"🧪 OpenAI Test Response: {test_response.choices[0].message.content}")
            
        except Exception as e:
            print(f"❌ Error initializing OpenAI client: {e}")
            self.openai_client = None
            raise Exception(f"Failed to initialize OpenAI client: {e}")

    def extract_job_requirements_with_ai(self, job_description: str) -> Dict[str, Any]:
        """Use AI to intelligently extract job requirements."""
        if not self.openai_client:
            return self._extract_job_requirements_fallback(job_description)
        
        try:
            prompt = f"""
Analyze this job description and extract detailed requirements. Return ONLY a JSON object:

{{
    "position_title": "extracted job title",
    "seniority_level": "junior/mid/senior/executive",
    "required_skills": ["list of explicitly REQUIRED skills/technologies"],
    "preferred_skills": ["list of PREFERRED/nice-to-have skills"],
    "required_experience_years": "number or null",
    "required_qualifications": ["degrees, certifications explicitly required"],
    "job_responsibilities": ["main duties and responsibilities"],
    "industry_type": "technology/finance/healthcare/etc",
    "work_type": "remote/hybrid/onsite/not_specified",
    "key_requirements_summary": "concise summary of what makes an ideal candidate"
}}

JOB DESCRIPTION:
{job_description}

Focus on what is explicitly REQUIRED vs just mentioned. Be precise.
"""

            # Always use the new OpenAI client format
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=800,
                temperature=0.1
            )
            ai_response = response.choices[0].message.content

            try:
                print(f"📝 Raw AI Response for Job Requirements: {ai_response}")
                requirements = json.loads(ai_response)
                print(f"🧠 AI extracted job requirements: {requirements.get('position_title', 'Unknown Position')}")
                return requirements
            except json.JSONDecodeError as e:
                print(f"⚠️ Could not parse AI job requirements: {e}")
                print(f"📝 Raw response that failed: {ai_response}")
                print("⚠️ Using fallback job requirements")
                return self._extract_job_requirements_fallback(job_description)
                
        except Exception as e:
            print(f"❌ AI job extraction failed: {e}")
            return self._extract_job_requirements_fallback(job_description)

    def _extract_job_requirements_fallback(self, job_description: str) -> Dict[str, Any]:
        """Fallback job requirements extraction using pattern matching."""
        text = job_description.lower()
        
        # Extract experience years
        exp_match = re.search(r'(\d+)\+?\s*years?\s*(?:of\s*)?experience', text)
        experience_years = int(exp_match.group(1)) if exp_match else None
        
        # Determine seniority
        if any(word in text for word in ['senior', 'lead', 'principal', 'architect', 'manager']):
            seniority = "senior"
        elif any(word in text for word in ['junior', 'entry', 'graduate', 'intern']):
            seniority = "junior"
        else:
            seniority = "mid"
            
        # Basic tech skills extraction
        tech_skills = []
        skill_patterns = ['python', 'javascript', 'java', 'react', 'angular', 'vue', 'sql', 'mongodb', 'docker', 'aws', 'azure', 'git']
        for skill in skill_patterns:
            if skill in text:
                tech_skills.append(skill)
        
        return {
            "position_title": "Position",
            "seniority_level": seniority,
            "required_skills": tech_skills,
            "preferred_skills": [],
            "required_experience_years": experience_years,
            "required_qualifications": [],
            "job_responsibilities": [],
            "industry_type": "technology",
            "work_type": "not_specified",
            "key_requirements_summary": "Pattern-based analysis of job requirements"
        }

    def analyze_cv_with_ai(self, cv_text: str, job_requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced CV analysis using AI with job context."""
        if not self.openai_client:
            return self._analyze_cv_fallback(cv_text)
        
        try:
            prompt = f"""
Analyze this CV comprehensively. Consider the job requirements context for better analysis.

JOB CONTEXT:
- Position: {job_requirements.get('position_title', 'Unknown')}
- Seniority: {job_requirements.get('seniority_level', 'Unknown')}
- Required Skills: {', '.join(job_requirements.get('required_skills', []))}

Return ONLY a JSON object:
{{
    "candidate_name": "extracted full name",
    "professional_summary": "2-3 sentence summary of candidate's profile",
    "technical_skills": ["ALL technical skills, tools, languages, frameworks found"],
    "experience_years": "total years of experience as number or null",
    "seniority_level": "junior/mid/senior based on roles and experience",
    "education": ["degrees, certifications, institutions"],
    "key_achievements": ["notable accomplishments or projects"],
    "relevant_experience": ["work experiences most relevant to the job"],
    "strengths_for_role": ["specific strengths that match the target job"],
    "industry_background": "main industries worked in"
}}

CV TEXT:
{cv_text[:8000]}

Be thorough in extracting ALL technical skills mentioned anywhere in the CV.
"""

            # Always use the new OpenAI client format
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1000,
                temperature=0.1
            )
            ai_response = response.choices[0].message.content

            try:
                print(f"📝 Raw AI Response for CV Analysis: {ai_response}")
                cv_analysis = json.loads(ai_response)
                print(f"🧠 AI analyzed CV: {cv_analysis.get('candidate_name', 'Unknown Candidate')}")
                return cv_analysis
            except json.JSONDecodeError as e:
                print(f"⚠️ Could not parse AI CV analysis: {e}")
                print(f"📝 Raw response that failed: {ai_response}")
                print("⚠️ Using fallback CV analysis")
                return self._analyze_cv_fallback(cv_text)
                
        except Exception as e:
            print(f"❌ AI CV analysis failed: {e}")
            return self._analyze_cv_fallback(cv_text)

    def _analyze_cv_fallback(self, cv_text: str) -> Dict[str, Any]:
        """Fallback CV analysis using document parser."""
        return {
            "candidate_name": document_parser.extract_candidate_name(cv_text) or "Unknown Candidate",
            "professional_summary": document_parser.extract_complete_summary(cv_text),
            "technical_skills": document_parser.extract_skills_section(cv_text),
            "experience_years": document_parser.extract_experience_years(cv_text),
            "seniority_level": "mid",
            "education": [],
            "key_achievements": [],
            "relevant_experience": [],
            "strengths_for_role": [],
            "industry_background": "Unknown"
        }

    def calculate_intelligent_match_score(self, job_requirements: Dict[str, Any], cv_analysis: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
        """Calculate intelligent match score with detailed analysis."""
        if not self.openai_client:
            return self._calculate_fallback_score(job_requirements, cv_analysis)
        
        try:
            prompt = f"""
You are a senior HR professional with 15+ years of experience in technical recruitment. Provide a comprehensive candidate assessment that will be read by hiring managers and technical leads.

JOB REQUIREMENTS:
Position: {job_requirements.get('position_title', 'Unknown')}
Seniority Level: {job_requirements.get('seniority_level', 'Unknown')}
Required Skills: {', '.join(job_requirements.get('required_skills', []))}
Preferred Skills: {', '.join(job_requirements.get('preferred_skills', []))}
Required Experience: {job_requirements.get('required_experience_years', 'Not specified')} years
Key Requirements: {job_requirements.get('key_requirements_summary', 'See above')}

CANDIDATE PROFILE:
Name: {cv_analysis.get('candidate_name', 'Unknown')}
Experience: {cv_analysis.get('experience_years', 'Unknown')} years
Seniority: {cv_analysis.get('seniority_level', 'Unknown')}
Technical Skills: {', '.join(cv_analysis.get('technical_skills', [])[:20])}
Relevant Experience: {', '.join(cv_analysis.get('relevant_experience', [])[:3])}
Education: {', '.join(cv_analysis.get('education', [])[:2])}

SCORING GUIDELINES:
- 90-100%: Exceeds requirements, perfect match with bonus qualifications
- 80-89%: Meets ALL key requirements, minor gaps in secondary areas
- 70-79%: Meets most requirements, some gaps in important areas
- 60-69%: Meets basic requirements, notable gaps in key skills
- 40-59%: Missing several important requirements
- 20-39%: Significant gaps in fundamental requirements
- 0-19%: Poor match, lacks most basic requirements

IMPORTANT: Write professional, actionable summaries that hiring managers can use for decision-making.

Return ONLY a JSON object:
{{
    "overall_score": 75,
    "match_category": "excellent_match/good_match/average_match/poor_match",
    "detailed_analysis": {{
        "strengths_summary": "Professional paragraph highlighting the candidate's top 3-4 strengths that directly align with job requirements. Focus on specific skills, experience depth, and unique value propositions.",
        "gaps_summary": "Professional paragraph identifying key missing requirements or areas where the candidate may need development. Be constructive and specific about what's lacking.",
        "skill_matches": ["Required skills the candidate has"],
        "skill_gaps": ["Required skills the candidate lacks"],
        "experience_assessment": "Assessment of experience level vs requirements",
        "education_match": "How education aligns with requirements"
    }},
    "recommendation_summary": "Professional paragraph with a clear hiring recommendation. Include specific reasoning, potential fit for the role, and next steps. Be decisive but balanced.",
    "key_selling_points": ["Top 3-4 reasons to consider this candidate"],
    "concerns": ["Main concerns or areas needing development"],
    "interview_focus": ["Key areas to explore in interview"]
}}

Write in a professional, executive summary style. Each summary should be 2-4 sentences that a busy hiring manager can quickly digest.
"""

            # Always use the new OpenAI client format
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1200,
                temperature=0.1
            )
            ai_response = response.choices[0].message.content

            try:
                print(f"📝 Raw AI Response for Match Analysis: {ai_response}")
                match_analysis = json.loads(ai_response)
                score = float(match_analysis.get('overall_score', 50))
                score = max(0, min(100, score))  # Ensure score is within valid range
                
                print(f"🎯 AI Match Score: {score}% ({match_analysis.get('match_category', 'unknown')})")
                return score, match_analysis
                
            except json.JSONDecodeError as e:
                print(f"⚠️ Could not parse AI match analysis: {e}")
                print(f"📝 Raw response that failed: {ai_response}")
                print("⚠️ Using fallback match analysis")
                return self._calculate_fallback_score(job_requirements, cv_analysis)
                
        except Exception as e:
            print(f"❌ AI match scoring failed: {e}")
            return self._calculate_fallback_score(job_requirements, cv_analysis)

    def _calculate_fallback_score(self, job_requirements: Dict[str, Any], cv_analysis: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
        """Fallback scoring method with professional summaries."""
        score = 50.0
        required_skills = job_requirements.get('required_skills', [])
        candidate_skills = cv_analysis.get('technical_skills', [])
        matched_skills = []
        
        if required_skills and candidate_skills:
            matched_skills = [skill for skill in required_skills if any(skill.lower() in cs.lower() for cs in candidate_skills)]
            score = (len(matched_skills) / len(required_skills)) * 80 + 20
        
        # Generate professional fallback summaries
        candidate_name = cv_analysis.get('candidate_name', 'This candidate')
        position = job_requirements.get('position_title', 'the position')
        
        strengths_summary = f"{candidate_name} demonstrates relevant technical capabilities with skills in {', '.join(candidate_skills[:3]) if candidate_skills else 'various areas'}. The candidate's background shows potential alignment with {position} requirements."
        
        if score >= 60:
            gaps_summary = f"While {candidate_name} meets many basic requirements, some technical skills may need verification during the interview process. Additional training in specific tools or methodologies might be beneficial."
            recommendation_summary = f"This candidate shows promise for {position} and merits further evaluation. Recommend proceeding with technical interview to assess depth of experience and cultural fit."
        else:
            gaps_summary = f"{candidate_name} appears to lack several key technical requirements for {position}. Significant skill gaps may require extensive training or development to meet role expectations."
            recommendation_summary = f"While {candidate_name} has some relevant experience, the skill gaps are substantial for {position}. Consider for alternative roles or if willing to invest in significant skill development."
        
        analysis = {
            "overall_score": score,
            "match_category": "average_match" if score >= 60 else "poor_match",
            "detailed_analysis": {
                "strengths_summary": strengths_summary,
                "gaps_summary": gaps_summary,
                "skill_matches": matched_skills,
                "skill_gaps": [skill for skill in required_skills if skill not in matched_skills],
                "experience_assessment": "Assessment based on available CV information and pattern matching",
                "education_match": "Educational background not fully analyzed in fallback mode"
            },
            "recommendation_summary": recommendation_summary,
            "key_selling_points": [f"Experience with {', '.join(matched_skills[:2])}", "Shows learning potential", "Available for interview"],
            "concerns": ["Limited automated analysis", "Requires manual skill verification"],
            "interview_focus": ["Verify technical proficiency", "Assess learning capability", "Evaluate project experience"]
        }
        
        return score, analysis

    def generate_summary_report(self, match_results: List[Dict], job_requirements: Dict[str, Any], total_files: int) -> Dict[str, Any]:
        """Generate an intelligent summary report of all matches."""
        
        if not match_results:
            return {
                "overall_summary": f"No suitable candidates found among {total_files} CVs reviewed.",
                "search_effectiveness": "no_matches",
                "recommendations": [
                    "Consider broadening the job requirements",
                    "Review if the CV folder contains relevant profiles",
                    "Consider adjusting required experience levels",
                    "Expand the search to include related skills"
                ],
                "next_steps": [
                    "Review job description for overly restrictive requirements",
                    "Consider alternative skill combinations",
                    "Expand recruitment channels"
                ]
            }
        
        # Analyze match distribution
        excellent_matches = [r for r in match_results if r['relevance_score'] >= 80]
        good_matches = [r for r in match_results if 60 <= r['relevance_score'] < 80]
        average_matches = [r for r in match_results if 40 <= r['relevance_score'] < 60]
        
        # Generate intelligent summary
        if excellent_matches:
            search_effectiveness = "excellent"
            summary = f"Found {len(excellent_matches)} excellent candidate(s) among {len(match_results)} relevant profiles from {total_files} CVs reviewed."
        elif good_matches:
            search_effectiveness = "good"
            summary = f"Found {len(good_matches)} good candidate(s) among {len(match_results)} relevant profiles from {total_files} CVs reviewed."
        elif average_matches:
            search_effectiveness = "moderate"
            summary = f"Found {len(average_matches)} moderate candidate(s) among {len(match_results)} relevant profiles from {total_files} CVs reviewed."
        else:
            search_effectiveness = "limited"
            summary = f"Found {len(match_results)} candidates with limited relevance from {total_files} CVs reviewed."
        
        # Generate recommendations
        recommendations = []
        if excellent_matches:
            recommendations.extend([
                f"Prioritize interviews with the top {min(3, len(excellent_matches))} candidates",
                "Focus on cultural fit and specific project experience in interviews"
            ])
        elif good_matches:
            recommendations.extend([
                "Consider skills training for good matches to fill minor gaps",
                "Evaluate candidates based on learning potential and motivation"
            ])
        else:
            recommendations.extend([
                "Consider revising job requirements or expanding search criteria",
                "Look for candidates with transferable skills",
                "Consider remote candidates or alternative experience backgrounds"
            ])
        
        return {
            "overall_summary": summary,
            "search_effectiveness": search_effectiveness,
            "excellent_matches": len(excellent_matches),
            "good_matches": len(good_matches),
            "average_matches": len(average_matches),
            "total_relevant": len(match_results),
            "total_reviewed": total_files,
            "recommendations": recommendations,
            "top_candidate_summary": self._generate_top_candidate_summary(match_results[:3]) if match_results else None
        }

    def _generate_top_candidate_summary(self, top_candidates: List[Dict]) -> str:
        """Generate a summary of top candidates."""
        if not top_candidates:
            return "No top candidates identified."
        
        summaries = []
        for i, candidate in enumerate(top_candidates[:3], 1):
            name = candidate.get('candidate_name', f'Candidate {i}')
            score = candidate.get('relevance_score', 0)
            summary = f"{i}. {name} ({score:.1f}% match)"
            summaries.append(summary)
        
        return " | ".join(summaries)

    def process_enhanced_cv_matching(self, db: Session, user_id: int, job_description: str) -> Dict[str, Any]:
        """Enhanced CV matching with intelligent analysis and better formatting."""
        start_time = time.time()
        
        # Get user config and validate setup
        user_config = db.query(UserConfig).filter(UserConfig.user_id == user_id).first()
        if not user_config:
            raise Exception("User configuration not found")
        
        openai_key = self.get_openai_key(db, user_id)
        if not openai_key:
            raise Exception("OpenAI API key not configured")
        
        self.initialize_openai_client(openai_key)
        
        if not user_config.google_drive_token:
            return {
                "results": [],
                "match_id": None,
                "total_cvs_processed": 0,
                "top_matches_count": 0,
                "status": "google_drive_not_configured",
                "message": "Google Drive not configured. Please set up Google Drive access first.",
                "enhanced_summary": {
                    "search_effectiveness": "setup_required",
                    "total_cvs_reviewed": 0,
                    "total_relevant_matches": 0,
                    "recommendations": ["Complete Google Drive setup in the configuration section"],
                    "excellent_matches": 0,
                    "good_matches": 0,
                    "average_matches": 0,
                    "total_relevant": 0,
                    "total_reviewed": 0
                }
            }
        
        # Extract job requirements using AI
        print("🧠 Analyzing job description with AI...")
        print(f"📝 Job Description Input: {job_description[:200]}...")
        print(f"🔑 OpenAI Client Status: {type(self.openai_client)}")
        job_requirements = self.extract_job_requirements_with_ai(job_description)
        print(f"✅ Job Requirements Extracted: {job_requirements}")
        
        # Get CV files
        cv_folder = user_config.cv_folder_name or "cvs"
        files = google_drive_service.list_files_in_folder(db, user_id, cv_folder)
        
        if not files:
            return {
                "results": [],
                "match_id": None,
                "total_cvs_processed": 0,
                "top_matches_count": 0,
                "status": "no_files_found",
                "message": f"No CV files found in the '{cv_folder}' folder. Please upload CV files to your Google Drive folder.",
                "folder_name": cv_folder,
                "enhanced_summary": {
                    "search_effectiveness": "no_files",
                    "total_cvs_reviewed": 0,
                    "total_relevant_matches": 0,
                    "recommendations": [
                        f"Upload CV files to your '{cv_folder}' Google Drive folder",
                        "Ensure files are in PDF, DOC, or DOCX format",
                        "Check that the folder name matches your configuration"
                    ],
                    "excellent_matches": 0,
                    "good_matches": 0,
                    "average_matches": 0,
                    "total_relevant": 0,
                    "total_reviewed": 0
                }
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
        
        print(f"🚀 Processing {len(files)} CVs with enhanced AI matching...")
        
        # OPTIMIZATION: Collect all CVs for scoring first, then filter and limit
        all_cv_results = []
        processed_results = []
        
        # PERFORMANCE OPTIMIZATION: Process CVs in smaller batches
        batch_size = 3  # Process 3 CVs at a time to balance speed vs resource usage
        
        for batch_start in range(0, len(files), batch_size):
            batch_files = files[batch_start:batch_start + batch_size]
            print(f"📦 Processing batch {batch_start//batch_size + 1} ({len(batch_files)} CVs)...")
            
            for i, file_info in enumerate(batch_files, batch_start + 1):
                try:
                    print(f"📄 Processing CV {i}/{len(files)}: {file_info['name']}")
                    
                    # Download and extract text
                    file_content = google_drive_service.download_file(db, user_id, file_info['id'])
                    if not file_content:
                        continue
                
                    cv_text = document_parser.extract_text_from_file(file_content, file_info['name'])
                    print(f"  📄 CV Text Length: {len(cv_text) if cv_text else 0} characters")
                    print(f"  📝 CV Text Preview: {cv_text[:300] if cv_text else 'NO TEXT'}...")
                    if not cv_text or len(cv_text.strip()) < 100:
                        print(f"  ⚠️ Insufficient text content extracted")
                        continue
                    
                    # OPTIMIZATION: Quick pre-filter for exact matches and relevance
                    job_desc_lower = job_description.lower()
                    cv_text_lower = cv_text.lower()
                    
                    # Check for exact string match with better algorithm
                    job_phrases = [phrase.strip() for phrase in job_desc_lower.split() if len(phrase.strip()) > 3]
                    exact_phrase_matches = sum(1 for phrase in job_phrases if phrase in cv_text_lower)
                    exact_match_percentage = (exact_phrase_matches / len(job_phrases)) * 100 if job_phrases else 0
                    
                    # Check for substring match (copied text)
                    job_sentences = [s.strip() for s in job_description.split('.') if len(s.strip()) > 20]
                    has_sentence_match = any(sentence.lower() in cv_text_lower for sentence in job_sentences)
                    
                    print(f"  🔍 Exact match analysis: {exact_match_percentage:.1f}% phrase matches, sentence match: {has_sentence_match}")
                    
                    # AI-powered CV analysis
                    print(f"  🧠 Starting AI CV analysis for {file_info['name']}...")
                    cv_analysis = self.analyze_cv_with_ai(cv_text, job_requirements)
                    print(f"  ✅ CV Analysis Result: {cv_analysis}")
                    
                    # AI-powered match scoring
                    print(f"  🎯 Starting AI match scoring...")
                    relevance_score, match_analysis = self.calculate_intelligent_match_score(job_requirements, cv_analysis)
                    print(f"  📊 Match Analysis Result: {match_analysis}")
                    
                    # BOOST SCORE for exact matches (this fixes the exact match issue)
                    if has_sentence_match or exact_match_percentage > 70:
                        boost = min(25, (100 - relevance_score) * 0.5)  # Boost by up to 25 points
                        relevance_score = min(95, relevance_score + boost)  # Cap at 95%
                        print(f"  🚀 EXACT MATCH BOOST: Score boosted to {relevance_score:.1f}%")
                    
                    # OPTIMIZATION: Only proceed if score >= 50% OR has string match
                    has_string_match = exact_match_percentage > 30 or has_sentence_match
                    if relevance_score < 50 and not has_string_match:
                        print(f"  ⏭️ Skipping CV (score: {relevance_score:.1f}%, no significant match)")
                        continue
                    
                    # Skip very low relevance matches (keep original threshold for safety)
                    if relevance_score < 20:
                        print(f"  ⏭️ Skipping low relevance match: {relevance_score:.1f}%")
                        continue
                    
                    # Store CV data for potential inclusion in top 6
                    cv_data = {
                        "file_info": file_info,
                        "cv_analysis": cv_analysis,
                        "match_analysis": match_analysis,
                        "relevance_score": relevance_score,
                        "cv_text": cv_text,
                        "has_string_match": has_string_match,
                        "exact_match_percentage": exact_match_percentage,
                        "has_sentence_match": has_sentence_match
                    }
                    all_cv_results.append(cv_data)
                    
                    print(f"  ✅ Qualified CV: {relevance_score:.1f}% ({'EXACT MATCH' if has_sentence_match else 'with string match' if has_string_match else 'score ≥50%'})")
                
                except Exception as e:
                    print(f"❌ Error processing {file_info['name']}: {e}")
                    continue
            
            # OPTIMIZATION: Early termination if we have enough high-scoring candidates
            if len(all_cv_results) >= 12:  # Collect more than 6 to ensure good selection
                all_cv_results.sort(key=lambda x: x['relevance_score'], reverse=True)
                if all_cv_results[5]['relevance_score'] >= 80:  # If 6th best is already 80%+
                    print(f"⚡ EARLY TERMINATION: Found {len(all_cv_results)} high-quality candidates, stopping batch processing")
                    break
        
        # OPTIMIZATION: Sort all qualified CVs and take top 6
        all_cv_results.sort(key=lambda x: x['relevance_score'], reverse=True)
        top_cvs = all_cv_results[:6]  # Limit to maximum 6 CVs
        
        print(f"🏆 Selected {len(top_cvs)} top CVs from {len(all_cv_results)} qualified candidates for detailed processing")
        
        # Process the top CVs for final results
        for cv_data in top_cvs:
            file_info = cv_data['file_info']
            cv_analysis = cv_data['cv_analysis']
            match_analysis = cv_data['match_analysis']
            relevance_score = cv_data['relevance_score']
            
            # Create structured result with professional summaries
            detailed_analysis = match_analysis.get('detailed_analysis', {})
            result = {
                "cv_filename": file_info['name'],
                "candidate_name": cv_analysis.get('candidate_name', 'Unknown Candidate'),
                "professional_summary": cv_analysis.get('professional_summary', 'Summary not available'),
                "relevance_score": round(relevance_score, 1),
                "match_category": match_analysis.get('match_category', 'unknown'),
                "technical_skills": cv_analysis.get('technical_skills', []),
                "experience_years": cv_analysis.get('experience_years'),
                "education": cv_analysis.get('education', []),
                "strengths": detailed_analysis.get('strengths_summary', 'Professional strengths assessment not available'),
                "gaps": detailed_analysis.get('gaps_summary', 'Areas for development assessment not available'),
                "recommendation": match_analysis.get('recommendation_summary', 'Professional recommendation not available'),
                "key_selling_points": match_analysis.get('key_selling_points', []),
                "concerns": match_analysis.get('concerns', []),
                "google_drive_file_id": file_info['id'],
                "download_url": file_info.get('webContentLink')
            }
            
            # Save to database
            match_result = MatchResult(
                match_log_id=match_log.id,
                cv_filename=file_info['name'],
                candidate_name=result['candidate_name'],
                candidate_summary=result['professional_summary'],
                relevance_score=relevance_score,
                google_drive_file_id=file_info['id'],
                download_url=result['download_url'],
                key_skills=json.dumps(result['technical_skills']),
                match_analysis=json.dumps(match_analysis),
                experience_years=result['experience_years']
            )
            
            db.add(match_result)
            processed_results.append(result)
            
            print(f"  💾 Saved top CV: {result['candidate_name']} ({relevance_score:.1f}%)")
        
        # Commit all results
        db.commit()
        
        # Update match log with actual counts
        match_log.total_cvs_processed = len(processed_results)
        match_log.top_matches_count = len([r for r in processed_results if r['relevance_score'] >= 70])
        db.commit()
        
        print(f"📦 Final results: {len(processed_results)} CVs processed and saved to database")
        
        # Handle case where no relevant matches were found
        if not processed_results:
            match_log.total_cvs_processed = 0
            db.commit()
            
            return {
                "results": [],
                "match_id": match_log.id,
                "total_cvs_processed": 0,
                "top_matches_count": 0,
                "status": "no_matches_found",
                "message": f"No suitable candidates found among {len(files)} CVs reviewed. Consider broadening the job requirements or reviewing the CV folder contents.",
                "folder_name": cv_folder,
                "enhanced_summary": {
                    "search_effectiveness": "no_matches",
                    "total_cvs_reviewed": len(files),
                    "total_relevant_matches": 0,
                    "recommendations": [
                        "Consider broadening the job requirements",
                        "Review if the CV folder contains relevant profiles",
                        "Adjust required experience levels",
                        "Expand the search to include related skills"
                    ],
                    "position": job_requirements.get('position_title', 'Unknown'),
                    "required_skills": job_requirements.get('required_skills', []),
                    "seniority_level": job_requirements.get('seniority_level', 'Unknown'),
                    "excellent_matches": 0,
                    "good_matches": 0,
                    "average_matches": 0,
                    "total_relevant": 0,
                    "total_reviewed": len(files)
                }
            }
        
        # Results are already sorted from the top CVs selection
        # processed_results.sort(key=lambda x: x['relevance_score'], reverse=True) # No need to sort again
        
        # Generate intelligent summary
        summary_report = self.generate_summary_report(processed_results, job_requirements, len(files))
        
        processing_time = time.time() - start_time
        print(f"🎉 Enhanced matching completed in {processing_time:.2f}s")
        
        # Format results for compatibility with existing frontend
        formatted_results = []
        for result in processed_results:
            formatted_result = {
                "cv_filename": result["cv_filename"],
                "candidate_name": result["candidate_name"],
                "candidate_summary": result["professional_summary"],
                "relevance_score": result["relevance_score"],
                "match_status": self._convert_category_to_status(result["match_category"]),
                "download_url": result.get("download_url"),
                "google_drive_file_id": result["google_drive_file_id"],
                "key_skills": result["technical_skills"],
                "match_analysis": self._format_match_analysis(result),
                "experience_years": result.get("experience_years")
            }
            formatted_results.append(formatted_result)
        
        return {
            "results": formatted_results,
            "match_id": match_log.id,
            "total_cvs_processed": len(processed_results),
            "top_matches_count": len([r for r in processed_results if r['relevance_score'] >= 70]),
            "status": "success",
            "message": summary_report['overall_summary'],
            "folder_name": cv_folder,
            # Enhanced information
            "enhanced_summary": {
                "search_effectiveness": summary_report['search_effectiveness'],
                "total_cvs_reviewed": len(files),
                "total_relevant_matches": len(processed_results),
                "recommendations": summary_report['recommendations'],
                "top_candidate_summary": summary_report.get('top_candidate_summary'),
                "excellent_matches": len([r for r in processed_results if r['relevance_score'] >= 80]),
                "good_matches": len([r for r in processed_results if 60 <= r['relevance_score'] < 80]),
                "average_matches": len([r for r in processed_results if 40 <= r['relevance_score'] < 60]),
                "total_relevant": len(processed_results),
                "total_reviewed": len(files),
                "position": job_requirements.get('position_title', 'Unknown'),
                "required_skills": job_requirements.get('required_skills', []),
                "seniority_level": job_requirements.get('seniority_level', 'Unknown'),
                "processing_time": f"{processing_time:.2f}s"
            }
        }

    def _convert_category_to_status(self, category: str) -> str:
        """Convert AI category to frontend-compatible status."""
        if category == "excellent_match":
            return "best_match"
        elif category == "good_match":
            return "good_match"
        elif category == "average_match":
            return "average_match"
        else:
            return "low_match"

    def _format_match_analysis(self, result: Dict) -> str:
        """Format the match analysis into a professional, readable summary."""
        analysis_parts = []
        
        # Handle strengths - should be a professional paragraph
        if result.get("strengths"):
            strengths_text = str(result['strengths']) if not isinstance(result['strengths'], list) else '. '.join(result['strengths'][:3])
            analysis_parts.append(f"🟢 STRENGTHS: {strengths_text}")
        
        # Handle gaps - should be a professional paragraph  
        if result.get("gaps"):
            gaps_text = str(result['gaps']) if not isinstance(result['gaps'], list) else '. '.join(result['gaps'][:2])
            analysis_parts.append(f"🔴 GAPS: {gaps_text}")
        
        # Handle recommendation - should be a professional paragraph
        if result.get("recommendation"):
            recommendation_text = str(result['recommendation'])
            analysis_parts.append(f"💡 RECOMMENDATION: {recommendation_text}")
        
        # Join with pipe separator (frontend will handle proper formatting and spacing)
        return " | ".join(analysis_parts) if analysis_parts else "Professional analysis completed."

# Create service instance
enhanced_cv_matching_service = EnhancedCVMatchingService()