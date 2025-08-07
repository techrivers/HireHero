import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import API_CONFIG from '../config/api';
import DashboardCard from '../components/DashboardCard';
import { 
  Users, 
  FileText, 
  Star,
  Download,
  Filter,
  Search,
  Calendar,
  Award
} from 'lucide-react';
import './Candidates.css';

const Candidates = () => {
  const [candidates, setCandidates] = useState([]);
  const [filteredCandidates, setFilteredCandidates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterScore, setFilterScore] = useState('all');
  const [sortBy, setSortBy] = useState('score');

  useEffect(() => {
    axios.defaults.baseURL = API_CONFIG.baseURL;
    fetchCandidates();
  }, []);

  useEffect(() => {
    filterAndSortCandidates();
  }, [candidates, searchTerm, filterScore, sortBy]);

  const fetchCandidates = async () => {
    try {
      // Get all match results from history
      const response = await axios.get('/cv-matching/history');
      const allMatches = response.data || [];
      
      // Extract all candidates from all matches
      const allCandidates = [];
      allMatches.forEach(match => {
        if (match.results && Array.isArray(match.results)) {
          match.results.forEach(result => {
            allCandidates.push({
              ...result,
              job_title: `Match #${match.id}`, // Use match ID since job_title might not exist
              match_date: match.created_at,
              match_id: match.id,
              match_score: result.relevance_score, // Map relevance_score to match_score for consistency
              skills: result.key_skills, // Map key_skills to skills
              summary: result.candidate_summary
            });
          });
        }
      });

      setCandidates(allCandidates);
    } catch (error) {
      console.error('Error fetching candidates:', error);
      setCandidates([]); // Set empty array on error
    } finally {
      setLoading(false);
    }
  };

  const filterAndSortCandidates = () => {
    let filtered = [...candidates];

    // Search filter
    if (searchTerm) {
      filtered = filtered.filter(candidate => 
        candidate.candidate_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        candidate.skills?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        candidate.job_title?.toLowerCase().includes(searchTerm.toLowerCase())
      );
    }

    // Score filter
    if (filterScore !== 'all') {
      const minScore = parseInt(filterScore);
      filtered = filtered.filter(candidate => candidate.match_score >= minScore);
    }

    // Sort
    filtered.sort((a, b) => {
      switch (sortBy) {
        case 'score':
          return b.match_score - a.match_score;
        case 'name':
          return (a.candidate_name || '').localeCompare(b.candidate_name || '');
        case 'date':
          return new Date(b.match_date) - new Date(a.match_date);
        default:
          return 0;
      }
    });

    setFilteredCandidates(filtered);
  };

  const getScoreColor = (score) => {
    if (score >= 80) return '#38a169';
    if (score >= 60) return '#d69e2e';
    return '#e53e3e';
  };

  const getScoreLabel = (score) => {
    if (score >= 80) return 'Excellent';
    if (score >= 60) return 'Good';
    return 'Fair';
  };

  if (loading) {
    return (
      <div className="candidates-loading">
        <div className="spinner-large"></div>
        <p>Loading candidates...</p>
      </div>
    );
  }

  return (
    <div className="candidates-page">
      <div className="page-container">
        <div className="page-header">
          <h1 className="page-title">Candidates</h1>
          <p className="page-subtitle">
            All evaluated candidates from your matching history
          </p>
        </div>

        {/* Summary Stats */}
        <div className="candidates-stats">
          <div className="stat-item">
            <Users size={20} />
            <div>
              <span className="stat-number">{candidates.length}</span>
              <span className="stat-label">Total Candidates</span>
            </div>
          </div>
          <div className="stat-item">
            <Award size={20} />
            <div>
              <span className="stat-number">
                {candidates.filter(c => c.match_score >= 80).length}
              </span>
              <span className="stat-label">Excellent Matches</span>
            </div>
          </div>
          <div className="stat-item">
            <Star size={20} />
            <div>
              <span className="stat-number">
                {candidates.length > 0 ? 
                  Math.round(candidates.reduce((sum, c) => sum + c.match_score, 0) / candidates.length) 
                  : 0}%
              </span>
              <span className="stat-label">Average Score</span>
            </div>
          </div>
        </div>

        {/* Filters and Search */}
        <DashboardCard title="Filter Candidates" icon={Filter}>
          <div className="filters-container">
            <div className="search-box">
              <Search size={16} />
              <input
                type="text"
                placeholder="Search by name, skills, or job title..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
            
            <select
              value={filterScore}
              onChange={(e) => setFilterScore(e.target.value)}
              className="filter-select"
            >
              <option value="all">All Scores</option>
              <option value="80">Excellent (80%+)</option>
              <option value="60">Good (60%+)</option>
              <option value="40">Fair (40%+)</option>
            </select>
            
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="filter-select"
            >
              <option value="score">Sort by Score</option>
              <option value="name">Sort by Name</option>
              <option value="date">Sort by Date</option>
            </select>
          </div>
        </DashboardCard>

        {/* Candidates List */}
        <DashboardCard 
          title={`Candidates (${filteredCandidates.length})`} 
          icon={Users}
        >
          {filteredCandidates.length === 0 ? (
            <div className="no-candidates">
              <Users size={48} />
              <h3>No candidates found</h3>
              <p>
                {candidates.length === 0 
                  ? "Start matching resumes to see candidates here."
                  : "Try adjusting your search or filters."
                }
              </p>
              {candidates.length === 0 && (
                <Link to="/cv-matching" className="btn btn-primary">
                  Start Matching
                </Link>
              )}
            </div>
          ) : (
            <div className="candidates-list">
              {filteredCandidates.map((candidate, index) => (
                <div key={`${candidate.match_id}-${index}`} className="candidate-card">
                  <div className="candidate-header">
                    <div className="candidate-info">
                      <h3 className="candidate-name">
                        {candidate.candidate_name || 'Unnamed Candidate'}
                      </h3>
                      <p className="candidate-job">
                        Applied for: {candidate.job_title || 'Unknown Position'}
                      </p>
                    </div>
                    <div className="candidate-score">
                      <div 
                        className="score-circle"
                        style={{ color: getScoreColor(candidate.match_score) }}
                      >
                        {candidate.match_score}%
                      </div>
                      <span 
                        className="score-label"
                        style={{ color: getScoreColor(candidate.match_score) }}
                      >
                        {getScoreLabel(candidate.match_score)}
                      </span>
                    </div>
                  </div>
                  
                  <div className="candidate-content">
                    {candidate.skills && (
                      <div className="candidate-skills">
                        <strong>Skills:</strong>
                        <div className="skills-tags">
                          {candidate.skills.split(',').slice(0, 5).map((skill, i) => (
                            <span key={i} className="skill-tag">
                              {skill.trim()}
                            </span>
                          ))}
                          {candidate.skills.split(',').length > 5 && (
                            <span className="skill-tag more">
                              +{candidate.skills.split(',').length - 5} more
                            </span>
                          )}
                        </div>
                      </div>
                    )}
                    
                    {candidate.summary && (
                      <div className="candidate-summary">
                        <strong>Summary:</strong>
                        <p>{candidate.summary}</p>
                      </div>
                    )}
                  </div>
                  
                  <div className="candidate-footer">
                    <div className="candidate-meta">
                      <Calendar size={14} />
                      <span>Evaluated on {new Date(candidate.match_date).toLocaleDateString()}</span>
                    </div>
                    
                    {candidate.file_path && (
                      <a
                        href={`${API_CONFIG.baseURL}/cv-matching/download/${candidate.match_id}/${encodeURIComponent(candidate.file_path)}`}
                        className="btn btn-secondary btn-sm"
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        <Download size={14} />
                        Download Resume
                      </a>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </DashboardCard>
      </div>
    </div>
  );
};

export default Candidates;