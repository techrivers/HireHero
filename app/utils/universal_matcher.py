"""
Universal AI-Powered CV Matching System
Works with ANY job role without hardcoded skill databases
Uses AI for dynamic skill extraction and intelligent matching
"""

import re
import json
from typing import List, Dict, Set, Tuple, Optional, Any
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

class UniversalCVMatcher:
    def __init__(self):
        """Initialize universal matcher with AI capabilities."""
        self.openai_client = None
        # API key will be set dynamically from user config
        
    def _get_openai_client(self, db, user_id):
        """Get OpenAI client using user's configured API key."""
        try:
            from app.services.user_config_service import user_config_service
            from app.utils.encryption import encryption_service
            
            user_config = user_config_service.get_user_config(db, user_id)
            if not user_config or not user_config.openai_api_key:
                print("⚠️ OpenAI API key not configured for user - using fallback matching")
                return None
            
            # Decrypt the API key
            decrypted_key = encryption_service.decrypt(user_config.openai_api_key)
            if not decrypted_key:
                print("⚠️ Failed to decrypt OpenAI API key - using fallback matching")
                return None
            
            return OpenAI(api_key=decrypted_key)
            
        except Exception as e:
            print(f"⚠️ Error getting OpenAI client: {e}")
            return None
    
    def extract_job_requirements_ai(self, job_description: str, db=None, user_id=None) -> Dict[str, Any]:
        """Extract job requirements using AI - works for ANY role."""
        openai_client = self._get_openai_client(db, user_id) if db and user_id else None
        if not openai_client:
            return self._fallback_job_extraction(job_description)
        
        try:
            prompt = f"""
            Analyze this job description and extract ALL relevant requirements, skills, and criteria.
            Work with ANY job type (technical, non-technical, management, creative, etc.)
            
            Job Description: {job_description}
            
            Extract and return JSON with:
            {{
                "job_title": "extracted title",
                "role_category": "software_development|product_management|data_science|design|marketing|hr|finance|operations|etc",
                "seniority_level": "entry|junior|mid|senior|lead|principal|director|vp",
                "required_skills": ["skill1", "skill2", ...],
                "preferred_skills": ["skill1", "skill2", ...],
                "technical_skills": ["tech_skill1", "tech_skill2", ...],
                "soft_skills": ["communication", "leadership", ...],
                "tools_technologies": ["tool1", "tool2", ...],
                "experience_requirements": {{
                    "min_years": number,
                    "max_years": number,
                    "specific_experience": ["type1", "type2", ...]
                }},
                "education_requirements": ["degree_type", ...],
                "key_responsibilities": ["resp1", "resp2", ...],
                "industry_domain": "fintech|healthcare|ecommerce|etc",
                "work_type": "remote|onsite|hybrid",
                "employment_type": "full_time|part_time|contract|internship"
            }}
            
            Be comprehensive and extract EVERYTHING relevant. Return only valid JSON.
            """
            
            response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=1500
            )
            
            content = response.choices[0].message.content.strip()
            if content.startswith('```json'):
                content = content[7:-3]
            elif content.startswith('```'):
                content = content[3:-3]
            
            return json.loads(content)
            
        except Exception as e:
            print(f"❌ AI job extraction failed: {e}")
            return self._fallback_job_extraction(job_description)
    
    def _fallback_job_extraction(self, job_description: str) -> Dict[str, Any]:
        """Fallback job extraction without AI."""
        text_lower = job_description.lower()
        
        # Basic seniority detection
        if any(word in text_lower for word in ['senior', 'lead', 'principal', 'staff']):
            seniority = 'senior'
        elif any(word in text_lower for word in ['junior', 'entry', 'graduate', 'intern']):
            seniority = 'junior'
        else:
            seniority = 'mid'
        
        # Basic years extraction
        years_match = re.search(r'(\d+)\+?\s*years?', text_lower)
        min_years = int(years_match.group(1)) if years_match else 2
        
        # Basic role category detection
        role_category = 'software_development'  # default
        if any(word in text_lower for word in ['product', 'manager', 'pm']):
            role_category = 'product_management'
        elif any(word in text_lower for word in ['data', 'analyst', 'analytics']):
            role_category = 'data_science'
        elif any(word in text_lower for word in ['design', 'ui', 'ux']):
            role_category = 'design'
        elif any(word in text_lower for word in ['marketing', 'content', 'social']):
            role_category = 'marketing'
        
        return {
            "job_title": "Unknown Role",
            "role_category": role_category,
            "seniority_level": seniority,
            "required_skills": [],
            "preferred_skills": [],
            "technical_skills": [],
            "soft_skills": [],
            "tools_technologies": [],
            "experience_requirements": {"min_years": min_years, "max_years": min_years + 5},
            "education_requirements": [],
            "key_responsibilities": [],
            "industry_domain": "technology",
            "work_type": "full_time",
            "employment_type": "full_time"
        }
    
    def extract_cv_profile_ai(self, cv_text: str, db=None, user_id=None) -> Dict[str, Any]:
        """Extract comprehensive CV profile using AI - works for ANY role."""
        openai_client = self._get_openai_client(db, user_id) if db and user_id else None
        if not openai_client:
            return self._fallback_cv_extraction(cv_text)
        
        try:
            # Limit CV text to avoid token limits
            cv_text_limited = cv_text[:4000]
            
            prompt = f"""
            Analyze this CV/resume and extract a comprehensive profile.
            Work with ANY professional background (technical, non-technical, management, creative, etc.)
            
            CV Text: {cv_text_limited}
            
            Extract and return JSON with:
            {{
                "candidate_name": "extracted name",
                "professional_summary": "2-3 sentence summary",
                "role_category": "software_development|product_management|data_science|design|marketing|hr|finance|operations|etc",
                "seniority_level": "entry|junior|mid|senior|lead|principal|director|vp",
                "total_experience_years": number,
                "technical_skills": ["skill1", "skill2", ...],
                "soft_skills": ["communication", "leadership", ...],
                "tools_technologies": ["tool1", "tool2", ...],
                "programming_languages": ["lang1", "lang2", ...],
                "frameworks_libraries": ["framework1", "framework2", ...],
                "databases": ["db1", "db2", ...],
                "cloud_platforms": ["platform1", "platform2", ...],
                "certifications": ["cert1", "cert2", ...],
                "education": [{{
                    "degree": "degree_type",
                    "field": "field_of_study",
                    "institution": "university_name"
                }}],
                "work_experience": [{{
                    "title": "job_title",
                    "company": "company_name",
                    "duration": "years",
                    "key_achievements": ["achievement1", "achievement2"]
                }}],
                "key_strengths": ["strength1", "strength2", ...],
                "industry_experience": ["industry1", "industry2", ...],
                "project_experience": ["project_type1", "project_type2", ...],
                "management_experience": "yes|no",
                "team_size_managed": number,
                "languages": ["language1", "language2", ...]
            }}
            
            Be comprehensive and extract EVERYTHING mentioned. Return only valid JSON.
            """
            
            response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=2000
            )
            
            content = response.choices[0].message.content.strip()
            if content.startswith('```json'):
                content = content[7:-3]
            elif content.startswith('```'):
                content = content[3:-3]
            
            return json.loads(content)
            
        except Exception as e:
            print(f"❌ AI CV extraction failed: {e}")
            print(f"❌ CV text length: {len(cv_text)} chars")
            print(f"❌ CV text preview: {cv_text[:200]}...")
            import traceback
            traceback.print_exc()
            return self._fallback_cv_extraction(cv_text)
    
    def _fallback_cv_extraction(self, cv_text: str) -> Dict[str, Any]:
        """Fallback CV extraction without AI."""
        # Extract name (first line or first few words)
        lines = cv_text.split('\n')
        candidate_name = "Unknown Candidate"
        for line in lines[:5]:
            line = line.strip()
            if len(line) > 5 and len(line.split()) <= 4:
                candidate_name = line
                break
        
        # Basic years extraction
        years_matches = re.findall(r'(\d+)\+?\s*years?', cv_text.lower())
        total_years = max([int(y) for y in years_matches], default=0)
        
        return {
            "candidate_name": candidate_name,
            "professional_summary": "Extracted from CV analysis",
            "role_category": "unknown",
            "seniority_level": "mid",
            "total_experience_years": total_years,
            "technical_skills": [],
            "soft_skills": [],
            "tools_technologies": [],
            "programming_languages": [],
            "frameworks_libraries": [],
            "databases": [],
            "cloud_platforms": [],
            "certifications": [],
            "education": [],
            "work_experience": [],
            "key_strengths": [],
            "industry_experience": [],
            "project_experience": [],
            "management_experience": "no",
            "team_size_managed": 0,
            "languages": []
        }
    
    def calculate_universal_match_score(self, job_requirements: Dict, cv_profile: Dict, db=None, user_id=None) -> Dict[str, Any]:
        """Calculate match score using AI - works for ANY role combination."""
        openai_client = self._get_openai_client(db, user_id) if db and user_id else None
        if not openai_client:
            return self._fallback_scoring(job_requirements, cv_profile)
        
        try:
            prompt = f"""
            Calculate a comprehensive match score between this job and candidate.
            Consider ALL aspects of fit, not just technical skills.
            
            Job Requirements:
            {json.dumps(job_requirements, indent=2)}
            
            Candidate Profile:
            {json.dumps(cv_profile, indent=2)}
            
            Analyze and return JSON with:
            {{
                "overall_score": number_0_to_100,
                "skill_match_score": number_0_to_100,
                "experience_match_score": number_0_to_100,
                "seniority_match_score": number_0_to_100,
                "role_fit_score": number_0_to_100,
                "cultural_fit_score": number_0_to_100,
                "detailed_analysis": {{
                    "strengths": ["strength1", "strength2", ...],
                    "weaknesses": ["weakness1", "weakness2", ...],
                    "skill_gaps": ["gap1", "gap2", ...],
                    "skill_overlaps": ["overlap1", "overlap2", ...],
                    "experience_relevance": "high|medium|low",
                    "growth_potential": "high|medium|low"
                }},
                "recommendation": "strong_match|good_match|potential_match|poor_match",
                "reasoning": "Detailed explanation of why this candidate matches or doesn't match"
            }}
            
            Be thorough and realistic in scoring. Return only valid JSON.
            """
            
            response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=1500
            )
            
            content = response.choices[0].message.content.strip()
            if content.startswith('```json'):
                content = content[7:-3]
            elif content.startswith('```'):
                content = content[3:-3]
            
            return json.loads(content)
            
        except Exception as e:
            print(f"❌ AI scoring failed: {e}")
            print(f"❌ Job requirements: {job_requirements.get('job_title', 'Unknown')}")
            print(f"❌ CV profile candidate: {cv_profile.get('candidate_name', 'Unknown')}")
            import traceback
            traceback.print_exc()
            return self._fallback_scoring(job_requirements, cv_profile)
    
    def _fallback_scoring(self, job_requirements: Dict, cv_profile: Dict) -> Dict[str, Any]:
        """Fallback scoring without AI."""
        # Basic scoring logic
        score = 50  # Base score
        
        # Experience match
        job_years = job_requirements.get('experience_requirements', {}).get('min_years', 2)
        cv_years = cv_profile.get('total_experience_years', 0)
        if cv_years >= job_years:
            score += 20
        elif cv_years >= job_years * 0.8:
            score += 10
        
        # Role category match
        if job_requirements.get('role_category') == cv_profile.get('role_category'):
            score += 20
        
        # Seniority match
        job_seniority = job_requirements.get('seniority_level', 'mid')
        cv_seniority = cv_profile.get('seniority_level', 'mid')
        if job_seniority == cv_seniority:
            score += 10
        
        return {
            "overall_score": min(100, max(0, score)),
            "skill_match_score": score,
            "experience_match_score": score,
            "seniority_match_score": score,
            "role_fit_score": score,
            "cultural_fit_score": 70,
            "detailed_analysis": {
                "strengths": ["Professional experience"],
                "weaknesses": ["Limited analysis without AI"],
                "skill_gaps": [],
                "skill_overlaps": [],
                "experience_relevance": "medium",
                "growth_potential": "medium"
            },
            "recommendation": "potential_match",
            "reasoning": "Basic scoring - configure OpenAI for detailed analysis"
        }
    
    def intelligent_prefilter_universal(self, job_description: str, cv_text: str) -> Tuple[bool, Dict]:
        """Universal pre-filter that works for any role."""
        if not job_description or not cv_text:
            return False, {'reason': 'Missing text'}
        
        # Very basic text overlap scoring
        job_words = set(re.findall(r'\b[a-zA-Z]{3,}\b', job_description.lower()))
        cv_words = set(re.findall(r'\b[a-zA-Z]{3,}\b', cv_text.lower()))
        
        overlap = len(job_words.intersection(cv_words))
        job_word_count = len(job_words)
        
        overlap_ratio = overlap / job_word_count if job_word_count > 0 else 0
        
        # Very lenient filtering - let most CVs through for AI analysis
        passes = overlap_ratio >= 0.1 or overlap >= 5
        
        analysis = {
            'passes_filter': passes,
            'overlap_score': round(overlap_ratio, 3),
            'word_overlap_count': overlap,
            'job_word_count': job_word_count,
            'cv_word_count': len(cv_words),
            'reason': f'Word overlap: {overlap}/{job_word_count} words'
        }
        
        return passes, analysis

# Global instance
universal_matcher = UniversalCVMatcher()