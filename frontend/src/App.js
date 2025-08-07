import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './contexts/AuthContext';
import Layout from './components/Layout';
import Login from './pages/Login';
import Register from './pages/Register';
import EnhancedDashboard from './pages/EnhancedDashboard';
import CVMatching from './pages/CVMatching';
import ChatAgent from './pages/ChatAgent';
import Configuration from './pages/Configuration';
import GoogleDriveSetup from './pages/GoogleDriveSetup';
import History from './pages/History';
import Analytics from './pages/Analytics';
import Candidates from './pages/Candidates';
import LoadingSpinner from './components/LoadingSpinner';

function App() {
  const { user, loading } = useAuth();

  if (loading) {
    return <LoadingSpinner />;
  }

  return (
    <div className="App">
      <Routes>
        {!user ? (
          <>
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route path="*" element={<Navigate to="/login" />} />
          </>
        ) : (
          <Route path="*" element={
            <Layout>
              <Routes>
                <Route path="/dashboard" element={<EnhancedDashboard />} />
                <Route path="/chat-agent" element={<ChatAgent />} />
                <Route path="/cv-matching" element={<CVMatching />} />
                <Route path="/analytics" element={<Analytics />} />
                <Route path="/candidates" element={<Candidates />} />
                <Route path="/configuration" element={<Configuration />} />
                <Route path="/google-drive-setup" element={<GoogleDriveSetup />} />
                <Route path="/history" element={<History />} />
                <Route path="/" element={<Navigate to="/dashboard" />} />
                <Route path="*" element={<Navigate to="/dashboard" />} />
              </Routes>
            </Layout>
          } />
        )}
      </Routes>
    </div>
  );
}

export default App;