import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import API_CONFIG from '../config/api';
import DashboardCard, { StatCard, MetricCard } from '../components/DashboardCard';
import { 
  FileSearch, 
  Settings, 
  HardDrive, 
  History,
  CheckCircle,
  XCircle,
  AlertCircle,
  Users,
  TrendingUp,
  Award,
  Target,
  MessageCircle,
  BarChart3,
  Clock,
  ArrowUpRight,
  ArrowDownRight
} from 'lucide-react';
import './EnhancedDashboard.css';

const EnhancedDashboard = () => {
  const [status, setStatus] = useState({
    googleDrive: false,
    openaiApi: false,
    cvFolder: false
  });
  const [dashboardStats, setDashboardStats] = useState(null);
  const [recentActivity, setRecentActivity] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Set axios base URL
    axios.defaults.baseURL = API_CONFIG.baseURL;
    axios.defaults.timeout = API_CONFIG.timeout;
    
    Promise.all([
      checkSystemStatus(),
      fetchDashboardStats()
    ]).finally(() => setLoading(false));
  }, []);

  const checkSystemStatus = async () => {
    try {
      // Check Google Drive status
      try {
        const driveResponse = await axios.get('/google-drive/status');
        setStatus(prev => ({ ...prev, googleDrive: driveResponse.data.is_connected }));
      } catch (error) {
        setStatus(prev => ({ ...prev, googleDrive: false }));
      }

      // Check configuration
      try {
        const configResponse = await axios.get('/config/');
        const config = configResponse.data;
        setStatus(prev => ({
          ...prev,
          openaiApi: !!config.openai_api_key,
          cvFolder: !!config.cv_folder_name
        }));
      } catch (error) {
        setStatus(prev => ({
          ...prev,
          openaiApi: false,
          cvFolder: false
        }));
      }
    } catch (error) {
      console.error('Error checking system status:', error);
    }
  };

  const fetchDashboardStats = async () => {
    try {
      const response = await axios.get('/analytics/dashboard-stats');
      setDashboardStats(response.data);
      setRecentActivity(response.data.recent_activity || []);
    } catch (error) {
      console.error('Error fetching dashboard stats:', error);
      // Set default values if API fails
      setDashboardStats({
        total_matches: 0,
        matches_this_week: 0,
        matches_this_month: 0,
        total_candidates: 0,
        avg_match_score: 0,
        success_rate: 0,
        top_skills: [],
        recent_activity: [],
        week_over_week_change: 0,
        month_over_month_change: 0
      });
    }
  };

  const StatusIcon = ({ status }) => {
    if (status) {
      return <CheckCircle size={20} style={{ color: '#38a169' }} />;
    }
    return <XCircle size={20} style={{ color: '#e53e3e' }} />;
  };

  const formatChange = (change) => {
    if (!change) return null;
    const isPositive = change > 0;
    const Icon = isPositive ? ArrowUpRight : ArrowDownRight;
    return (
      <span className={`change ${isPositive ? 'positive' : 'negative'}`}>
        <Icon size={14} />
        {Math.abs(change)}%
      </span>
    );
  };

  const allConfigured = status.googleDrive && status.openaiApi && status.cvFolder;

  if (loading) {
    return (
      <div className="dashboard-loading">
        <div className="spinner-large"></div>
        <p>Loading dashboard...</p>
      </div>
    );
  }

  return (
    <div className="enhanced-dashboard">
      <div className="page-container">
        {/* Page Header */}
        <div className="page-header">
          <h1 className="page-title">Dashboard</h1>
          <p className="page-subtitle">
            Welcome to your Resume Matcher Agent dashboard
          </p>
        </div>

        {/* System Status Alert */}
        {!allConfigured && (
          <div className="alert alert-warning">
            <AlertCircle size={16} />
            <span>System is not fully configured. Please complete the setup steps below.</span>
          </div>
        )}

        {/* Key Metrics */}
        {dashboardStats && (
          <div className="dashboard-grid four-columns">
            <StatCard
              title="Total Matches"
              value={dashboardStats.total_matches}
              icon={Target}
              className="stat-primary"
              change={formatChange(dashboardStats.week_over_week_change)}
              changeType={dashboardStats.week_over_week_change > 0 ? 'positive' : 'negative'}
            />
            
            <StatCard
              title="Candidates Evaluated"
              value={dashboardStats.total_candidates}
              icon={Users}
              className="stat-success"
              change={formatChange(dashboardStats.month_over_month_change)}
              changeType={dashboardStats.month_over_month_change > 0 ? 'positive' : 'negative'}
            />
            
            <StatCard
              title="Avg Match Score"
              value={`${dashboardStats.avg_match_score}%`}
              icon={Award}
              className="stat-warning"
            />
            
            <StatCard
              title="Success Rate"
              value={`${dashboardStats.success_rate}%`}
              icon={TrendingUp}
              className="stat-info"
            />
          </div>
        )}

        <div className="dashboard-grid three-columns">
          {/* System Status Card */}
          <DashboardCard 
            title="System Status" 
            icon={Settings}
            className="status-card"
          >
            <div className="status-list">
              <div className="status-item">
                <div className="status-info">
                  <StatusIcon status={status.googleDrive} />
                  <span>Google Drive Integration</span>
                </div>
                {!status.googleDrive && (
                  <Link to="/google-drive-setup" className="btn btn-primary btn-sm">
                    Setup
                  </Link>
                )}
              </div>

              <div className="status-item">
                <div className="status-info">
                  <StatusIcon status={status.openaiApi} />
                  <span>OpenAI API Configuration</span>
                </div>
                {!status.openaiApi && (
                  <Link to="/configuration" className="btn btn-primary btn-sm">
                    Configure
                  </Link>
                )}
              </div>

              <div className="status-item">
                <div className="status-info">
                  <StatusIcon status={status.cvFolder} />
                  <span>Resume Folder Configuration</span>
                </div>
                {!status.cvFolder && (
                  <Link to="/configuration" className="btn btn-primary btn-sm">
                    Configure
                  </Link>
                )}
              </div>
            </div>
          </DashboardCard>

          {/* Quick Actions Card */}
          <DashboardCard title="Quick Actions" icon={Target}>
            <div className="quick-actions">
              <Link 
                to="/resume-matching"
                className={`action-item ${!allConfigured ? 'disabled' : ''}`}
                onClick={(e) => !allConfigured && e.preventDefault()}
              >
                <FileSearch size={20} />
                <div>
                  <span className="action-title">Match Resumes</span>
                  <span className="action-subtitle">Find the best candidates</span>
                </div>
              </Link>

              <Link to="/chat-agent" className="action-item">
                <MessageCircle size={20} />
                <div>
                  <span className="action-title">AI Chat</span>
                  <span className="action-subtitle">Intelligent conversations</span>
                </div>
              </Link>

              <Link to="/analytics" className="action-item">
                <BarChart3 size={20} />
                <div>
                  <span className="action-title">Analytics</span>
                  <span className="action-subtitle">View insights</span>
                </div>
              </Link>
            </div>
          </DashboardCard>

          {/* Top Skills Card */}
          {dashboardStats && dashboardStats.top_skills && (
            <MetricCard
              title="Top Skills This Month"
              metrics={dashboardStats.top_skills.map(skill => ({
                label: skill.skill,
                value: skill.count
              }))}
            />
          )}
        </div>

        {/* Recent Activity */}
        {recentActivity.length > 0 && (
          <DashboardCard 
            title="Recent Activity" 
            icon={Clock}
            action={
              <Link to="/history" className="btn btn-link">
                View All
              </Link>
            }
          >
            <div className="activity-card">
              {recentActivity.slice(0, 5).map((activity) => (
                <div key={activity.id} className="activity-item">
                  <div className="activity-icon">
                    <FileSearch size={16} />
                  </div>
                  <div className="activity-content">
                    <h4 className="activity-title">{activity.job_title}</h4>
                    <p className="activity-description">
                      {activity.candidates_found} candidates found
                    </p>
                  </div>
                  <div className="activity-time">
                    {new Date(activity.created_at).toLocaleDateString()}
                  </div>
                </div>
              ))}
            </div>
          </DashboardCard>
        )}

        {/* Getting Started Card */}
        {!allConfigured && (
          <DashboardCard title="Getting Started" icon={AlertCircle}>
            <div className="getting-started">
              <p>Complete these steps to start matching resumes:</p>
              <ol>
                <li>
                  <Link to="/google-drive-setup">Connect your Google Drive</Link>
                  {status.googleDrive && <CheckCircle size={16} color="#38a169" />}
                </li>
                <li>
                  <Link to="/configuration">Configure OpenAI API key</Link>
                  {status.openaiApi && <CheckCircle size={16} color="#38a169" />}
                </li>
                <li>
                  <Link to="/configuration">Set resume folder name</Link>
                  {status.cvFolder && <CheckCircle size={16} color="#38a169" />}
                </li>
              </ol>
            </div>
          </DashboardCard>
        )}
      </div>
    </div>
  );
};

export default EnhancedDashboard;