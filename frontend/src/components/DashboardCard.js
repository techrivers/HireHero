import React from 'react';
import './DashboardCard.css';

const DashboardCard = ({ 
  title, 
  children, 
  icon: Icon, 
  className = '', 
  action,
  loading = false,
  ...props 
}) => {
  return (
    <div className={`dashboard-card ${className}`} {...props}>
      <div className="card-header">
        {Icon && (
          <div className="card-icon">
            <Icon size={20} />
          </div>
        )}
        <h3 className="card-title">{title}</h3>
        {action && (
          <div className="card-action">
            {action}
          </div>
        )}
      </div>
      
      <div className="card-content">
        {loading ? (
          <div className="card-loading">
            <div className="spinner-small"></div>
          </div>
        ) : (
          children
        )}
      </div>
    </div>
  );
};

export const StatCard = ({ 
  title, 
  value, 
  icon: Icon, 
  change, 
  changeType = 'neutral',
  className = '',
  onClick,
  ...props
}) => {
  const handleProps = onClick ? {
    onClick,
    tabIndex: 0,
    role: 'button',
    'aria-label': `${title}: ${value}`,
    onKeyDown: (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        onClick(e);
      }
    }
  } : {};
  
  return (
    <div className={`stat-card ${className}`} {...handleProps} {...props}>
      <div className="stat-header">
        <div>
          <h4 className="stat-title">{title}</h4>
          <div className="stat-value">{value}</div>
        </div>
        {Icon && (
          <div className="stat-icon">
            <Icon size={24} />
          </div>
        )}
      </div>
      
      {change && (
        <div className={`stat-change ${changeType}`}>
          {change}
        </div>
      )}
    </div>
  );
};

export const MetricCard = ({ 
  title, 
  metrics = [], 
  className = '' 
}) => {
  return (
    <div className={`metric-card ${className}`}>
      <h4 className="metric-title">{title}</h4>
      <div className="metric-list">
        {metrics.map((metric, index) => (
          <div key={index} className="metric-item">
            <span className="metric-label">{metric.label}</span>
            <span className="metric-value">{metric.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

export default DashboardCard;