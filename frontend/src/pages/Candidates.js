import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import API_CONFIG from '../config/api';
import DashboardCard from '../components/DashboardCard';
import FloatingChatWidget from '../components/FloatingChatWidget';
import { 
  Users, 
  FileText, 
  Star,
  Download,
  Filter,
  Search,
  Calendar,
  Award,
  MapPin,
  Briefcase,
  Brain,
  RefreshCw,
  Plus
} from 'lucide-react';
import './Candidates.css';

const Candidates = () => {
  const [candidates, setCandidates] = useState([]);
  const [filteredCandidates, setFilteredCandidates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterExperience, setFilterExperience] = useState('all');
  const [filterAvailability, setFilterAvailability] = useState('all');
  const [sortBy, setSortBy] = useState('updated');
  const [analytics, setAnalytics] = useState({});
  const [searchMode, setSearchMode] = useState('normal'); // 'normal', 'ai', 'fallback'

  useEffect(() => {
    axios.defaults.baseURL = API_CONFIG.baseURL;
    fetchCandidates();
    fetchAnalytics();
  }, []);

  useEffect(() => {
    filterAndSortCandidates();
    // Reset search mode when not using AI search
    if (!searchTerm) {
      setSearchMode('normal');
    }
  }, [candidates, searchTerm, filterExperience, filterAvailability, sortBy]);

  const fetchCandidates = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get('/candidates/', {
        headers: { Authorization: `Bearer ${token}` }
      });
      // API returns array directly, not wrapped in an object
      const candidatesData = Array.isArray(response.data) ? response.data : response.data.candidates || [];
      console.log('Candidates API Response:', response.data);
      console.log('Processed candidates:', candidatesData);
      setCandidates(candidatesData);
    } catch (error) {
      console.error('Error fetching candidates:', error);
      // Fallback to old API if new one isn't available yet
      if (error.response?.status === 404) {
        await fetchCandidatesOld();
      } else {
        setCandidates([]);
      }
    } finally {
      setLoading(false);
    }
  };

  const fetchCandidatesOld = async () => {
    try {
      const response = await axios.get('/cv-matching/history');
      const allMatches = response.data || [];
      
      const allCandidates = [];
      allMatches.forEach(match => {
        if (match.results && Array.isArray(match.results)) {
          match.results.forEach(result => {
            allCandidates.push({
              id: `${match.id}-${result.id}`,
              name: result.candidate_name || 'Unnamed Candidate',
              email: null,
              skills_json: { skills: result.key_skills ? result.key_skills.split(',') : [] },
              experience_years: result.experience_years || 0,
              professional_summary: result.candidate_summary,
              availability_status: 'unknown',
              last_updated: match.created_at,
              match_count: 1,
              avg_match_score: result.relevance_score || 0,
              cv_filename: result.cv_filename
            });
          });
        }
      });

      setCandidates(allCandidates);
    } catch (error) {
      console.error('Error fetching candidates from old API:', error);
      setCandidates([]);
    }
  };

  const fetchAnalytics = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get('/candidates/analytics/overview', {
        headers: { Authorization: `Bearer ${token}` }
      });
      setAnalytics(response.data);
    } catch (error) {
      console.error('Error fetching analytics:', error);
    }
  };

  const handleNaturalLanguageSearch = async () => {
    if (!searchTerm.trim()) return;
    
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      console.log('🔍 Performing AI search for:', searchTerm);
      setSearchMode('ai');
      
      const response = await axios.post('/candidates/search', {
        query: searchTerm,
        limit: 50
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      console.log('🎯 AI search response:', response.data);
      
      // Search API returns results property containing candidates
      const searchResults = response.data.results || response.data.candidates || [];
      
      if (searchResults.length === 0) {
        console.log('⚠️ AI search returned no results, falling back to basic search');
        setSearchMode('fallback');
        // If AI search returns nothing, fall back to enhanced local filtering
        const originalCandidates = [...candidates];
        const enhancedFiltered = originalCandidates.filter(candidate => {
          const query = searchTerm.toLowerCase();
          return (
            // Name matching
            candidate.name?.toLowerCase().includes(query) ||
            // Summary matching
            candidate.professional_summary?.toLowerCase().includes(query) ||
            // Role matching
            candidate.current_role?.toLowerCase().includes(query) ||
            // Company matching  
            candidate.current_company?.toLowerCase().includes(query) ||
            // Skills matching (enhanced)
            (candidate.skills_json?.skills || candidate.skills_json || []).some(skill => {
              const skillName = typeof skill === 'string' ? skill : skill.name || skill;
              return skillName.toLowerCase().includes(query);
            }) ||
            // Check if it's a role-based query
            (query.includes('manager') && 
              (candidate.professional_summary?.toLowerCase().includes('manage') ||
               candidate.current_role?.toLowerCase().includes('manager') ||
               (candidate.skills_json?.soft_skills || []).some(skill => 
                 typeof skill === 'string' ? skill.toLowerCase().includes('management') : false
               )
              )
            )
          );
        });
        
        console.log(`🔄 Enhanced fallback found ${enhancedFiltered.length} candidates`);
        setFilteredCandidates(enhancedFiltered);
      } else {
        console.log(`✅ AI search found ${searchResults.length} candidates`);
        setSearchMode('ai');
        setCandidates(searchResults);
      }
    } catch (error) {
      console.error('❌ Error with intelligent search:', error);
      setSearchMode('fallback');
      // Fall back to regular filtering
      filterAndSortCandidates();
    } finally {
      setLoading(false);
    }
  };

  const reanalyzeCandidateProfile = async (candidateId) => {
    try {
      const token = localStorage.getItem('token');
      await axios.post(`/candidates/${candidateId}/reanalyze`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      // Refresh the candidate data
      fetchCandidates();
    } catch (error) {
      console.error('Error reanalyzing candidate:', error);
    }
  };

  const regenerateAllSummaries = async () => {
    if (!window.confirm('This will regenerate professional summaries for all candidates with missing or poor summaries. This may take a few minutes. Continue?')) {
      return;
    }
    
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const response = await axios.post('/candidates/regenerate-summaries', {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      console.log('✅ Summary regeneration completed:', response.data);
      alert(`Successfully regenerated summaries for ${response.data.updated_candidates} candidates!`);
      
      // Refresh the candidates data
      await fetchCandidates();
    } catch (error) {
      console.error('❌ Error regenerating summaries:', error);
      alert('Failed to regenerate summaries. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const filterAndSortCandidates = () => {
    let filtered = [...candidates];

    // Search filter (basic text search if not using AI search)
    if (searchTerm && !loading) {
      filtered = filtered.filter(candidate => {
        // Check name and summary
        const nameMatch = candidate.name?.toLowerCase().includes(searchTerm.toLowerCase());
        const summaryMatch = candidate.professional_summary?.toLowerCase().includes(searchTerm.toLowerCase());
        
        // Safely check skills
        let skillsMatch = false;
        try {
          const skills = candidate.skills_json?.skills || candidate.skills_json || [];
          if (Array.isArray(skills)) {
            skillsMatch = skills.some(skill => 
              (typeof skill === 'string' ? skill : skill.name || skill).toLowerCase().includes(searchTerm.toLowerCase())
            );
          }
        } catch (error) {
          console.warn('Error processing skills for candidate:', candidate.id, error);
        }
        
        return nameMatch || summaryMatch || skillsMatch;
      });
    }

    // Experience filter
    if (filterExperience !== 'all') {
      const [min, max] = filterExperience.split('-').map(Number);
      filtered = filtered.filter(candidate => {
        const exp = candidate.experience_years || 0;
        if (max) return exp >= min && exp <= max;
        return exp >= min;
      });
    }

    // Availability filter
    if (filterAvailability !== 'all') {
      filtered = filtered.filter(candidate => 
        candidate.availability_status === filterAvailability
      );
    }

    // Sort
    filtered.sort((a, b) => {
      switch (sortBy) {
        case 'name':
          return (a.name || '').localeCompare(b.name || '');
        case 'experience':
          return (b.experience_years || 0) - (a.experience_years || 0);
        case 'score':
          return (b.avg_match_score || 0) - (a.avg_match_score || 0);
        case 'updated':
        default:
          return new Date(b.last_updated || b.updated_at || b.created_at) - new Date(a.last_updated || a.updated_at || a.created_at);
      }
    });

    setFilteredCandidates(filtered);
  };

  const getExperienceLabel = (years) => {
    if (years === 0) return 'Entry Level';
    if (years <= 2) return 'Junior';
    if (years <= 5) return 'Mid-Level';
    if (years <= 10) return 'Senior';
    return 'Expert';
  };

  const getAvailabilityColor = (status) => {
    switch (status) {
      case 'available': return '#38a169';
      case 'employed': return '#d69e2e';
      case 'interviewing': return '#3182ce';
      default: return '#718096';
    }
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
          <div>
            <h1 className="page-title">Enhanced Candidate Management</h1>
            <p className="page-subtitle">
              AI-powered candidate profiling and intelligent search
            </p>
          </div>
          <div className="header-actions">
            <button 
              onClick={regenerateAllSummaries}
              className="btn btn-secondary"
              disabled={loading}
              title="Regenerate professional summaries using AI"
            >
              <RefreshCw size={16} />
              Fix Summaries
            </button>
            <Link to="/candidates/import" className="btn btn-primary">
              <Plus size={16} />
              Import Candidates
            </Link>
          </div>
        </div>

        {/* Enhanced Analytics */}
        <div className="candidates-stats">
          <div className="stat-item">
            <Users size={20} />
            <div>
              <span className="stat-number">{analytics.total_candidates || candidates.length}</span>
              <span className="stat-label">Total Candidates</span>
            </div>
          </div>
          <div className="stat-item">
            <Award size={20} />
            <div>
              <span className="stat-number">
                {analytics.high_potential_candidates || candidates.filter(c => (c.avg_match_score || 0) >= 80).length}
              </span>
              <span className="stat-label">High Potential</span>
            </div>
          </div>
          <div className="stat-item">
            <Briefcase size={20} />
            <div>
              <span className="stat-number">
                {analytics.candidates_by_availability?.available || candidates.filter(c => c.availability_status === 'available').length}
              </span>
              <span className="stat-label">Available Now</span>
            </div>
          </div>
          <div className="stat-item">
            <Brain size={20} />
            <div>
              <span className="stat-number">
                {Math.round(analytics.average_experience_years || 
                  (candidates.length > 0 ? candidates.reduce((sum, c) => sum + (c.experience_years || 0), 0) / candidates.length : 0)
                )}
              </span>
              <span className="stat-label">Avg. Experience</span>
            </div>
          </div>
        </div>

        {/* Enhanced Search and Filters */}
        <DashboardCard title="Intelligent Candidate Search" icon={Brain}>
          <div className="filters-container">
            <div className="search-container">
              <div className="search-box intelligent-search">
                <Search size={14}/>

                <input
                    type="text"
                    className="ai-input"
                    placeholder="Try: 'React developers with 5+ years experience' or 'project managers with agile experience'"
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && handleNaturalLanguageSearch()}
                />

                <button
                    onClick={handleNaturalLanguageSearch}
                    className="btn btn-primary btn-sm ai-button"
                    disabled={!searchTerm.trim()}
                >
                  AI Search
                </button>
              </div>

              {searchMode === 'fallback' && searchTerm && (
                  <div className="search-mode-indicator">
      <span className="fallback-indicator">
        ⚠️ Using enhanced fallback search - AI couldn't find matches
      </span>
                  </div>
              )}
            </div>


            <div className="filters-row">
              <select
                  value={filterExperience}
                  onChange={(e) => setFilterExperience(e.target.value)}
                  className="filter-select"
              >
                <option value="all">All Experience Levels</option>
                <option value="0-2">Entry Level (0-2 years)</option>
                <option value="3-5">Mid-Level (3-5 years)</option>
                <option value="6-10">Senior (6-10 years)</option>
                <option value="10">Expert (10+ years)</option>
              </select>

              <select
                  value={filterAvailability}
                  onChange={(e) => setFilterAvailability(e.target.value)}
                  className="filter-select"
              >
                <option value="all">All Availability</option>
                <option value="available">Available</option>
                <option value="employed">Currently Employed</option>
                <option value="interviewing">Interviewing</option>
              </select>

              <select
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value)}
                  className="filter-select"
              >
                <option value="updated">Recently Updated</option>
                <option value="score">Match Score</option>
                <option value="experience">Experience Level</option>
                <option value="name">Name A-Z</option>
              </select>
            </div>
          </div>
        </DashboardCard>

        {/* Enhanced Candidates List */}
        <DashboardCard
            title={`Candidates (${filteredCandidates.length})`}
            icon={Users}
        >
          {filteredCandidates.length === 0 ? (
              <div className="no-candidates">
                <Users size={48}/>
                <h3>No candidates found</h3>
                <p>
                  {candidates.length === 0
                      ? "Import candidates or start matching to see profiles here."
                      : "Try adjusting your search or filters."
                  }
                </p>
                <div className="empty-state-actions">
                  <Link to="/cv-matching" className="btn btn-primary">
                    Start Matching
                  </Link>
                  <Link to="/candidates/import" className="btn btn-secondary">
                    Import Candidates
                  </Link>
                </div>
            </div>
          ) : (
            <div className="candidates-list enhanced">
              {filteredCandidates.map((candidate) => (
                <div key={candidate.id} className="candidate-card enhanced">
                  <div className="candidate-header">
                    <div className="candidate-info">
                      <h3 className="candidate-name">
                        {candidate.name}
                      </h3>
                      <div className="candidate-meta">
                        {candidate.email && (
                          <span className="candidate-email">{candidate.email}</span>
                        )}
                        <div className="candidate-badges">
                          <span className="experience-badge">
                            <Briefcase size={12} />
                            {candidate.experience_years || 0} years • {getExperienceLabel(candidate.experience_years || 0)}
                          </span>
                          {candidate.availability_status && (
                            <span 
                              className="availability-badge"
                              style={{ color: getAvailabilityColor(candidate.availability_status) }}
                            >
                              {candidate.availability_status.charAt(0).toUpperCase() + candidate.availability_status.slice(1)}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                    <div className="candidate-actions">
                      {candidate.avg_match_score !== undefined && (
                        <div className="candidate-score">
                          <div className="score-circle">
                            {Math.round(candidate.avg_match_score)}%
                          </div>
                          <span className="score-label">Avg Match</span>
                        </div>
                      )}
                      <button 
                        onClick={() => reanalyzeCandidateProfile(candidate.id)}
                        className="btn btn-secondary btn-sm"
                        title="Reanalyze with AI"
                      >
                        <RefreshCw size={14} />
                      </button>
                    </div>
                  </div>
                  
                  <div className="candidate-content">
                    {candidate.professional_summary && (
                      <div className="candidate-summary">
                        <strong>Professional Summary:</strong>
                        <p>{candidate.professional_summary}</p>
                      </div>
                    )}
                    
                    {(() => {
                      const skills = candidate.skills_json?.skills || candidate.skills_json || [];
                      const skillsArray = Array.isArray(skills) ? skills : [];
                      return skillsArray.length > 0 && (
                        <div className="candidate-skills">
                          <strong>Key Skills:</strong>
                          <div className="skills-tags">
                            {skillsArray.slice(0, 8).map((skill, i) => (
                              <span key={i} className="skill-tag">
                                {typeof skill === 'string' ? skill : skill.name || skill}
                              </span>
                            ))}
                            {skillsArray.length > 8 && (
                              <span className="skill-tag more">
                                +{skillsArray.length - 8} more
                              </span>
                            )}
                          </div>
                        </div>
                      );
                    })()}
                  </div>
                  
                  <div className="candidate-footer">
                    <div className="candidate-meta">
                      <Calendar size={14} />
                      <span>Updated {new Date(candidate.last_updated || candidate.updated_at || candidate.created_at).toLocaleDateString()}</span>
                      {candidate.match_count && (
                        <>
                          <span className="separator">•</span>
                          <Star size={14} />
                          <span>{candidate.match_count} matches</span>
                        </>
                      )}
                    </div>
                    
                    <div className="candidate-actions">
                      <Link 
                        to={`/candidates/${candidate.id}/matches`}
                        className="btn btn-secondary btn-sm"
                      >
                        View Matches
                      </Link>
                      {candidate.cv_filename && (
                        <button className="btn btn-secondary btn-sm">
                          <Download size={14} />
                          Download CV
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </DashboardCard>
      </div>
      
      {/* AI Chat Widget */}
      <FloatingChatWidget 
        context="candidates" 
        contextData={{
          totalCandidates: candidates.length,
          filteredCandidates: filteredCandidates.length,
          candidatesData: filteredCandidates, // Pass actual candidates data for AI analysis
          searchTerm,
          filterExperience,
          filterAvailability,
          analytics
        }} 
      />
    </div>
  );
};

export default Candidates;