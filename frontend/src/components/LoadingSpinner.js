import React from 'react';

const LoadingSpinner = ({ message = 'Loading...' }) => {
  return (
    <div className="loading">
      <div style={{ textAlign: 'center' }}>
        <div className="spinner" />
        <p style={{ marginTop: '16px', color: '#718096' }}>{message}</p>
      </div>
    </div>
  );
};

export default LoadingSpinner;