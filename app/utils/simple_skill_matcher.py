"""
Simple Skill Matching Module (Fallback)
Provides basic skill matching without heavy ML dependencies
"""

import re
from typing import List, Dict, Set, Tuple, Optional
from collections import Counter

class SimpleSkillMatcher:
    def __init__(self):
        """Initialize with basic skill databases."""
        self.tech_skills_db = {
            # Technical Programming Skills
            'programming': [
                'python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'php', 'ruby', 'go', 'rust',
                'kotlin', 'swift', 'scala', 'r', 'matlab', 'perl', 'shell', 'bash', 'powershell'
            ],
            'web': [
                'html', 'css', 'react', 'angular', 'vue', 'node.js', 'express', 'django', 'flask',
                'spring', 'laravel', 'bootstrap', 'jquery', 'webpack', 'sass', 'less'
            ],
            'databases': [
                'mysql', 'postgresql', 'mongodb', 'redis', 'elasticsearch', 'oracle', 'sql server',
                'sqlite', 'cassandra', 'dynamodb', 'firebase', 'neo4j'
            ],
            'cloud': [
                'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'jenkins', 'gitlab', 'terraform',
                'ansible', 'chef', 'puppet', 'nginx', 'apache', 'linux', 'ubuntu'
            ],
            'data_science': [
                'machine learning', 'deep learning', 'neural networks', 'tensorflow', 'pytorch',
                'scikit-learn', 'pandas', 'numpy', 'matplotlib', 'seaborn', 'jupyter', 'tableau'
            ],
            'mobile': [
                'android', 'ios', 'react native', 'flutter', 'xamarin', 'ionic'
            ],
            # Content Writing & Marketing Skills
            'content_writing': [
                'content writing', 'content creation', 'copywriting', 'technical writing', 'creative writing',
                'blog writing', 'article writing', 'web content', 'seo writing', 'marketing copy'
            ],
            'digital_marketing': [
                'digital marketing', 'social media marketing', 'seo', 'sem', 'google ads', 'facebook ads',
                'email marketing', 'content marketing', 'affiliate marketing', 'influencer marketing'
            ],
            'social_media': [
                'social media', 'facebook', 'instagram', 'twitter', 'linkedin', 'youtube', 'tiktok',
                'social media management', 'community management', 'social media strategy'
            ],
            'project_management': [
                'project management', 'agile', 'scrum', 'kanban', 'waterfall', 'jira', 'trello',
                'asana', 'monday.com', 'ms project', 'gantt charts', 'risk management'
            ],
            'business_analysis': [
                'business analysis', 'requirements gathering', 'stakeholder management', 'process improvement',
                'data analysis', 'reporting', 'documentation', 'user stories', 'wireframing'
            ],
            'design': [
                'graphic design', 'ui design', 'ux design', 'web design', 'photoshop', 'illustrator',
                'figma', 'sketch', 'canva', 'adobe xd', 'indesign', 'after effects'
            ],
            'tools': [
                'microsoft office', 'excel', 'powerpoint', 'word', 'google sheets', 'slack', 'teams',
                'zoom', 'confluence', 'notion', 'smartsheets', 'clickup', 'hubspot', 'salesforce'
            ]
        }
        
        # Flatten all skills
        self.all_skills = set()
        for category_skills in self.tech_skills_db.values():
            self.all_skills.update(category_skills)
    
    def extract_skills_from_text(self, text: str) -> Set[str]:
        """Extract technical skills from text."""
        if not text:
            return set()
        
        text_lower = text.lower()
        found_skills = set()
        
        # Direct skill matching
        for skill in self.all_skills:
            pattern = r'\b' + re.escape(skill.lower()) + r'\b'
            if re.search(pattern, text_lower):
                found_skills.add(skill)
        
        # Common variations
        variations = {
            'javascript': ['js', 'node.js', 'nodejs'],
            'postgresql': ['postgres', 'psql'],
            'machine learning': ['ml', 'ai'],
            'react native': ['react-native'],
            'c++': ['cpp'],
            'c#': ['csharp']
        }
        
        for main_skill, vars in variations.items():
            for var in vars:
                if re.search(r'\b' + re.escape(var) + r'\b', text_lower):
                    found_skills.add(main_skill)
        
        return found_skills
    
    def extract_experience_level(self, text: str) -> Tuple[str, int]:
        """Extract experience level from text."""
        if not text:
            return 'unknown', 0
        
        text_lower = text.lower()
        years = 0
        level = 'unknown'
        
        # Extract years
        year_patterns = [
            r'(\d+)\+?\s*years?\s+(?:of\s+)?experience',
            r'(\d+)\+?\s*years?\s+(?:in|with)',
            r'experience[:\s]+(\d+)\+?\s*years?'
        ]
        
        for pattern in year_patterns:
            matches = re.findall(pattern, text_lower)
            for match in matches:
                years = max(years, int(match))
        
        # Detect level
        if re.search(r'\bsenior\b|\blead\b|\bprincipal\b', text_lower):
            level = 'senior'
        elif re.search(r'\bjunior\b|\bentry\b|\bintern\b', text_lower):
            level = 'junior'
        else:
            level = 'mid'
        
        # Override with years
        if years >= 8:
            level = 'senior'
        elif years >= 4:
            level = 'mid'
        elif years >= 1:
            level = 'junior'
        
        return level, years
    
    def simple_skill_similarity(self, job_skills: Set[str], cv_skills: Set[str]) -> float:
        """Calculate simple Jaccard similarity."""
        if not job_skills or not cv_skills:
            return 0.0
        
        intersection = len(job_skills.intersection(cv_skills))
        union = len(job_skills.union(cv_skills))
        return intersection / union if union > 0 else 0.0
    
    def validate_experience_compatibility(self, job_level: str, job_years: int, 
                                        cv_level: str, cv_years: int) -> Tuple[bool, float]:
        """Simple experience validation."""
        level_hierarchy = {
            'intern': 0,
            'junior': 1,
            'mid': 2,
            'senior': 3,
            'unknown': 1
        }
        
        job_score = level_hierarchy.get(job_level, 1)
        cv_score = level_hierarchy.get(cv_level, 1)
        
        level_diff = abs(job_score - cv_score)
        
        if level_diff == 0:
            compatibility = 1.0
        elif level_diff == 1:
            compatibility = 0.7
        else:
            compatibility = 0.4
        
        return compatibility >= 0.5, compatibility
    
    def intelligent_prefilter(self, job_description: str, cv_text: str, 
                            strict_mode: bool = False) -> Tuple[bool, Dict]:
        """Simple pre-filtering logic."""
        if not job_description or not cv_text:
            return False, {'reason': 'Missing text'}
        
        # Extract skills
        job_skills = self.extract_skills_from_text(job_description)
        cv_skills = self.extract_skills_from_text(cv_text)
        
        # Extract experience
        job_level, job_years = self.extract_experience_level(job_description)
        cv_level, cv_years = self.extract_experience_level(cv_text)
        
        # Calculate similarities
        skill_similarity = self.simple_skill_similarity(job_skills, cv_skills)
        exp_compatible, exp_score = self.validate_experience_compatibility(
            job_level, job_years, cv_level, cv_years
        )
        
        # Overall score
        overall_score = (skill_similarity * 0.7) + (exp_score * 0.3)
        
        # Thresholds (made more lenient for testing)
        threshold = 0.3 if strict_mode else 0.1
        passes = overall_score >= threshold or len(job_skills.intersection(cv_skills)) > 0
        
        analysis = {
            'passes_filter': passes,
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
        
        return passes, analysis

# Global instance
simple_skill_matcher = SimpleSkillMatcher()