import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { 
  LayoutDashboard, 
  FileSearch, 
  Settings, 
  History, 
  HardDrive,
  LogOut,
  MessageCircle
} from 'lucide-react';

const Navbar = () => {
  const { user, logout } = useAuth();
  const location = useLocation();

  const navItems = [
    { path: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { path: '/chat-agent', label: 'AI Chat', icon: MessageCircle },
    { path: '/resume-matching', label: 'Resume Matching', icon: FileSearch },
    { path: '/configuration', label: 'Configuration', icon: Settings },
    { path: '/google-drive-setup', label: 'Google Drive', icon: HardDrive },
    { path: '/history', label: 'History', icon: History },
  ];

  return (
    <nav className="nav">
      <div className="container">
        <div className="nav-content">
          <Link to="/dashboard" className="nav-brand">
            Resume Matcher Agent
          </Link>
          
          <div className="nav-links">
            {navItems.map((item) => {
              const Icon = item.icon;
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`nav-link ${location.pathname === item.path ? 'active' : ''}`}
                >
                  <Icon size={16} />
                  {item.label}
                </Link>
              );
            })}
            
            <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
              <span style={{ color: '#718096', fontSize: '14px' }}>
                Welcome, {user?.username}
              </span>
              <button
                onClick={logout}
                className="btn btn-secondary"
                style={{ padding: '8px 16px', fontSize: '12px' }}
              >
                <LogOut size={14} />
                Logout
              </button>
            </div>
          </div>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;