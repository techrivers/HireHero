const API_CONFIG = {
  baseURL: process.env.REACT_APP_API_URL || 'http://localhost:9000/api',
  timeout: 300000, // 5 minutes - same as Resume matching, no cancellation
};

export default API_CONFIG;