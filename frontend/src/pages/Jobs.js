import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import API_CONFIG from '../config/api';
import DashboardCard from '../components/DashboardCard';
import { 
  Briefcase, 
  Plus,
  Search,
  Filter,
  Calendar,
  MapPin,
  Building,
  Users,
  Star,
  BarChart,
  RefreshCw,
  Eye,
  Edit,
  Trash2,
  Brain,
  ExternalLink
} from 'lucide-react';
import './Jobs.css';

const Jobs = () => {
  const [jobs, setJobs] = useState([]);
  const [filteredJobs, setFilteredJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterCompany, setFilterCompany] = useState('all');
  const [filterExperience, setFilterExperience] = useState('all');
  const [filterStatus, setFilterStatus] = useState('active');
  const [sortBy, setSortBy] = useState('created_at');
  const [analytics, setAnalytics] = useState({});
  const [showCreateForm, setShowCreateForm] = useState(false);

  const [newJob, setNewJob] = useState({
    title: '',
    company: '',
    description: '',
    required_skills: [],
    experience_level: '',
    salary_range: '',
    location: '',
    remote_friendly: false,
    url: ''
  });

  useEffect(() => {
    axios.defaults.baseURL = API_CONFIG.baseURL;
    fetchJobs();
    fetchAnalytics();
  }, []);

  useEffect(() => {
    filterAndSortJobs();
  }, [jobs, searchTerm, filterCompany, filterExperience, filterStatus, sortBy]);

  const fetchJobs = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get('/jobs/', {
        headers: { Authorization: `Bearer ${token}` },
        params: { limit: 100 }
      });
      setJobs(response.data || []);
    } catch (error) {
      console.error('Error fetching jobs:', error);
      setJobs([]);
    } finally {
      setLoading(false);
    }
  };

  const fetchAnalytics = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get('/jobs/analytics/overview', {
        headers: { Authorization: `Bearer ${token}` }
      });
      setAnalytics(response.data);
    } catch (error) {
      console.error('Error fetching analytics:', error);
    }
  };

  const createJob = async () => {
    try {
      const token = localStorage.getItem('token');
      await axios.post('/jobs/', newJob, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      // Reset form and refresh jobs
      setNewJob({
        title: '',
        company: '',
        description: '',
        required_skills: [],
        experience_level: '',
        salary_range: '',
        location: '',
        remote_friendly: false,
        url: ''
      });
      setShowCreateForm(false);
      fetchJobs();
    } catch (error) {
      console.error('Error creating job:', error);
    }
  };

  const updateJobStatus = async (jobId, status) => {
    try {
      const token = localStorage.getItem('token');
      await axios.patch(`/api/jobs/${jobId}`, { status }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      fetchJobs();
    } catch (error) {
      console.error('Error updating job status:', error);
    }
  };

  const deleteJob = async (jobId) => {
    if (!window.confirm('Are you sure you want to delete this job posting?')) return;
    
    try {
      const token = localStorage.getItem('token');
      await axios.delete(`/jobs/${jobId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      fetchJobs();
    } catch (error) {
      console.error('Error deleting job:', error);
    }
  };

  const findSimilarJobs = async (jobId) => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`/api/jobs/${jobId}/similar`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      console.log('Similar jobs:', response.data);
      // You could show these in a modal or navigate to a results page
    } catch (error) {
      console.error('Error finding similar jobs:', error);
    }
  };

  const filterAndSortJobs = () => {
    let filtered = [...jobs];

    // Search filter
    if (searchTerm) {
      filtered = filtered.filter(job => 
        job.title?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        job.company?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        job.description?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        (job.required_skills || []).some(skill => 
          skill.toLowerCase().includes(searchTerm.toLowerCase())
        )
      );
    }

    // Company filter
    if (filterCompany !== 'all') {
      filtered = filtered.filter(job => job.company === filterCompany);
    }

    // Experience filter
    if (filterExperience !== 'all') {
      filtered = filtered.filter(job => {
        const jobLevel = (job.experience_level || '').toLowerCase();
        const filterLevel = filterExperience.toLowerCase();
        return jobLevel.includes(filterLevel) || 
               (filterLevel === 'mid' && jobLevel.includes('mid-level')) ||
               (filterLevel === 'entry' && jobLevel.includes('junior')) ||
               jobLevel === filterExperience;
      });
    }

    // Status filter
    if (filterStatus !== 'all') {
      filtered = filtered.filter(job => job.status === filterStatus);
    }

    // Sort
    filtered.sort((a, b) => {
      switch (sortBy) {
        case 'title':
          return (a.title || '').localeCompare(b.title || '');
        case 'company':
          return (a.company || '').localeCompare(b.company || '');
        case 'posted_date':
          return new Date(b.posted_date || b.created_at) - new Date(a.posted_date || a.created_at);
        case 'created_at':
        default:
          return new Date(b.created_at) - new Date(a.created_at);
      }
    });

    setFilteredJobs(filtered);
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'active': return '#38a169';
      case 'filled': return '#3182ce';
      case 'expired': return '#e53e3e';
      case 'paused': return '#d69e2e';
      default: return '#718096';
    }
  };

  const getExperienceLabel = (level) => {
    if (!level) return '';
    
    // Handle scraped job formats that may already be properly formatted
    if (level.includes('Mid-Level') || level.includes('Senior') || level.includes('Junior')) {
      return level;
    }
    
    const labels = {
      entry: 'Entry Level',
      junior: 'Junior',
      mid: 'Mid-Level', 
      senior: 'Senior',
      executive: 'Executive'
    };
    return labels[level.toLowerCase()] || level;
  };

  const getUniqueCompanies = () => {
    return [...new Set(jobs.map(job => job.company).filter(Boolean))];
  };

  if (loading) {
    return (
      <div className="jobs-loading">
        <div className="spinner-large"></div>
        <p>Loading jobs...</p>
      </div>
    );
  }

  return (
    <div className="jobs-page">
      <div className="page-container">
        <div className="page-header">
          <div>
            <h1 className="page-title">Job Management</h1>
            <p className="page-subtitle">
              AI-powered job posting management and candidate matching
            </p>
          </div>
          <button 
            onClick={() => setShowCreateForm(true)}
            className="btn btn-primary"
          >
            <Plus size={16} />
            Add Job Posting
          </button>
        </div>

        {/* Job Analytics */}
        <div className="jobs-stats">
          <div className="stat-item">
            <Briefcase size={20} />
            <div>
              <span className="stat-number">{analytics.active_jobs || jobs.filter(j => j.status === 'active').length}</span>
              <span className="stat-label">Active Jobs</span>
            </div>
          </div>
          <div className="stat-item">
            <Building size={20} />
            <div>
              <span className="stat-number">{Object.keys(analytics.jobs_by_company || {}).length || getUniqueCompanies().length}</span>
              <span className="stat-label">Companies</span>
            </div>
          </div>
          <div className="stat-item">
            <Users size={20} />
            <div>
              <span className="stat-number">{analytics.total_matches || 0}</span>
              <span className="stat-label">Total Matches</span>
            </div>
          </div>
          <div className="stat-item">
            <BarChart size={20} />
            <div>
              <span className="stat-number">
                {analytics.top_required_skills ? analytics.top_required_skills[0]?.skill || 'N/A' : 'N/A'}
              </span>
              <span className="stat-label">Top Skill</span>
            </div>
          </div>
        </div>

        {/* Filters */}
        <DashboardCard title="Filter Jobs" icon={Filter}>
          <div className="filters-container">
            <div className="search-box">
              <Search size={16} />
              <input
                type="text"
                placeholder="Search jobs by title, company, skills..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
            
            <div className="filters-row">
              <select
                value={filterCompany}
                onChange={(e) => setFilterCompany(e.target.value)}
                className="filter-select"
              >
                <option value="all">All Companies</option>
                {getUniqueCompanies().map(company => (
                  <option key={company} value={company}>{company}</option>
                ))}
              </select>
              
              <select
                value={filterExperience}
                onChange={(e) => setFilterExperience(e.target.value)}
                className="filter-select"
              >
                <option value="all">All Experience Levels</option>
                <option value="entry">Entry Level</option>
                <option value="mid">Mid-Level</option>
                <option value="senior">Senior</option>
                <option value="executive">Executive</option>
              </select>
              
              <select
                value={filterStatus}
                onChange={(e) => setFilterStatus(e.target.value)}
                className="filter-select"
              >
                <option value="all">All Status</option>
                <option value="active">Active</option>
                <option value="filled">Filled</option>
                <option value="expired">Expired</option>
                <option value="paused">Paused</option>
              </select>
              
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value)}
                className="filter-select"
              >
                <option value="created_at">Recently Added</option>
                <option value="posted_date">Posted Date</option>
                <option value="title">Job Title A-Z</option>
                <option value="company">Company A-Z</option>
              </select>
            </div>
          </div>
        </DashboardCard>

        {/* Create Job Form Modal */}
        {showCreateForm && (
          <div className="modal-overlay" onClick={() => setShowCreateForm(false)}>
            <div className="modal-content" onClick={(e) => e.stopPropagation()}>
              <div className="modal-header">
                <h2>Create New Job Posting</h2>
                <button onClick={() => setShowCreateForm(false)}>&times;</button>
              </div>
              <div className="modal-body">
                <div className="form-grid">
                  <input
                    type="text"
                    placeholder="Job Title"
                    value={newJob.title}
                    onChange={(e) => setNewJob({...newJob, title: e.target.value})}
                  />
                  <input
                    type="text"
                    placeholder="Company"
                    value={newJob.company}
                    onChange={(e) => setNewJob({...newJob, company: e.target.value})}
                  />
                  <input
                    type="text"
                    placeholder="Location"
                    value={newJob.location}
                    onChange={(e) => setNewJob({...newJob, location: e.target.value})}
                  />
                  <select
                    value={newJob.experience_level}
                    onChange={(e) => setNewJob({...newJob, experience_level: e.target.value})}
                  >
                    <option value="">Select Experience Level</option>
                    <option value="entry">Entry Level</option>
                    <option value="mid">Mid-Level</option>
                    <option value="senior">Senior</option>
                    <option value="executive">Executive</option>
                  </select>
                  <input
                    type="text"
                    placeholder="Salary Range (optional)"
                    value={newJob.salary_range}
                    onChange={(e) => setNewJob({...newJob, salary_range: e.target.value})}
                  />
                  <input
                    type="url"
                    placeholder="Job URL (optional)"
                    value={newJob.url}
                    onChange={(e) => setNewJob({...newJob, url: e.target.value})}
                  />
                </div>
                <textarea
                  placeholder="Job Description"
                  value={newJob.description}
                  onChange={(e) => setNewJob({...newJob, description: e.target.value})}
                  rows={4}
                />
                <input
                  type="text"
                  placeholder="Required Skills (comma-separated)"
                  value={newJob.required_skills.join(', ')}
                  onChange={(e) => setNewJob({...newJob, required_skills: e.target.value.split(',').map(s => s.trim()).filter(Boolean)})}
                />
                <label className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={newJob.remote_friendly}
                    onChange={(e) => setNewJob({...newJob, remote_friendly: e.target.checked})}
                  />
                  Remote Friendly
                </label>
              </div>
              <div className="modal-footer">
                <button onClick={() => setShowCreateForm(false)} className="btn btn-secondary">
                  Cancel
                </button>
                <button onClick={createJob} className="btn btn-primary">
                  <Brain size={14} />
                  Create with AI Analysis
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Jobs List */}
        <DashboardCard 
          title={`Job Postings (${filteredJobs.length})`} 
          icon={Briefcase}
        >
          {filteredJobs.length === 0 ? (
            <div className="no-jobs">
              <Briefcase size={48} />
              <h3>No job postings found</h3>
              <p>
                {jobs.length === 0 
                  ? "Start by creating your first job posting or configure career page scraping."
                  : "Try adjusting your search or filters."
                }
              </p>
              <div className="empty-state-actions">
                <button 
                  onClick={() => setShowCreateForm(true)}
                  className="btn btn-primary"
                >
                  Create Job Posting
                </button>
                <Link to="/career-pages" className="btn btn-secondary">
                  Configure Scraping
                </Link>
              </div>
            </div>
          ) : (
            <div className="jobs-list">
              {filteredJobs.map((job) => (
                <div key={job.id} className="job-card">
                  <div className="job-header">
                    <div className="job-info">
                      <h3 className="job-title">{job.title}</h3>
                      <div className="job-meta">
                        <span className="job-company">
                          <Building size={14} />
                          {job.company}
                        </span>
                        {job.location && (
                          <span className="job-location">
                            <MapPin size={14} />
                            {job.location}
                            {job.remote_friendly && ' (Remote OK)'}
                          </span>
                        )}
                        {job.experience_level && (
                          <span className="job-experience">
                            {getExperienceLabel(job.experience_level)}
                          </span>
                        )}
                      </div>
                    </div>
                    <div className="job-actions">
                      <span 
                        className="job-status"
                        style={{ color: getStatusColor(job.status) }}
                      >
                        {job.status?.charAt(0).toUpperCase() + job.status?.slice(1)}
                      </span>
                      <div className="job-buttons">
                        <button 
                          onClick={() => findSimilarJobs(job.id)}
                          className="btn btn-secondary btn-sm"
                          title="Find similar jobs"
                        >
                          <RefreshCw size={14} />
                        </button>
                        <Link 
                          to={`/jobs/${job.id}/matches`}
                          className="btn btn-secondary btn-sm"
                          title="View candidates"
                        >
                          <Users size={14} />
                          {job.match_count || 0}
                        </Link>
                      </div>
                    </div>
                  </div>
                  
                  <div className="job-content">
                    {job.description && (
                      <p className="job-description">
                        {job.description.length > 200 
                          ? `${job.description.substring(0, 200)}...`
                          : job.description
                        }
                      </p>
                    )}
                    
                    {job.required_skills && job.required_skills.length > 0 && (
                      <div className="job-skills">
                        <strong>Required Skills:</strong>
                        <div className="skills-tags">
                          {job.required_skills.slice(0, 6).map((skill, i) => (
                            <span key={i} className="skill-tag">
                              {skill}
                            </span>
                          ))}
                          {job.required_skills.length > 6 && (
                            <span className="skill-tag more">
                              +{job.required_skills.length - 6} more
                            </span>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                  
                  <div className="job-footer">
                    <div className="job-meta">
                      <Calendar size={14} />
                      <span>
                        {job.posted_date 
                          ? `Posted ${new Date(job.posted_date).toLocaleDateString()}`
                          : `Added ${new Date(job.created_at).toLocaleDateString()}`
                        }
                      </span>
                      {job.salary_range && (
                        <>
                          <span className="separator">•</span>
                          <span>{job.salary_range}</span>
                        </>
                      )}
                    </div>
                    
                    <div className="job-actions">
                      {job.url && (
                        <a 
                          href={job.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="btn btn-secondary btn-sm"
                        >
                          <ExternalLink size={14} />
                          View Original
                        </a>
                      )}
                      <button 
                        onClick={() => updateJobStatus(job.id, job.status === 'active' ? 'paused' : 'active')}
                        className="btn btn-secondary btn-sm"
                      >
                        {job.status === 'active' ? 'Pause' : 'Activate'}
                      </button>
                      <button 
                        onClick={() => deleteJob(job.id)}
                        className="btn btn-danger btn-sm"
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
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

export default Jobs;