import React, { useState, useEffect } from 'react';
import axios from 'axios';
import API_CONFIG from '../config/api';
import DashboardCard from '../components/DashboardCard';
import { 
  Zap, 
  Users,
  Briefcase,
  Star,
  Brain,
  TrendingUp,
  Target,
  RefreshCw,
  Eye,
  ThumbsUp,
  ThumbsDown,
  ArrowRight,
  Award,
  AlertCircle,
  CheckCircle,
  Filter,
  BarChart
} from 'lucide-react';
import './EnhancedMatching.css';

const EnhancedMatching = () => {
  const [matches, setMatches] = useState([]);
  const [candidates, setCandidates] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedCandidate, setSelectedCandidate] = useState('');
  const [selectedJob, setSelectedJob] = useState('');
  const [matchingMode, setMatchingMode] = useState('candidate'); // 'candidate' or 'job'
  const [analytics, setAnalytics] = useState({});
  const [filterScore, setFilterScore] = useState(0);

  useEffect(() => {
    axios.defaults.baseURL = API_CONFIG.baseURL;
    fetchCandidates();
    fetchJobs();
    fetchMatchingAnalytics();
  }, []);

  const fetchCandidates = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get('/candidates/', {
        headers: { Authorization: `Bearer ${token}` },
        params: { limit: 100 }
      });
      setCandidates(response.data.candidates || []);
    } catch (error) {
      console.error('Error fetching candidates:', error);
    }
  };

  const fetchJobs = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get('/jobs/', {
        headers: { Authorization: `Bearer ${token}` },
        params: { limit: 100, status: 'active' }
      });
      setJobs(response.data.jobs || []);
    } catch (error) {
      console.error('Error fetching jobs:', error);
    }
  };

  const fetchMatchingAnalytics = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get('/matching/analytics/overview', {
        headers: { Authorization: `Bearer ${token}` }
      });
      setAnalytics(response.data);
    } catch (error) {
      console.error('Error fetching matching analytics:', error);
    }
  };

  const runCandidateMatching = async () => {
    if (!selectedCandidate) return;
    
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const response = await axios.post(`/matching/candidate/${selectedCandidate}/jobs`, {
        limit: 10,
        min_score: filterScore / 100
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setMatches(response.data.matches || []);
    } catch (error) {
      console.error('Error running candidate matching:', error);
      setMatches([]);
    } finally {
      setLoading(false);
    }
  };

  const runJobMatching = async () => {
    if (!selectedJob) return;
    
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const response = await axios.post(`/matching/job/${selectedJob}/candidates`, {
        limit: 10,
        min_score: filterScore / 100
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setMatches(response.data.matches || []);
    } catch (error) {
      console.error('Error running job matching:', error);
      setMatches([]);
    } finally {
      setLoading(false);
    }
  };

  const runBulkMatching = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const response = await axios.post('/matching/bulk', {
        candidate_ids: selectedCandidate ? [parseInt(selectedCandidate)] : null,
        job_ids: selectedJob ? [parseInt(selectedJob)] : null,
        min_score: filterScore / 100
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      alert(`Bulk matching started! Processing ${response.data.total_matches} potential matches.`);
      fetchMatchingAnalytics();
    } catch (error) {
      console.error('Error running bulk matching:', error);
    } finally {
      setLoading(false);
    }
  };

  const updateMatchFeedback = async (matchId, feedback) => {
    try {
      const token = localStorage.getItem('token');
      await axios.patch(`/matching/match/${matchId}`, {
        recommendation: feedback
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      // Update local state
      setMatches(matches.map(match => 
        match.id === matchId 
          ? { ...match, recommendation: feedback }
          : match
      ));
    } catch (error) {
      console.error('Error updating match feedback:', error);
    }
  };

  const getScoreColor = (score) => {
    if (score >= 0.8) return '#38a169';
    if (score >= 0.6) return '#d69e2e';
    if (score >= 0.4) return '#dd6b20';
    return '#e53e3e';
  };

  const getScoreLabel = (score) => {
    if (score >= 0.8) return 'Excellent Match';
    if (score >= 0.6) return 'Good Match';
    if (score >= 0.4) return 'Fair Match';
    return 'Weak Match';
  };

  const getRecommendationIcon = (recommendation) => {
    switch (recommendation) {
      case 'strong':
        return <Award className="text-green-600" size={16} />;
      case 'consider':
        return <CheckCircle className="text-blue-600" size={16} />;
      case 'weak':
        return <AlertCircle className="text-orange-600" size={16} />;
      default:
        return null;
    }
  };

  return (
    <div className="enhanced-matching-page">
      <div className="page-container">
        <div className="page-header">
          <div>
            <h1 className="page-title">Enhanced AI Matching</h1>
            <p className="page-subtitle">
              Intelligent job-candidate matching with AI-powered explanations
            </p>
          </div>
        </div>

        {/* Matching Analytics */}
        <div className="matching-stats">
          <div className="stat-item">
            <Zap size={20} />
            <div>
              <span className="stat-number">{analytics.total_matches || 0}</span>
              <span className="stat-label">Total Matches</span>
            </div>
          </div>
          <div className="stat-item">
            <Award size={20} />
            <div>
              <span className="stat-number">{analytics.strong_matches || 0}</span>
              <span className="stat-label">Strong Matches</span>
            </div>
          </div>
          <div className="stat-item">
            <TrendingUp size={20} />
            <div>
              <span className="stat-number">
                {analytics.average_match_score ? `${Math.round(analytics.average_match_score * 100)}%` : '0%'}
              </span>
              <span className="stat-label">Avg Score</span>
            </div>
          </div>
          <div className="stat-item">
            <Target size={20} />
            <div>
              <span className="stat-number">{analytics.matches_today || 0}</span>
              <span className="stat-label">Today's Matches</span>
            </div>
          </div>
        </div>

        {/* Matching Controls */}
        <DashboardCard title="AI Matching Configuration" icon={Brain}>
          <div className="matching-controls">
            <div className="control-section">
              <h3>Matching Mode</h3>
              <div className="mode-selector">
                <label className="radio-option">
                  <input
                    type="radio"
                    value="candidate"
                    checked={matchingMode === 'candidate'}
                    onChange={(e) => setMatchingMode(e.target.value)}
                  />
                  <span className="radio-custom"></span>
                  Find Jobs for Candidate
                </label>
                <label className="radio-option">
                  <input
                    type="radio"
                    value="job"
                    checked={matchingMode === 'job'}
                    onChange={(e) => setMatchingMode(e.target.value)}
                  />
                  <span className="radio-custom"></span>
                  Find Candidates for Job
                </label>
              </div>
            </div>

            <div className="control-section">
              <h3>Selection</h3>
              <div className="selection-controls">
                {matchingMode === 'candidate' ? (
                  <select
                    value={selectedCandidate}
                    onChange={(e) => setSelectedCandidate(e.target.value)}
                    className="control-select"
                  >
                    <option value="">Select a candidate...</option>
                    {candidates.map(candidate => (
                      <option key={candidate.id} value={candidate.id}>
                        {candidate.name} - {candidate.experience_years || 0} years
                      </option>
                    ))}
                  </select>
                ) : (
                  <select
                    value={selectedJob}
                    onChange={(e) => setSelectedJob(e.target.value)}
                    className="control-select"
                  >
                    <option value="">Select a job...</option>
                    {jobs.map(job => (
                      <option key={job.id} value={job.id}>
                        {job.title} at {job.company}
                      </option>
                    ))}
                  </select>
                )}
              </div>
            </div>

            <div className="control-section">
              <h3>Minimum Match Score: {filterScore}%</h3>
              <input
                type="range"
                min="0"
                max="100"
                value={filterScore}
                onChange={(e) => setFilterScore(parseInt(e.target.value))}
                className="score-slider"
              />
            </div>

            <div className="action-buttons">
              <button
                onClick={matchingMode === 'candidate' ? runCandidateMatching : runJobMatching}
                className="btn btn-primary"
                disabled={loading || (matchingMode === 'candidate' ? !selectedCandidate : !selectedJob)}
              >
                {loading ? (
                  <RefreshCw size={16} className="spinning" />
                ) : (
                  <Brain size={16} />
                )}
                Run AI Matching
              </button>

              <button
                onClick={runBulkMatching}
                className="btn btn-secondary"
                disabled={loading}
              >
                <Zap size={16} />
                Bulk Match All
              </button>
            </div>
          </div>
        </DashboardCard>

        {/* Matching Results */}
        {matches.length > 0 && (
          <DashboardCard title={`AI Matching Results (${matches.length})`} icon={Target}>
            <div className="matches-list">
              {matches.map((match) => (
                <div key={match.id} className="match-card">
                  <div className="match-header">
                    <div className="match-info">
                      <div className="match-participants">
                        <div className="participant candidate">
                          <Users size={16} />
                          <span>{match.candidate?.name || 'Unknown Candidate'}</span>
                        </div>
                        <ArrowRight size={16} className="match-arrow" />
                        <div className="participant job">
                          <Briefcase size={16} />
                          <span>{match.job?.title || 'Unknown Job'} at {match.job?.company}</span>
                        </div>
                      </div>
                      <div className="match-meta">
                        <span className="match-date">
                          Matched {new Date(match.created_at).toLocaleDateString()}
                        </span>
                      </div>
                    </div>
                    <div className="match-score">
                      <div 
                        className="score-circle large"
                        style={{ color: getScoreColor(match.match_score) }}
                      >
                        {Math.round(match.match_score * 100)}%
                      </div>
                      <span 
                        className="score-label"
                        style={{ color: getScoreColor(match.match_score) }}
                      >
                        {getScoreLabel(match.match_score)}
                      </span>
                    </div>
                  </div>

                  <div className="match-content">
                    {match.explanation && (
                      <div className="ai-explanation">
                        <div className="explanation-header">
                          <Brain size={16} />
                          <span>AI Analysis</span>
                        </div>
                        <p>{match.explanation}</p>
                      </div>
                    )}

                    <div className="match-details">
                      {match.strengths && match.strengths.length > 0 && (
                        <div className="detail-section strengths">
                          <h4>
                            <CheckCircle size={16} />
                            Key Strengths
                          </h4>
                          <div className="detail-tags">
                            {match.strengths.map((strength, i) => (
                              <span key={i} className="tag strength-tag">
                                {strength}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                      {match.gaps && match.gaps.length > 0 && (
                        <div className="detail-section gaps">
                          <h4>
                            <AlertCircle size={16} />
                            Skill Gaps
                          </h4>
                          <div className="detail-tags">
                            {match.gaps.map((gap, i) => (
                              <span key={i} className="tag gap-tag">
                                {gap}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                      {match.extra_skills && match.extra_skills.length > 0 && (
                        <div className="detail-section extras">
                          <h4>
                            <Star size={16} />
                            Bonus Skills
                          </h4>
                          <div className="detail-tags">
                            {match.extra_skills.map((skill, i) => (
                              <span key={i} className="tag extra-tag">
                                {skill}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                      {match.alternative_roles && match.alternative_roles.length > 0 && (
                        <div className="detail-section alternatives">
                          <h4>
                            <Target size={16} />
                            Alternative Roles
                          </h4>
                          <div className="detail-tags">
                            {match.alternative_roles.map((role, i) => (
                              <span key={i} className="tag alternative-tag">
                                {role}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="match-footer">
                    <div className="match-recommendation">
                      {getRecommendationIcon(match.recommendation)}
                      <span className={`recommendation-text ${match.recommendation}`}>
                        {match.recommendation ? match.recommendation.charAt(0).toUpperCase() + match.recommendation.slice(1) : 'Pending'}
                      </span>
                    </div>
                    <div className="match-actions">
                      <button
                        onClick={() => updateMatchFeedback(match.id, 'strong')}
                        className={`btn btn-sm ${match.recommendation === 'strong' ? 'btn-primary' : 'btn-secondary'}`}
                      >
                        <ThumbsUp size={14} />
                        Strong
                      </button>
                      <button
                        onClick={() => updateMatchFeedback(match.id, 'consider')}
                        className={`btn btn-sm ${match.recommendation === 'consider' ? 'btn-primary' : 'btn-secondary'}`}
                      >
                        <CheckCircle size={14} />
                        Consider
                      </button>
                      <button
                        onClick={() => updateMatchFeedback(match.id, 'weak')}
                        className={`btn btn-sm ${match.recommendation === 'weak' ? 'btn-danger' : 'btn-secondary'}`}
                      >
                        <ThumbsDown size={14} />
                        Weak
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </DashboardCard>
        )}

        {matches.length === 0 && !loading && (
          <DashboardCard title="Get Started" icon={Brain}>
            <div className="empty-state">
              <Zap size={48} />
              <h3>Ready to find perfect matches?</h3>
              <p>
                Select a candidate or job above and run AI-powered matching to discover 
                intelligent connections with detailed explanations.
              </p>
              <div className="feature-highlights">
                <div className="feature">
                  <Brain size={24} />
                  <div>
                    <h4>AI-Powered Analysis</h4>
                    <p>Get detailed explanations for every match</p>
                  </div>
                </div>
                <div className="feature">
                  <Target size={24} />
                  <div>
                    <h4>Intelligent Scoring</h4>
                    <p>Advanced algorithms consider multiple factors</p>
                  </div>
                </div>
                <div className="feature">
                  <Star size={24} />
                  <div>
                    <h4>Alternative Suggestions</h4>
                    <p>Discover unexpected but relevant opportunities</p>
                  </div>
                </div>
              </div>
            </div>
          </DashboardCard>
        )}
      </div>
    </div>
  );
};

export default EnhancedMatching;