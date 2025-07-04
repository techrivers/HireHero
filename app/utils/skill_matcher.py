"""
Advanced Skill Matching and Experience Validation Module
Provides semantic skill matching, experience level validation, and intelligent pre-filtering
"""

import re
import spacy
from typing import List, Dict, Set, Tuple, Optional
from collections import Counter
import logging
from sentence_transformers import SentenceTransformer
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AdvancedSkillMatcher:
    def __init__(self):
        """Initialize the skill matcher with NLP models and skill databases."""
        try:
            # Load spaCy model for NLP processing
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            logger.warning("spaCy model not found. Install with: python -m spacy download en_core_web_sm")
            self.nlp = None
        
        try:
            # Load sentence transformer for semantic similarity
            self.sentence_model = SentenceTransformer('all-MiniLM-L6-v2')
        except Exception as e:
            logger.warning(f"Could not load sentence transformer: {e}")
            self.sentence_model = None
        
        # Comprehensive skill databases
        self.tech_skills_db = {
            # Programming Languages
            'programming': [
                'python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'php', 'ruby', 'go', 'rust',
                'kotlin', 'swift', 'scala', 'r', 'matlab', 'perl', 'shell', 'bash', 'powershell'
            ],
            # Web Technologies
            'web': [
                'html', 'css', 'react', 'angular', 'vue', 'node.js', 'express', 'django', 'flask',
                'spring', 'laravel', 'bootstrap', 'jquery', 'webpack', 'sass', 'less'
            ],
            # Databases
            'databases': [
                'mysql', 'postgresql', 'mongodb', 'redis', 'elasticsearch', 'oracle', 'sql server',
                'sqlite', 'cassandra', 'dynamodb', 'firebase', 'neo4j'
            ],
            # Cloud & DevOps
            'cloud': [
                'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'jenkins', 'gitlab', 'terraform',
                'ansible', 'chef', 'puppet', 'nginx', 'apache', 'linux', 'ubuntu'
            ],
            # Data Science & AI
            'data_science': [
                'machine learning', 'deep learning', 'neural networks', 'tensorflow', 'pytorch',
                'scikit-learn', 'pandas', 'numpy', 'matplotlib', 'seaborn', 'jupyter', 'tableau',
                'power bi', 'spark', 'hadoop', 'kafka'
            ],
            # Mobile Development
            'mobile': [
                'android', 'ios', 'react native', 'flutter', 'xamarin', 'ionic', 'cordova'
            ],
            # Testing
            'testing': [
                'unit testing', 'integration testing', 'selenium', 'cypress', 'jest', 'pytest',
                'junit', 'mocha', 'chai', 'testng'
            ]
        }
        
        # Flatten all skills for easy searching
        self.all_skills = set()
        for category_skills in self.tech_skills_db.values():
            self.all_skills.update(category_skills)
        
        # Experience level patterns
        self.experience_patterns = {
            'senior': [
                r'senior\s+(?:software\s+)?(?:engineer|developer|architect)',
                r'lead\s+(?:software\s+)?(?:engineer|developer)',
                r'principal\s+(?:software\s+)?(?:engineer|developer)',
                r'staff\s+(?:software\s+)?(?:engineer|developer)',
                r'tech\s+lead', r'technical\s+lead',
                r'(\d+)\+?\s*years?\s+(?:of\s+)?experience',
                r'(\d+)\+?\s*years?\s+(?:in|with)',
            ],
            'mid': [
                r'(?:software\s+)?(?:engineer|developer)(?:\s+ii|\s+2)?',
                r'(\d+)\s*-?\s*(\d+)\s*years?\s+(?:of\s+)?experience',
                r'intermediate\s+(?:software\s+)?(?:engineer|developer)',
            ],
            'junior': [
                r'junior\s+(?:software\s+)?(?:engineer|developer)',
                r'entry\s+level', r'graduate\s+(?:software\s+)?(?:engineer|developer)',
                r'intern(?:ship)?', r'trainee',
                r'(\d+)\s*(?:months?|years?)\s+(?:of\s+)?experience',
            ],
            'intern': [
                r'intern(?:ship)?', r'trainee', r'co-op', r'student',
                r'graduate\s+(?:software\s+)?(?:engineer|developer)',
            ]
        }
        
    def extract_skills_from_text(self, text: str) -> Set[str]:
        """Extract technical skills from text using multiple approaches."""
        if not text:
            return set()
        
        text_lower = text.lower()
        found_skills = set()
        
        # 1. Direct skill matching
        for skill in self.all_skills:
            # Use word boundaries for better matching
            pattern = r'\b' + re.escape(skill.lower()) + r'\b'
            if re.search(pattern, text_lower):
                found_skills.add(skill)
        
        # 2. Common skill variations and synonyms
        skill_variations = {
            'javascript': ['js', 'node.js', 'nodejs'],
            'postgresql': ['postgres', 'psql'],
            'machine learning': ['ml', 'artificial intelligence', 'ai'],
            'deep learning': ['dl', 'neural networks', 'cnn', 'rnn'],
            'react native': ['react-native'],
            'node.js': ['nodejs', 'node js'],
            'c++': ['cpp', 'c plus plus'],
            'c#': ['csharp', 'c sharp'],
        }
        
        for main_skill, variations in skill_variations.items():
            for variation in variations:
                pattern = r'\b' + re.escape(variation.lower()) + r'\b'
                if re.search(pattern, text_lower):
                    found_skills.add(main_skill)
        
        # 3. Framework and library specific matching
        framework_patterns = {
            'react': [r'\breact\b', r'\breactjs\b', r'\breact\.js\b'],
            'angular': [r'\bangular\b', r'\bangularjs\b'],
            'vue': [r'\bvue\b', r'\bvuejs\b', r'\bvue\.js\b'],
            'django': [r'\bdjango\b'],
            'flask': [r'\bflask\b'],
            'spring': [r'\bspring\s+boot\b', r'\bspring\s+framework\b', r'\bspring\b'],
        }
        
        for skill, patterns in framework_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    found_skills.add(skill)
        
        return found_skills
    
    def extract_experience_level(self, text: str) -> Tuple[str, int]:
        """Extract experience level and years from text."""
        if not text:
            return 'unknown', 0
        
        text_lower = text.lower()
        max_years = 0
        detected_level = 'unknown'
        
        # Extract years of experience
        year_patterns = [
            r'(\d+)\+?\s*years?\s+(?:of\s+)?experience',
            r'(\d+)\+?\s*years?\s+(?:in|with)',
            r'experience[:\s]+(\d+)\+?\s*years?',
            r'(\d+)\+?\s*yrs?\s+(?:exp|experience)',
        ]
        
        for pattern in year_patterns:
            matches = re.findall(pattern, text_lower)
            for match in matches:
                years = int(match)
                max_years = max(max_years, years)
        
        # Determine level based on patterns and years
        for level, patterns in self.experience_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text_lower, re.IGNORECASE):
                    detected_level = level
                    break
        
        # Override with years-based classification if available
        if max_years > 0:
            if max_years >= 8:
                detected_level = 'senior'
            elif max_years >= 4:
                detected_level = 'mid'
            elif max_years >= 1:
                detected_level = 'junior'
            else:
                detected_level = 'intern'
        
        return detected_level, max_years
    
    def semantic_skill_similarity(self, job_skills: Set[str], cv_skills: Set[str]) -> float:
        """Calculate semantic similarity between job and CV skills using embeddings."""
        if not self.sentence_model or not job_skills or not cv_skills:
            # Fallback to simple overlap
            intersection = len(job_skills.intersection(cv_skills))
            union = len(job_skills.union(cv_skills))
            return intersection / union if union > 0 else 0.0
        
        try:
            # Convert skills to sentences for better embeddings
            job_skills_text = ' '.join(job_skills)
            cv_skills_text = ' '.join(cv_skills)
            
            # Generate embeddings
            job_embedding = self.sentence_model.encode([job_skills_text])
            cv_embedding = self.sentence_model.encode([cv_skills_text])
            
            # Calculate cosine similarity
            similarity = cosine_similarity(job_embedding, cv_embedding)[0][0]
            return float(similarity)
        
        except Exception as e:
            logger.warning(f"Semantic similarity calculation failed: {e}")
            # Fallback to Jaccard similarity
            intersection = len(job_skills.intersection(cv_skills))
            union = len(job_skills.union(cv_skills))
            return intersection / union if union > 0 else 0.0
    
    def validate_experience_compatibility(self, job_level: str, job_years: int, 
                                        cv_level: str, cv_years: int) -> Tuple[bool, float]:
        """Validate if CV experience matches job requirements."""
        # Experience level hierarchy
        level_hierarchy = {
            'intern': 0,
            'junior': 1,
            'mid': 2,
            'senior': 3,
            'unknown': 1  # Default to mid-level
        }
        
        job_level_score = level_hierarchy.get(job_level, 1)
        cv_level_score = level_hierarchy.get(cv_level, 1)
        
        # Calculate compatibility score
        level_diff = abs(job_level_score - cv_level_score)
        year_diff = abs(job_years - cv_years) if job_years > 0 and cv_years > 0 else 0
        
        # Scoring logic
        if level_diff == 0:
            level_compatibility = 1.0
        elif level_diff == 1:
            level_compatibility = 0.7
        elif level_diff == 2:
            level_compatibility = 0.4
        else:
            level_compatibility = 0.1
        
        # Year-based adjustment
        if job_years > 0 and cv_years > 0:
            if year_diff <= 1:
                year_compatibility = 1.0
            elif year_diff <= 3:
                year_compatibility = 0.8
            elif year_diff <= 5:
                year_compatibility = 0.6
            else:
                year_compatibility = 0.3
        else:
            year_compatibility = 0.8  # Neutral if years not specified
        
        # Combined score
        compatibility_score = (level_compatibility * 0.6) + (year_compatibility * 0.4)
        
        # Is compatible if score > 0.5
        is_compatible = compatibility_score >= 0.5
        
        return is_compatible, compatibility_score
    
    def intelligent_prefilter(self, job_description: str, cv_text: str, 
                            strict_mode: bool = False) -> Tuple[bool, Dict]:
        """Intelligent pre-filtering with detailed scoring."""
        if not job_description or not cv_text:
            return False, {'reason': 'Missing text'}
        
        # Extract skills
        job_skills = self.extract_skills_from_text(job_description)
        cv_skills = self.extract_skills_from_text(cv_text)
        
        # Extract experience levels
        job_level, job_years = self.extract_experience_level(job_description)
        cv_level, cv_years = self.extract_experience_level(cv_text)
        
        # Calculate skill similarity
        skill_similarity = self.semantic_skill_similarity(job_skills, cv_skills)
        
        # Validate experience compatibility
        exp_compatible, exp_score = self.validate_experience_compatibility(
            job_level, job_years, cv_level, cv_years
        )
        
        # Calculate overall pre-filter score
        skill_weight = 0.7
        exp_weight = 0.3
        
        overall_score = (skill_similarity * skill_weight) + (exp_score * exp_weight)
        
        # Determine filtering thresholds
        if strict_mode:
            skill_threshold = 0.4
            exp_threshold = 0.5
            overall_threshold = 0.6
        else:
            skill_threshold = 0.2
            exp_threshold = 0.3
            overall_threshold = 0.4
        
        # Filter decision
        passes_filter = (
            skill_similarity >= skill_threshold and
            exp_score >= exp_threshold and
            overall_score >= overall_threshold
        )
        
        # Detailed analysis
        analysis = {
            'passes_filter': passes_filter,
            'overall_score': round(overall_score, 3),
            'skill_similarity': round(skill_similarity, 3),
            'experience_compatibility': round(exp_score, 3),
            'job_skills': list(job_skills),
            'cv_skills': list(cv_skills),
            'skill_overlap': list(job_skills.intersection(cv_skills)),
            'job_experience': {'level': job_level, 'years': job_years},
            'cv_experience': {'level': cv_level, 'years': cv_years},
            'experience_compatible': exp_compatible
        }
        
        return passes_filter, analysis

# Global instance
skill_matcher = AdvancedSkillMatcher()