import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import API_CONFIG from '../config/api';
import { 
  FileSearch, 
  Settings, 
  HardDrive, 
  History,
  CheckCircle,
  XCircle,
  AlertCircle
} from 'lucide-react';

const Dashboard = () => {
  const [status, setStatus] = useState({
    googleDrive: false,
    openaiApi: false,
    cvFolder: false
  });
  const [recentMatches, setRecentMatches] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Set axios base URL
    axios.defaults.baseURL = API_CONFIG.baseURL;
    axios.defaults.timeout = API_CONFIG.timeout;
    
    checkSystemStatus();
    fetchRecentMatches();
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
    } finally {
      setLoading(false);
    }
  };

  const fetchRecentMatches = async () => {
    try {
      const response = await axios.get('/cv-matching/history?limit=5');
      setRecentMatches(response.data);
    } catch (error) {
      console.error('Error fetching recent matches:', error);
    }
  };

  const StatusIcon = ({ status }) => {
    if (status) {
      return <CheckCircle size={20} style={{ color: '#38a169' }} />;
    }
    return <XCircle size={20} style={{ color: '#e53e3e' }} />;
  };

  if (loading) {
    return (
      <div className="container">
        <div className="loading">
          <div className="spinner" />
        </div>
      </div>
    );
  }

  const allConfigured = status.googleDrive && status.openaiApi && status.cvFolder;

  return (
    <div className="container">
      <div style={{ marginBottom: '32px' }}>
        <h1 style={{ fontSize: '32px', fontWeight: '700', marginBottom: '8px' }}>
          Dashboard
        </h1>
        <p style={{ color: '#718096' }}>
          Welcome to your Resume Matcher Agent dashboard
        </p>
      </div>

      {/* System Status */}
      <div className="card">
        <h2 style={{ fontSize: '20px', fontWeight: '600', marginBottom: '16px' }}>
          System Status
        </h2>
        
        {!allConfigured && (
          <div style={{ 
            background: '#fed7d7', 
            color: '#c53030', 
            padding: '12px 16px', 
            borderRadius: '6px', 
            marginBottom: '16px',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}>
            <AlertCircle size={16} />
            <span>System is not fully configured. Please complete the setup steps below.</span>
          </div>
        )}

        <div style={{ display: 'grid', gap: '12px' }}>
          <div style={{ 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'space-between',
            padding: '12px 0'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <StatusIcon status={status.googleDrive} />
              <span>Google Drive Integration</span>
            </div>
            {!status.googleDrive && (
              <Link to="/google-drive-setup" className="btn btn-primary" style={{ padding: '6px 12px', fontSize: '12px' }}>
                Setup
              </Link>
            )}
          </div>

          <div style={{ 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'space-between',
            padding: '12px 0'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <StatusIcon status={status.openaiApi} />
              <span>OpenAI API Configuration</span>
            </div>
            {!status.openaiApi && (
              <Link to="/configuration" className="btn btn-primary" style={{ padding: '6px 12px', fontSize: '12px' }}>
                Configure
              </Link>
            )}
          </div>

          <div style={{ 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'space-between',
            padding: '12px 0'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <StatusIcon status={status.cvFolder} />
              <span>Resume Folder Configuration</span>
            </div>
            {!status.cvFolder && (
              <Link to="/configuration" className="btn btn-primary" style={{ padding: '6px 12px', fontSize: '12px' }}>
                Configure
              </Link>
            )}
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="card">
        <h2 style={{ fontSize: '20px', fontWeight: '600', marginBottom: '16px' }}>
          Quick Actions
        </h2>
        
        <div style={{ 
          display: 'grid', 
          gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', 
          gap: '16px' 
        }}>
          <Link 
            to="/cv-matching"
            className="btn btn-primary"
            style={{ 
              padding: '20px', 
              flexDirection: 'column', 
              gap: '8px',
              textDecoration: 'none',
              opacity: allConfigured ? 1 : 0.6,
              pointerEvents: allConfigured ? 'auto' : 'none'
            }}
          >
            <FileSearch size={24} />
            <span>Match Resume</span>
            <span style={{ fontSize: '12px', opacity: 0.8 }}>
              Find the best candidates for your job
            </span>
          </Link>

          <Link 
            to="/configuration" 
            className="btn btn-secondary"
            style={{ 
              padding: '20px', 
              flexDirection: 'column', 
              gap: '8px',
              textDecoration: 'none'
            }}
          >
            <Settings size={24} />
            <span>Configuration</span>
            <span style={{ fontSize: '12px', opacity: 0.8 }}>
              Manage your API keys and settings
            </span>
          </Link>

          <Link 
            to="/google-drive-setup" 
            className="btn btn-secondary"
            style={{ 
              padding: '20px', 
              flexDirection: 'column', 
              gap: '8px',
              textDecoration: 'none'
            }}
          >
            <HardDrive size={24} />
            <span>Google Drive</span>
            <span style={{ fontSize: '12px', opacity: 0.8 }}>
              Connect your Google Drive account
            </span>
          </Link>

          <Link 
            to="/history" 
            className="btn btn-secondary"
            style={{ 
              padding: '20px', 
              flexDirection: 'column', 
              gap: '8px',
              textDecoration: 'none'
            }}
          >
            <History size={24} />
            <span>History</span>
            <span style={{ fontSize: '12px', opacity: 0.8 }}>
              View your matching history
            </span>
          </Link>
        </div>
      </div>

      {/* Recent Matches */}
      {recentMatches.length > 0 && (
        <div className="card">
          <div style={{ 
            display: 'flex', 
            justifyContent: 'space-between', 
            alignItems: 'center', 
            marginBottom: '16px' 
          }}>
            <h2 style={{ fontSize: '20px', fontWeight: '600' }}>
              Recent Matches
            </h2>
            <Link 
              to="/history" 
              style={{ color: '#3182ce', textDecoration: 'none', fontSize: '14px' }}
            >
              View All
            </Link>
          </div>
          
          <div style={{ display: 'grid', gap: '12px' }}>
            {recentMatches.slice(0, 3).map((match) => (
              <div 
                key={match.id}
                style={{
                  padding: '12px',
                  border: '1px solid #e2e8f0',
                  borderRadius: '6px',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center'
                }}
              >
                <div>
                  <p style={{ fontWeight: '500', marginBottom: '4px' }}>
                    {match.job_title || 'Job Match'}
                  </p>
                  <p style={{ fontSize: '12px', color: '#718096' }}>
                    {new Date(match.created_at).toLocaleDateString()}
                  </p>
                </div>
                <div style={{ 
                  fontSize: '14px', 
                  fontWeight: '500',
                  color: match.results?.length > 0 ? '#38a169' : '#718096'
                }}>
                  {match.results?.length || 0} matches
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default Dashboard;