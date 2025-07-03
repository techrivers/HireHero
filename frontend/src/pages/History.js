import React, { useState, useEffect } from 'react';
import axios from 'axios';
import API_CONFIG from '../config/api';
import { toast } from 'react-toastify';
import { 
  History as HistoryIcon, 
  Calendar, 
  FileText, 
  Users, 
  Download,
  Trash2,
  Eye
} from 'lucide-react';

const History = () => {
  const [matches, setMatches] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedMatch, setSelectedMatch] = useState(null);
  const [showDetails, setShowDetails] = useState(false);

  useEffect(() => {
    // Set axios base URL
    axios.defaults.baseURL = API_CONFIG.baseURL;
    axios.defaults.timeout = API_CONFIG.timeout;
    
    fetchHistory();
  }, []);

  const fetchHistory = async () => {
    try {
      const response = await axios.get('/cv-matching/history');
      setMatches(response.data);
    } catch (error) {
      toast.error('Failed to fetch matching history');
    } finally {
      setLoading(false);
    }
  };

  const deleteMatch = async (matchId) => {
    if (!window.confirm('Are you sure you want to delete this match?')) {
      return;
    }

    try {
      await axios.delete(`/cv-matching/history/${matchId}`);
      setMatches(matches.filter(match => match.id !== matchId));
      toast.success('Match deleted successfully');
    } catch (error) {
      toast.error('Failed to delete match');
    }
  };

  const exportMatch = async (matchId) => {
    try {
      const response = await axios.get(`/cv-matching/export/${matchId}`, {
        responseType: 'blob'
      });
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `cv-match-${matchId}.json`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      
      toast.success('Match exported successfully!');
    } catch (error) {
      toast.error('Failed to export match');
    }
  };

  const viewDetails = async (matchId) => {
    try {
      const response = await axios.get(`/cv-matching/history/${matchId}`);
      setSelectedMatch(response.data);
      setShowDetails(true);
    } catch (error) {
      toast.error('Failed to fetch match details');
    }
  };

  const getScoreColor = (score) => {
    if (score >= 80) return '#38a169';
    if (score >= 60) return '#d69e2e';
    return '#e53e3e';
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

  return (
    <div className="container">
      <div style={{ marginBottom: '32px' }}>
        <h1 style={{ fontSize: '32px', fontWeight: '700', marginBottom: '8px' }}>
          Matching History
        </h1>
        <p style={{ color: '#718096' }}>
          View and manage your previous CV matching sessions
        </p>
      </div>

      {matches.length === 0 ? (
        <div className="card">
          <div style={{ 
            textAlign: 'center', 
            padding: '60px 20px',
            color: '#718096'
          }}>
            <HistoryIcon size={64} style={{ opacity: 0.3, marginBottom: '16px' }} />
            <h3 style={{ fontSize: '18px', fontWeight: '600', marginBottom: '8px' }}>
              No Matching History
            </h3>
            <p>
              You haven't performed any CV matching yet. Start by creating your first match!
            </p>
          </div>
        </div>
      ) : (
        <div style={{ display: 'grid', gap: '16px' }}>
          {matches.map((match) => (
            <div key={match.id} className="card">
              <div style={{ 
                display: 'flex', 
                justifyContent: 'space-between', 
                alignItems: 'flex-start',
                marginBottom: '16px'
              }}>
                <div style={{ flex: 1 }}>
                  <h3 style={{ 
                    fontSize: '18px', 
                    fontWeight: '600', 
                    marginBottom: '8px',
                    color: '#2d3748'
                  }}>
                    {match.job_title || `Match #${match.id}`}
                  </h3>
                  
                  <div style={{ 
                    display: 'flex', 
                    alignItems: 'center', 
                    gap: '16px',
                    fontSize: '14px',
                    color: '#718096',
                    marginBottom: '12px'
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <Calendar size={14} />
                      {new Date(match.created_at).toLocaleDateString()}
                    </div>
                    
                    <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <Users size={14} />
                      {match.results?.length || 0} matches
                    </div>
                  </div>

                  <p style={{ 
                    fontSize: '14px', 
                    color: '#4a5568',
                    lineHeight: '1.5',
                    maxHeight: '60px',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis'
                  }}>
                    {match.job_description?.substring(0, 200)}
                    {match.job_description?.length > 200 && '...'}
                  </p>
                </div>

                <div style={{ 
                  display: 'flex', 
                  gap: '8px',
                  marginLeft: '16px'
                }}>
                  <button
                    onClick={() => viewDetails(match.id)}
                    className="btn btn-secondary"
                    style={{ padding: '8px 12px', fontSize: '12px' }}
                  >
                    <Eye size={14} />
                    View
                  </button>
                  
                  <button
                    onClick={() => exportMatch(match.id)}
                    className="btn btn-secondary"
                    style={{ padding: '8px 12px', fontSize: '12px' }}
                  >
                    <Download size={14} />
                    Export
                  </button>
                  
                  <button
                    onClick={() => deleteMatch(match.id)}
                    className="btn btn-danger"
                    style={{ padding: '8px 12px', fontSize: '12px' }}
                  >
                    <Trash2 size={14} />
                    Delete
                  </button>
                </div>
              </div>

              {/* Top matches preview */}
              {match.results && match.results.length > 0 && (
                <div>
                  <h4 style={{ 
                    fontSize: '14px', 
                    fontWeight: '600', 
                    marginBottom: '8px',
                    color: '#2d3748'
                  }}>
                    Top Matches:
                  </h4>
                  <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                    {match.results.slice(0, 3).map((result, index) => (
                      <div 
                        key={index}
                        style={{
                          background: '#f7fafc',
                          border: '1px solid #e2e8f0',
                          borderRadius: '6px',
                          padding: '8px 12px',
                          fontSize: '12px',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '6px'
                        }}
                      >
                        <span style={{ fontWeight: '500' }}>
                          {result.filename}
                        </span>
                        <span style={{ 
                          color: getScoreColor(result.score),
                          fontWeight: '600'
                        }}>
                          {result.score}%
                        </span>
                      </div>
                    ))}
                    {match.results.length > 3 && (
                      <div style={{
                        background: '#edf2f7',
                        border: '1px solid #e2e8f0',
                        borderRadius: '6px',
                        padding: '8px 12px',
                        fontSize: '12px',
                        color: '#718096'
                      }}>
                        +{match.results.length - 3} more
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Details Modal */}
      {showDetails && selectedMatch && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0, 0, 0, 0.5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000,
          padding: '20px'
        }}>
          <div style={{
            background: 'white',
            borderRadius: '8px',
            padding: '24px',
            maxWidth: '800px',
            width: '100%',
            maxHeight: '80vh',
            overflow: 'auto'
          }}>
            <div style={{ 
              display: 'flex', 
              justifyContent: 'space-between', 
              alignItems: 'center',
              marginBottom: '20px'
            }}>
              <h2 style={{ fontSize: '20px', fontWeight: '600' }}>
                Match Details
              </h2>
              <button
                onClick={() => setShowDetails(false)}
                style={{ 
                  background: 'none', 
                  border: 'none', 
                  fontSize: '20px',
                  cursor: 'pointer',
                  color: '#718096'
                }}
              >
                ×
              </button>
            </div>

            <div style={{ marginBottom: '20px' }}>
              <h3 style={{ fontSize: '16px', fontWeight: '600', marginBottom: '8px' }}>
                Job Description:
              </h3>
              <p style={{ 
                fontSize: '14px', 
                color: '#4a5568',
                lineHeight: '1.5',
                background: '#f7fafc',
                padding: '12px',
                borderRadius: '6px'
              }}>
                {selectedMatch.job_description}
              </p>
            </div>

            <div>
              <h3 style={{ fontSize: '16px', fontWeight: '600', marginBottom: '12px' }}>
                Results ({selectedMatch.results?.length || 0}):
              </h3>
              <div style={{ display: 'grid', gap: '12px', maxHeight: '300px', overflow: 'auto' }}>
                {selectedMatch.results?.map((result, index) => (
                  <div 
                    key={index}
                    style={{
                      border: '1px solid #e2e8f0',
                      borderRadius: '6px',
                      padding: '12px'
                    }}
                  >
                    <div style={{ 
                      display: 'flex', 
                      justifyContent: 'space-between', 
                      alignItems: 'center',
                      marginBottom: '8px'
                    }}>
                      <span style={{ fontWeight: '500' }}>
                        {result.filename}
                      </span>
                      <span style={{ 
                        color: getScoreColor(result.score),
                        fontWeight: '600'
                      }}>
                        {result.score}%
                      </span>
                    </div>
                    {result.reasoning && (
                      <p style={{ fontSize: '12px', color: '#718096' }}>
                        {result.reasoning}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default History;