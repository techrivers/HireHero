import React, { useState, useEffect } from 'react';
import axios from 'axios';
import API_CONFIG from '../config/api';
import { toast } from 'react-toastify';
import { HardDrive, CheckCircle, ExternalLink, RefreshCw } from 'lucide-react';

const GoogleDriveSetup = () => {
  const [status, setStatus] = useState({
    connected: false,
    email: null,
    loading: true
  });
  const [authUrl, setAuthUrl] = useState('');
  const [isConnecting, setIsConnecting] = useState(false);

  useEffect(() => {
    // Set axios base URL
    axios.defaults.baseURL = API_CONFIG.baseURL;
    axios.defaults.timeout = API_CONFIG.timeout;
    
    checkGoogleDriveStatus();
  }, []);

  // Separate useEffect for window focus listener to avoid constant re-creation
  useEffect(() => {
    const handleWindowFocus = () => {
      if (isConnecting && !status.connected) {
        console.log('Window focused during connection, checking status...');
        setTimeout(() => {
          checkGoogleDriveStatus();
        }, 500);
      }
    };

    window.addEventListener('focus', handleWindowFocus);
    
    return () => {
      window.removeEventListener('focus', handleWindowFocus);
    };
  }, [isConnecting, status.connected]);

  const checkGoogleDriveStatus = async () => {
    try {
      console.log('Checking Google Drive status...');
      const response = await axios.get('/google-drive/status');
      console.log('Google Drive status response:', response.data);
      setStatus({
        connected: response.data.is_connected,
        email: response.data.email || null,
        loading: false
      });
    } catch (error) {
      console.error('Error checking Google Drive status:', error);
      setStatus({
        connected: false,
        email: null,
        loading: false
      });
    }
  };

  const startGoogleDriveAuth = async () => {
    try {
      setIsConnecting(true);
      const response = await axios.get('/google-drive/auth');
      setAuthUrl(response.data.authorization_url);
      
      // Open auth URL in new window
      const authWindow = window.open(response.data.authorization_url, 'google-auth', 'width=500,height=600');
      
      // Check if popup was blocked
      if (!authWindow || authWindow.closed) {
        setIsConnecting(false);
        toast.error('Popup was blocked. Please allow popups for this site and try again.');
        return;
      }
      
      // Track if we've received a message response
      let messageReceived = false;
      
      // Additional safety net: Auto-refresh after 10 seconds if still connecting
      const safetyTimeout = setTimeout(() => {
        console.log('Safety timeout triggered, checking status...');
        setIsConnecting(false);
        checkGoogleDriveStatus();
        clearInterval(checkClosed);
        window.removeEventListener('message', handleMessage);
      }, 10000);

      // Listen for messages from the popup window
      const handleMessage = (event) => {
        if (event.data && event.data.type === 'GOOGLE_AUTH_SUCCESS') {
          messageReceived = true;
          clearTimeout(safetyTimeout);
          toast.success('Google Drive connected successfully!');
          checkGoogleDriveStatus();
          setIsConnecting(false);
          window.removeEventListener('message', handleMessage);
        } else if (event.data && event.data.type === 'GOOGLE_AUTH_ERROR') {
          messageReceived = true;
          clearTimeout(safetyTimeout);
          toast.error(`Authentication failed: ${event.data.error}`);
          setIsConnecting(false);
          window.removeEventListener('message', handleMessage);
        }
      };
      
      window.addEventListener('message', handleMessage);
      
      // Enhanced polling: Check if window is closed and handle both success/cancel cases
      const checkClosed = setInterval(() => {
        if (authWindow.closed) {
          clearInterval(checkClosed);
          clearTimeout(safetyTimeout);
          window.removeEventListener('message', handleMessage);
          
          // If window closed and no message received, still check status
          // This handles cases where user completed auth but message wasn't received
          if (!messageReceived) {
            console.log('Auth window closed, checking status...');
            setIsConnecting(false);
            
            // Wait a bit for server to process the callback, then check status
            setTimeout(() => {
              checkGoogleDriveStatus();
            }, 1500);
          }
        }
      }, 500); // Check more frequently (every 500ms instead of 1000ms)
      
    } catch (error) {
      toast.error('Failed to start Google Drive authentication');
      setIsConnecting(false);
    }
  };

  const disconnectGoogleDrive = async () => {
    try {
      await axios.post('/google-drive/disconnect');
      setStatus({
        connected: false,
        email: null,
        loading: false
      });
      toast.success('Google Drive disconnected successfully');
    } catch (error) {
      toast.error('Failed to disconnect Google Drive');
    }
  };

  const testConnection = async () => {
    try {
      const response = await axios.get('/google-drive/test');
      toast.success(`Connection test successful! Found ${response.data.file_count} files in your drive.`);
    } catch (error) {
      toast.error('Connection test failed');
    }
  };

  const refreshStatus = async () => {
    setStatus(prev => ({ ...prev, loading: true }));
    await checkGoogleDriveStatus();
    toast.info('Status refreshed');
  };

  if (status.loading) {
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
          Google Drive Setup
        </h1>
        <p style={{ color: '#718096' }}>
          Connect your Google Drive account to access your CV files
        </p>
      </div>

      <div className="card">
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginBottom: '24px' }}>
          <HardDrive size={32} style={{ color: '#3182ce' }} />
          <div>
            <h2 style={{ fontSize: '20px', fontWeight: '600', marginBottom: '4px' }}>
              Google Drive Integration
            </h2>
            <p style={{ color: '#718096', fontSize: '14px' }}>
              Access and analyze CV files stored in your Google Drive
            </p>
          </div>
        </div>

        {status.connected ? (
          <div>
            <div style={{ 
              background: '#c6f6d5', 
              color: '#22543d', 
              padding: '16px', 
              borderRadius: '8px', 
              marginBottom: '24px',
              display: 'flex',
              alignItems: 'center',
              gap: '12px'
            }}>
              <CheckCircle size={20} />
              <div>
                <p style={{ fontWeight: '500', marginBottom: '4px' }}>
                  Google Drive Connected Successfully!
                </p>
                {status.email ? (
                  <p style={{ fontSize: '14px', opacity: 0.8 }}>
                    Connected as: {status.email}
                  </p>
                ) : (
                  <p style={{ fontSize: '14px', opacity: 0.8 }}>
                    Your Google Drive account is now connected and ready to use.
                  </p>
                )}
              </div>
            </div>

            <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
              <button
                onClick={testConnection}
                className="btn btn-primary"
              >
                <RefreshCw size={16} />
                Test Connection
              </button>
              
              <button
                onClick={refreshStatus}
                className="btn btn-secondary"
                disabled={status.loading}
              >
                <RefreshCw size={16} />
                Refresh Status
              </button>
              
              <button
                onClick={disconnectGoogleDrive}
                className="btn btn-danger"
              >
                Disconnect
              </button>
            </div>

            <div style={{ 
              marginTop: '24px', 
              padding: '16px', 
              background: '#f7fafc', 
              borderRadius: '8px' 
            }}>
              <h3 style={{ fontSize: '16px', fontWeight: '600', marginBottom: '8px' }}>
                Next Steps:
              </h3>
              <ul style={{ paddingLeft: '20px', color: '#4a5568' }}>
                <li>Make sure your CV files are uploaded to Google Drive</li>
                <li>Configure your CV folder name in the Configuration page</li>
                <li>Start matching CVs to job descriptions</li>
              </ul>
            </div>
          </div>
        ) : (
          <div>
            <div style={{ marginBottom: '24px' }}>
              <h3 style={{ fontSize: '18px', fontWeight: '600', marginBottom: '12px' }}>
                Why Connect Google Drive?
              </h3>
              <ul style={{ paddingLeft: '20px', color: '#4a5568', lineHeight: '1.6' }}>
                <li>Access your CV files directly from Google Drive</li>
                <li>Automatically process and analyze resume documents</li>
                <li>Keep your files secure and organized in one place</li>
                <li>Support for PDF, DOC, and DOCX formats</li>
              </ul>
            </div>

            <div style={{ marginBottom: '24px' }}>
              <h3 style={{ fontSize: '18px', fontWeight: '600', marginBottom: '12px' }}>
                Required Permissions:
              </h3>
              <ul style={{ paddingLeft: '20px', color: '#4a5568', lineHeight: '1.6' }}>
                <li>Read access to your Google Drive files</li>
                <li>View metadata of your files (name, size, type)</li>
                <li>Download files for processing (files are not stored permanently)</li>
              </ul>
            </div>

            <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', marginBottom: '16px' }}>
              <button
                onClick={startGoogleDriveAuth}
                className="btn btn-primary"
                disabled={isConnecting}
              >
                {isConnecting ? (
                  <>
                    <div className="spinner" style={{ width: '16px', height: '16px' }} />
                    Connecting...
                  </>
                ) : (
                  <>
                    <ExternalLink size={16} />
                    Connect Google Drive
                  </>
                )}
              </button>
              
              <button
                onClick={refreshStatus}
                className="btn btn-secondary"
                disabled={status.loading || isConnecting}
              >
                <RefreshCw size={16} />
                Refresh Status
              </button>
            </div>

            {authUrl && (
              <div style={{ 
                background: '#edf2f7', 
                padding: '12px', 
                borderRadius: '6px',
                fontSize: '14px',
                color: '#4a5568'
              }}>
                <p>
                  If the popup window didn't open, you can{' '}
                  <a 
                    href={authUrl} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    style={{ color: '#3182ce' }}
                  >
                    click here to authenticate manually
                  </a>
                </p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default GoogleDriveSetup;