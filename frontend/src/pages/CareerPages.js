import React, { useState, useEffect } from 'react';
import axios from 'axios';
import API_CONFIG from '../config/api';
import DashboardCard from '../components/DashboardCard';
import { 
  Globe, 
  Plus,
  Search,
  Calendar,
  CheckCircle,
  XCircle,
  AlertCircle,
  Settings,
  RefreshCw,
  Eye,
  Edit,
  Trash2,
  Play,
  Pause,
  BarChart,
  Clock
} from 'lucide-react';
import './CareerPages.css';

const CareerPages = () => {
  const [configs, setConfigs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [testingUrl, setTestingUrl] = useState(null);
  const [scrapingStats, setScrapingStats] = useState({});

  const [newConfig, setNewConfig] = useState({
    company_name: '',
    career_url: '',
    scrape_frequency: 24,
    is_active: true,
    scraping_rules: {
      job_title_selector: '',
      job_url_selector: '',
      job_description_selector: '',
      pagination_selector: '',
      max_pages: 10
    }
  });

  useEffect(() => {
    axios.defaults.baseURL = API_CONFIG.baseURL;
    fetchConfigs().then();
    fetchStats().then();
  }, []);

  const fetchConfigs = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get('/career-pages/', {
        headers: { Authorization: `Bearer ${token}` }
      });

      // Check different possible response structures
      const configsData = response.data.configs || response.data || [];
      setConfigs(Array.isArray(configsData) ? configsData : []);

      console.log('API Response:', response.data); // For debugging
    } catch (error) {
      console.error('Error fetching career page configs:', error);
      setConfigs([]);
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get('/career-pages/analytics/scraping-stats', {
        headers: { Authorization: `Bearer ${token}` }
      });
      setScrapingStats(response.data);
    } catch (error) {
      console.error('Error fetching scraping stats:', error);
    }
  };

  const createConfig = async () => {
    try {
      const token = localStorage.getItem('token');
      await axios.post('/career-pages/', newConfig, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      // Reset form and refresh configs
      setNewConfig({
        company_name: '',
        career_url: '',
        scrape_frequency: 24,
        is_active: true,
        scraping_rules: {
          job_title_selector: '',
          job_url_selector: '',
          job_description_selector: '',
          pagination_selector: '',
          max_pages: 10
        }
      });
      setShowCreateForm(false);
      fetchConfigs();
    } catch (error) {
      console.error('Error creating career page config:', error);
    }
  };

  const toggleConfigStatus = async (configId, currentStatus) => {
    try {
      const token = localStorage.getItem('token');
      await axios.patch(`/career-pages/${configId}`, { 
        is_active: !currentStatus 
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      fetchConfigs();
    } catch (error) {
      console.error('Error updating config status:', error);
    }
  };

  const deleteConfig = async (configId) => {
    if (!window.confirm('Are you sure you want to delete this career page configuration?')) return;
    
    try {
      const token = localStorage.getItem('token');
      await axios.delete(`/career-pages/${configId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      fetchConfigs();
    } catch (error) {
      console.error('Error deleting config:', error);
    }
  };

  const testScraping = async (configId) => {
    setTestingUrl(configId);
    try {
      const token = localStorage.getItem('token');
      const response = await axios.post(`/career-pages/${configId}/test`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      alert(`Test Results:\nJobs Found: ${response.data.jobs_found}\nSample Job: ${response.data.sample_job?.title || 'None'}`);
    } catch (error) {
      console.error('Error testing scraping:', error);
      alert('Test failed: ' + (error.response?.data?.detail || 'Unknown error'));
    } finally {
      setTestingUrl(null);
    }
  };

  const runScraping = async (configId) => {
    try {
      const token = localStorage.getItem('token');
      setTestingUrl(configId); // Show loading indicator

      const response = await axios.post(`/career-pages/${configId}/scrape`, {}, {
        headers: {Authorization: `Bearer ${token}`}
      });

      console.log('Scraping response:', response.data);

      if (response.data && response.data.status === 'success') {
        alert(`Scraping started successfully! ${response.data.message || 'Check back later for results.'}`);
      } else if (response.data && response.data.jobs_found !== undefined) {
        alert(`Scraping completed! Jobs found: ${response.data.jobs_found}`);
      } else {
        alert('Scraping started! Check back later for results.');
      }

      fetchConfigs();
    } catch (error) {
      console.error('Error running scraping:', error);
      alert(`Scraping failed: ${error.response?.data?.detail || error.message || 'Unknown error'}`);
    } finally {
      setTestingUrl(null); // Hide loading indicator
    }
  };

  const runAllScraping = async () => {
    try {
      const token = localStorage.getItem('token');
      await axios.post('/career-pages/scrape-all', {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      alert('Bulk scraping started for all active configurations!');
      fetchConfigs();
    } catch (error) {
      console.error('Error running bulk scraping:', error);
    }
  };

  const getStatusIcon = (lastSuccess, isActive) => {
    if (!isActive) return <Pause size={16} className="status-paused" />;
    if (lastSuccess === true) return <CheckCircle size={16} className="status-success" />;
    if (lastSuccess === false) return <XCircle size={16} className="status-error" />;
    return <AlertCircle size={16} className="status-pending" />;
  };

  const getStatusText = (lastSuccess, isActive) => {
    if (!isActive) return 'Paused';
    if (lastSuccess === true) return 'Success';
    if (lastSuccess === false) return 'Error';
    return 'Pending';
  };

  const formatLastScraped = (date) => {
    if (!date) return 'Never';
    const now = new Date();
    const scraped = new Date(date);
    const diffHours = Math.floor((now - scraped) / (1000 * 60 * 60));
    
    if (diffHours < 1) return 'Just now';
    if (diffHours < 24) return `${diffHours} hours ago`;
    const diffDays = Math.floor(diffHours / 24);
    if (diffDays < 7) return `${diffDays} days ago`;
    return scraped.toLocaleDateString();
  };

  if (loading) {
    return (
      <div className="career-pages-loading">
        <div className="spinner-large"></div>
        <p>Loading career page configurations...</p>
      </div>
    );
  }

  return (
    <div className="career-pages-page">
      <div className="page-container">
        <div className="page-header">
          <div>
            <h1 className="page-title">Career Page Scraping</h1>
            <p className="page-subtitle">
              Automated job discovery from company career pages
            </p>
          </div>
          <div className="header-actions">
            <button 
              onClick={runAllScraping}
              className="btn btn-secondary"
              disabled={configs.filter(c => c.is_active).length === 0}
            >
              <RefreshCw size={16} />
              Run All Active
            </button>
            <button 
              onClick={() => setShowCreateForm(true)}
              className="btn btn-primary"
            >
              <Plus size={16} />
              Add Career Page
            </button>
          </div>
        </div>

        {/* Scraping Statistics */}
        <div className="scraping-stats">
          <div className="stat-item">
            <Globe size={20} />
            <div>
              <span className="stat-number">{configs.length}</span>
              <span className="stat-label">Total Configs</span>
            </div>
          </div>
          <div className="stat-item">
            <CheckCircle size={20} />
            <div>
              <span className="stat-number">{configs.filter(c => c.is_active).length}</span>
              <span className="stat-label">Active</span>
            </div>
          </div>
          <div className="stat-item">
            <BarChart size={20} />
            <div>
              <span className="stat-number">{scrapingStats.total_jobs_scraped || 0}</span>
              <span className="stat-label">Jobs Scraped</span>
            </div>
          </div>
          <div className="stat-item">
            <Clock size={20} />
            <div>
              <span className="stat-number">
                {configs.length > 0 ? Math.round(configs.reduce((sum, c) => sum + (c.jobs_found_count || 0), 0) / configs.length) : 0}
              </span>
              <span className="stat-label">Avg Jobs/Page</span>
            </div>
          </div>
        </div>

        {/* Create Config Form Modal */}
        {showCreateForm && (
          <div className="modal-overlay" onClick={() => setShowCreateForm(false)}>
            <div className="modal-content large" onClick={(e) => e.stopPropagation()}>
              <div className="modal-header">
                <h2>Add Career Page Configuration</h2>
                <button onClick={() => setShowCreateForm(false)}>&times;</button>
              </div>
              <div className="modal-body">
                <div className="form-section">
                  <h3>Basic Information</h3>
                  <div className="form-grid">
                    <input
                      type="text"
                      placeholder="Company Name"
                      value={newConfig.company_name}
                      onChange={(e) => setNewConfig({...newConfig, company_name: e.target.value})}
                    />
                    <input
                      type="url"
                      placeholder="Career Page URL"
                      value={newConfig.career_url}
                      onChange={(e) => setNewConfig({...newConfig, career_url: e.target.value})}
                    />
                    <select
                      value={newConfig.scrape_frequency}
                      onChange={(e) => setNewConfig({...newConfig, scrape_frequency: parseInt(e.target.value)})}
                    >
                      <option value={1}>Every Hour</option>
                      <option value={6}>Every 6 Hours</option>
                      <option value={12}>Every 12 Hours</option>
                      <option value={24}>Daily</option>
                      <option value={168}>Weekly</option>
                    </select>
                    <label className="checkbox-label">
                      <input
                        type="checkbox"
                        checked={newConfig.is_active}
                        onChange={(e) => setNewConfig({...newConfig, is_active: e.target.checked})}
                      />
                      Active
                    </label>
                  </div>
                </div>

                <div className="form-section">
                  <h3>Scraping Rules (Optional - Leave blank for auto-detection)</h3>
                  <div className="form-grid">
                    <input
                      type="text"
                      placeholder="Job Title CSS Selector (e.g., .job-title)"
                      value={newConfig.scraping_rules.job_title_selector}
                      onChange={(e) => setNewConfig({
                        ...newConfig, 
                        scraping_rules: {
                          ...newConfig.scraping_rules,
                          job_title_selector: e.target.value
                        }
                      })}
                    />
                    <input
                      type="text"
                      placeholder="Job URL CSS Selector (e.g., .job-link)"
                      value={newConfig.scraping_rules.job_url_selector}
                      onChange={(e) => setNewConfig({
                        ...newConfig, 
                        scraping_rules: {
                          ...newConfig.scraping_rules,
                          job_url_selector: e.target.value
                        }
                      })}
                    />
                    <input
                      type="text"
                      placeholder="Job Description Selector (e.g., .job-description)"
                      value={newConfig.scraping_rules.job_description_selector}
                      onChange={(e) => setNewConfig({
                        ...newConfig, 
                        scraping_rules: {
                          ...newConfig.scraping_rules,
                          job_description_selector: e.target.value
                        }
                      })}
                    />
                    <input
                      type="text"
                      placeholder="Pagination Selector (e.g., .next-page)"
                      value={newConfig.scraping_rules.pagination_selector}
                      onChange={(e) => setNewConfig({
                        ...newConfig, 
                        scraping_rules: {
                          ...newConfig.scraping_rules,
                          pagination_selector: e.target.value
                        }
                      })}
                    />
                    <input
                      type="number"
                      placeholder="Max Pages to Scrape"
                      min="1"
                      max="50"
                      value={newConfig.scraping_rules.max_pages}
                      onChange={(e) => setNewConfig({
                        ...newConfig, 
                        scraping_rules: {
                          ...newConfig.scraping_rules,
                          max_pages: parseInt(e.target.value) || 10
                        }
                      })}
                    />
                  </div>
                </div>

                <div className="form-help">
                  <h4>Tips for Better Scraping:</h4>
                  <ul>
                    <li>Leave selectors blank to use automatic detection</li>
                    <li>Use browser developer tools to find CSS selectors</li>
                    <li>Test with a small max_pages value first</li>
                    <li>Some sites may require specific selectors for best results</li>
                  </ul>
                </div>
              </div>
              <div className="modal-footer">
                <button onClick={() => setShowCreateForm(false)} className="btn btn-secondary">
                  Cancel
                </button>
                <button onClick={createConfig} className="btn btn-primary">
                  Add Configuration
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Career Pages List */}
        <DashboardCard 
          title={`Career Page Configurations (${configs.length})`} 
          icon={Globe}
        >
          {configs.length === 0 ? (
            <div className="no-configs">
              <Globe size={48} />
              <h3>No career page configurations</h3>
              <p>
                Add your first career page configuration to start automatically discovering job postings.
              </p>
              <button 
                onClick={() => setShowCreateForm(true)}
                className="btn btn-primary"
              >
                Add Career Page
              </button>
            </div>
          ) : (
            <div className="configs-list">
              {configs.map((config) => (
                <div key={config.id} className="config-card">
                  <div className="config-header">
                    <div className="config-info">
                      <h3 className="config-company">{config.company_name}</h3>
                      <a 
                        href={config.career_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="config-url"
                      >
                        {config.career_url}
                      </a>
                      <div className="config-meta">
                        <span className="frequency">
                          <Clock size={14} />
                          Every {config.scrape_frequency}h
                        </span>
                        <span className="last-scraped">
                          <Calendar size={14} />
                          Last: {formatLastScraped(config.last_scraped)}
                        </span>
                      </div>
                    </div>
                    <div className="config-status">
                      {getStatusIcon(config.last_success, config.is_active)}
                      <span className={`status-text ${getStatusText(config.last_success, config.is_active).toLowerCase()}`}>
                        {getStatusText(config.last_success, config.is_active)}
                      </span>
                    </div>
                  </div>
                  
                  <div className="config-content">
                    <div className="config-stats">
                      <div className="stat">
                        <span className="stat-value">{config.jobs_found_count || 0}</span>
                        <span className="stat-label">Jobs Found</span>
                      </div>
                      <div className="stat">
                        <span className="stat-value">
                          {config.scraping_rules && Object.values(config.scraping_rules).some(v => v) ? 'Custom' : 'Auto'}
                        </span>
                        <span className="stat-label">Rules</span>
                      </div>
                    </div>
                    
                    {config.error_message && (
                      <div className="error-message">
                        <AlertCircle size={16} />
                        <span>{config.error_message}</span>
                      </div>
                    )}
                  </div>
                  
                  <div className="config-footer">
                    <div className="config-actions">
                      <button 
                        onClick={() => testScraping(config.id)}
                        className="btn btn-secondary btn-sm"
                        disabled={testingUrl === config.id}
                      >
                        {testingUrl === config.id ? (
                          <RefreshCw size={14} className="spinning" />
                        ) : (
                          <Eye size={14} />
                        )}
                        Test
                      </button>
                      
                      <button 
                        onClick={() => runScraping(config.id)}
                        className="btn btn-secondary btn-sm"
                        disabled={!config.is_active}
                      >
                        <Play size={14} />
                        Run Now
                      </button>
                      
                      <button 
                        onClick={() => toggleConfigStatus(config.id, config.is_active)}
                        className="btn btn-secondary btn-sm"
                      >
                        {config.is_active ? <Pause size={14} /> : <Play size={14} />}
                        {config.is_active ? 'Pause' : 'Activate'}
                      </button>
                      
                      <button 
                        onClick={() => deleteConfig(config.id)}
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

export default CareerPages;