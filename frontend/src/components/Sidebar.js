import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { 
  LayoutDashboard, 
  FileSearch, 
  Settings, 
  History, 
  HardDrive,
  LogOut,
  MessageCircle,
  Menu,
  X,
  User,
  BarChart3,
  Users
} from 'lucide-react';
import './Sidebar.css';

const Sidebar = () => {
  const { user, logout } = useAuth();
  const location = useLocation();
  const [isCollapsed, setIsCollapsed] = useState(false);

  const navItems = [
    { 
      path: '/dashboard', 
      label: 'Dashboard', 
      icon: LayoutDashboard,
      category: 'main'
    },
    { 
      path: '/chat-agent', 
      label: 'AI Chat', 
      icon: MessageCircle,
      category: 'main'
    },
    { 
      path: '/cv-matching',
      label: 'Resume Matching', 
      icon: FileSearch,
      category: 'main'
    },
    { 
      path: '/analytics', 
      label: 'Analytics', 
      icon: BarChart3,
      category: 'insights'
    },
    { 
      path: '/candidates', 
      label: 'Candidates', 
      icon: Users,
      category: 'insights'
    },
    { 
      path: '/history', 
      label: 'History', 
      icon: History,
      category: 'insights'
    },
    { 
      path: '/configuration', 
      label: 'Configuration', 
      icon: Settings,
      category: 'settings'
    },
    { 
      path: '/google-drive-setup', 
      label: 'Google Drive', 
      icon: HardDrive,
      category: 'settings'
    }
  ];

  const categories = {
    main: 'Main',
    insights: 'Insights',
    settings: 'Settings'
  };

  const toggleSidebar = () => {
    setIsCollapsed(!isCollapsed);
  };

  const handleLogout = () => {
    logout();
  };

  return (
    <div className={`sidebar ${isCollapsed ? 'collapsed' : ''}`}>
      {/* Sidebar Header */}
      <div className="sidebar-header">
        <div className="sidebar-brand">
          {!isCollapsed && (
            <span className="brand-text">Resume Matcher</span>
          )}
          <button className="toggle-btn" onClick={toggleSidebar}>
            {isCollapsed ? <Menu size={20} /> : <X size={20} />}
          </button>
        </div>
      </div>

      {/* Navigation Items */}
      <div className="sidebar-nav">
        {Object.entries(categories).map(([categoryKey, categoryLabel]) => (
          <div key={categoryKey} className="nav-category">
            {!isCollapsed && (
              <div className="category-label">{categoryLabel}</div>
            )}
            
            {navItems
              .filter(item => item.category === categoryKey)
              .map((item) => {
                const Icon = item.icon;
                const isActive = location.pathname === item.path;
                
                return (
                  <Link
                    key={item.path}
                    to={item.path}
                    className={`nav-item ${isActive ? 'active' : ''}`}
                    title={isCollapsed ? item.label : ''}
                  >
                    <div className="nav-icon">
                      <Icon size={20} />
                    </div>
                    {!isCollapsed && (
                      <span className="nav-label">{item.label}</span>
                    )}
                    {isActive && <div className="active-indicator" />}
                  </Link>
                );
              })}
          </div>
        ))}
      </div>

      {/* User Profile Section */}
      <div className="sidebar-footer">
        <div className="user-profile">
          <div className="user-avatar">
            <User size={20} />
          </div>
          {!isCollapsed && (
            <div className="user-info">
              <div className="user-name">{user?.username || 'User'}</div>
              <div className="user-email">{user?.email || 'user@example.com'}</div>
            </div>
          )}
        </div>
        
        <button
          onClick={handleLogout}
          className="logout-btn"
          title={isCollapsed ? 'Logout' : ''}
        >
          <LogOut size={18} />
          {!isCollapsed && <span>Logout</span>}
        </button>
      </div>
    </div>
  );
};

export default Sidebar;