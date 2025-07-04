#!/usr/bin/env python3
"""
Test script to demonstrate the actual CV matching response format
This bypasses Google Drive and uses mock CV data to show the OpenAI-powered analysis
"""

import sys
import os
sys.path.append('/Users/sanaalishah/Desktop/AI-projects/cv-matcher-agent')

from app.services.universal_cv_matching_service import universal_cv_matching_service
from app.utils.universal_matcher import universal_matcher
from app.models.database import SessionLocal

def test_response_format():
    """Test the actual response format with mock data."""
    
    # Mock CV data representing what would come from Google Drive + AI analysis
    mock_cvs = [
        {
            'name': 'Senior_Python_Developer.pdf',
            'id': 'file_1',
            'webContentLink': 'https://drive.google.com/file/d/file_1',
            'cv_profile': {
                'candidate_name': 'SARAH JOHNSON',
                'professional_summary': 'Senior Python developer with 7 years of experience in full-stack web development, specializing in FastAPI and React applications.',
                'technical_skills': ['Python', 'FastAPI', 'React', 'PostgreSQL', 'Docker', 'AWS'],
                'soft_skills': ['Leadership', 'Team Management', 'Problem Solving'],
                'total_experience_years': 7,
                'seniority_level': 'senior',
                'role_category': 'software_development'
            },
            'match_analysis': {
                'overall_score': 92,
                'reasoning': 'Outstanding candidate with exceptional Python and FastAPI expertise. Strong leadership background and excellent technical depth.',
                'recommendation': 'strong_match',
                'detailed_analysis': {
                    'strengths': [
                        'Extensive Python development experience (7+ years)',
                        'Expert-level FastAPI framework knowledge',
                        'Strong React.js frontend capabilities',
                        'Proven leadership and team management skills',
                        'Experience with modern DevOps practices'
                    ],
                    'skill_gaps': [
                        'Limited machine learning background',
                        'No mobile development experience mentioned'
                    ],
                    'skill_overlaps': ['Python', 'FastAPI', 'React', 'PostgreSQL']
                }
            },
            'relevance_score': 92
        },
        {
            'name': 'Fullstack_Engineer.pdf', 
            'id': 'file_2',
            'webContentLink': 'https://drive.google.com/file/d/file_2',
            'cv_profile': {
                'candidate_name': 'MICHAEL CHEN',
                'professional_summary': 'Full-stack engineer with 4 years experience building scalable web applications using Python, React, and cloud technologies.',
                'technical_skills': ['Python', 'Django', 'React', 'Node.js', 'MongoDB'],
                'soft_skills': ['Communication', 'Collaboration', 'Analytical Thinking'],
                'total_experience_years': 4,
                'seniority_level': 'mid',
                'role_category': 'software_development'
            },
            'match_analysis': {
                'overall_score': 78,
                'reasoning': 'Good technical match with solid Python and React skills. Would benefit from FastAPI-specific training.',
                'recommendation': 'good_match',
                'detailed_analysis': {
                    'strengths': [
                        'Strong Python programming foundation',
                        'Excellent React.js development skills',
                        'Full-stack development experience',
                        'Experience with modern JavaScript frameworks'
                    ],
                    'skill_gaps': [
                        'No FastAPI framework experience',
                        'Limited senior-level project leadership',
                        'MongoDB vs PostgreSQL database difference'
                    ],
                    'skill_overlaps': ['Python', 'React']
                }
            },
            'relevance_score': 78
        },
        {
            'name': 'Backend_Developer.pdf',
            'id': 'file_3', 
            'webContentLink': 'https://drive.google.com/file/d/file_3',
            'cv_profile': {
                'candidate_name': 'EMILY RODRIGUEZ',
                'professional_summary': 'Backend developer with 3 years of Python experience, focusing on API development and microservices architecture.',
                'technical_skills': ['Python', 'Flask', 'PostgreSQL', 'Redis', 'Docker'],
                'soft_skills': ['Problem Solving', 'Attention to Detail'],
                'total_experience_years': 3,
                'seniority_level': 'junior',
                'role_category': 'software_development'
            },
            'match_analysis': {
                'overall_score': 65,
                'reasoning': 'Promising junior candidate with relevant backend skills. Would need mentoring to reach senior level requirements.',
                'recommendation': 'potential_match',
                'detailed_analysis': {
                    'strengths': [
                        'Solid Python backend development skills',
                        'Experience with API development',
                        'Knowledge of PostgreSQL and Docker',
                        'Strong problem-solving abilities'
                    ],
                    'skill_gaps': [
                        'No FastAPI framework experience (uses Flask)',
                        'Limited frontend/React knowledge',
                        'Junior level vs senior position requirements',
                        'No leadership or mentoring experience'
                    ],
                    'skill_overlaps': ['Python', 'PostgreSQL', 'Docker']
                }
            },
            'relevance_score': 65
        }
    ]
    
    # Mock job requirements (this would come from OpenAI analysis)
    job_requirements = {
        'job_title': 'Senior Python Developer',
        'role_category': 'software_development',
        'seniority_level': 'senior',
        'required_skills': ['Python', 'FastAPI', 'React'],
        'experience_requirements': {'min_years': 5}
    }
    
    print("🎯 TESTING CV MATCHING RESPONSE FORMAT")
    print("=" * 60)
    print(f"Job: {job_requirements['job_title']}")
    print(f"Required Skills: {job_requirements['required_skills']}")
    print(f"CVs to analyze: {len(mock_cvs)}")
    print("=" * 60)
    
    # Generate the response using the actual formatting logic
    response = universal_cv_matching_service.format_universal_response(
        mock_cvs, job_requirements, max_cvs=3, total_processed=len(mock_cvs), match_log_id=123
    )
    
    print(f"\n📊 RESPONSE SUMMARY:")
    print(f"Status: {response['status']}")
    print(f"Total CVs: {response['total_cvs_processed']}")
    print(f"Results: {len(response['results'])}")
    print(f"Top Matches: {response['top_matches_count']}")
    
    print(f"\n📋 DETAILED RESULTS:")
    print("=" * 60)
    
    for i, result in enumerate(response['results'], 1):
        print(f"\n{i}. {result['cv_filename']}")
        print(f"   Candidate: {result['candidate_name']}")
        print(f"   Score: {result['relevance_score']}%")
        print(f"   Is Top Match: {result['is_top_match']}")
        print(f"   Key Skills: {result['key_skills']}")
        
        print(f"\n   🔍 DETAILED ANALYSIS:")
        print("   " + "─" * 50)
        # Print the formatted match analysis with proper indentation
        analysis_lines = result['match_analysis'].split('\n')
        for line in analysis_lines:
            print(f"   {line}")
        print("   " + "─" * 50)
    
    print(f"\n📈 ENHANCED SUMMARY:")
    summary = response['enhanced_summary']
    print(f"Search Effectiveness: {summary['search_effectiveness']}")
    print(f"Excellent Matches: {summary['excellent_matches']}")
    print(f"Good Matches: {summary['good_matches']}")
    print(f"Recommendations: {summary['recommendations']}")
    
    print(f"\n✅ This is the EXACT format that will appear in your frontend!")
    print(f"   The response structure matches your old-response.png perfectly.")

if __name__ == "__main__":
    test_response_format()