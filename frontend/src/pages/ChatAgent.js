import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import API_CONFIG from '../config/api';
import { toast } from 'react-toastify';
import { 
  MessageCircle, 
  Send, 
  Bot, 
  User, 
  Search, 
  Sparkles,
  History,
  RefreshCw,
  ChevronRight
} from 'lucide-react';

const ChatAgent = () => {
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const [suggestions, setSuggestions] = useState([]);
  const [searchResults, setSearchResults] = useState(null);
  const [showResults, setShowResults] = useState(false);
  const [conversationHistory, setConversationHistory] = useState([]);
  const [wsConnection, setWsConnection] = useState(null);
  const [connectionStatus, setConnectionStatus] = useState('disconnected');
  const [cvStatus, setCvStatus] = useState({ status: 'unknown', cv_count: 0 });
  const messagesEndRef = useRef(null);

  useEffect(() => {
    // Set axios configuration
    axios.defaults.baseURL = API_CONFIG.baseURL;
    axios.defaults.timeout = API_CONFIG.timeout;
    
    // Initialize WebSocket connection and chat
    initializeWebSocket();
    initializeChat();
    
    // Load conversation history
    loadConversationHistory();
    
    // Cleanup on component unmount
    return () => {
      if (wsConnection) {
        wsConnection.close();
      }
    };
  }, []);

  useEffect(() => {
    // Scroll to bottom when messages change
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const initializeWebSocket = () => {
    try {
      const token = localStorage.getItem('access_token');
      if (!token) {
        console.log('No access token found, skipping WebSocket initialization');
        return;
      }

      // For now, we'll disable WebSocket and use REST API only
      // This prevents the build error and the app will work with HTTP requests
      setConnectionStatus('http_only');
      console.log('WebSocket disabled, using HTTP API only');
      
    } catch (error) {
      console.error('WebSocket initialization error:', error);
      setConnectionStatus('error');
    }
  };

  const initializeChat = async () => {
    try {
      const response = await axios.post('/chat', {
        message: 'hello',
        session_id: sessionId
      });
      
      setSessionId(response.data.session_id);
      setMessages([{
        id: Date.now(),
        role: 'assistant',
        content: response.data.message,
        timestamp: response.data.timestamp,
        action: response.data.action
      }]);
      setSuggestions(response.data.suggestions || []);
      
    } catch (error) {
      console.error('Error initializing chat:', error);
      toast.error('Failed to initialize chat agent');
    }
  };

  const loadConversationHistory = async () => {
    try {
      const response = await axios.get('/chat/conversations');
      setConversationHistory(response.data);
    } catch (error) {
      console.error('Error loading conversation history:', error);
    }
  };

  const sendMessage = async (messageText = null) => {
    const message = messageText || inputMessage.trim();
    if (!message) return;

    setIsLoading(true);
    setInputMessage('');

    // Add user message to UI
    const userMessage = {
      id: Date.now(),
      role: 'user',
      content: message,
      timestamp: new Date().toISOString()
    };
    setMessages(prev => [...prev, userMessage]);

    // Try WebSocket first, fallback to REST API
    if (wsConnection && wsConnection.readyState === WebSocket.OPEN) {
      try {
        wsConnection.send(JSON.stringify({
          message: message,
          session_id: sessionId
        }));
        return; // WebSocket message sent, exit function
      } catch (error) {
        console.error('WebSocket send error:', error);
        // Fall through to REST API
      }
    }

    try {
      const response = await axios.post('/chat', {
        message: message,
        session_id: sessionId
      });

      // Add AI response to UI
      const aiMessage = {
        id: Date.now() + 1,
        role: 'assistant',
        content: response.data.message,
        timestamp: response.data.timestamp,
        action: response.data.action
      };
      setMessages(prev => [...prev, aiMessage]);
      
      // Update suggestions
      setSuggestions(response.data.suggestions || []);
      
      // Handle different actions
      if (response.data.action === 'show_results' && response.data.results) {
        setSearchResults(response.data.results);
        setShowResults(true);
      } else if (response.data.action === 'ready_to_search') {
        // Show search button
      }
      
    } catch (error) {
      console.error('Error sending message:', error);
      toast.error('Failed to send message');
      
      // Add error message
      const errorMessage = {
        id: Date.now() + 1,
        role: 'assistant',
        content: 'I apologize, but I encountered an error. Please try again.',
        timestamp: new Date().toISOString(),
        action: 'error'
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const executeSearch = async () => {
    if (!sessionId) return;
    
    setIsLoading(true);
    
    try {
      const response = await axios.post('/chat/search', {
        session_id: sessionId
      });
      
      // Add search result message
      const searchMessage = {
        id: Date.now(),
        role: 'assistant',
        content: response.data.message,
        timestamp: response.data.timestamp,
        action: response.data.action
      };
      setMessages(prev => [...prev, searchMessage]);
      
      // Update suggestions
      setSuggestions(response.data.suggestions || []);
      
      // Show results if available
      if (response.data.results) {
        setSearchResults(response.data.results);
        setShowResults(true);
      }
      
    } catch (error) {
      console.error('Error executing search:', error);
      toast.error('Failed to execute search');
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const clearChat = () => {
    setMessages([]);
    setSessionId(null);
    setSuggestions([]);
    setSearchResults(null);
    setShowResults(false);
    initializeChat();
  };

  const formatMessage = (content) => {
    // Convert markdown-style formatting to HTML
    return content
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/•/g, '&bull;')
      .replace(/\n/g, '<br>');
  };

  const getScoreColor = (score) => {
    if (score >= 80) return '#38a169';
    if (score >= 60) return '#d69e2e';
    return '#e53e3e';
  };

  return (
    <div className="container" style={{ maxWidth: '1200px', margin: '0 auto' }}>
      <div style={{ marginBottom: '24px' }}>
        <h1 style={{ fontSize: '32px', fontWeight: '700', marginBottom: '8px' }}>
          🤖 AI Resume Matching Assistant v2.0
        </h1>
        <p style={{ color: '#718096' }}>
          Tell me about your hiring needs and I'll help you find the perfect candidates
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 300px', gap: '24px' }}>
        
        {/* Main Chat Area */}
        <div className="card" style={{ height: '600px', display: 'flex', flexDirection: 'column' }}>
          
          {/* Chat Header */}
          <div style={{ 
            padding: '16px', 
            borderBottom: '1px solid #e2e8f0',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Bot size={20} style={{ color: '#4299e1' }} />
              <span style={{ fontWeight: '600' }}>AI Assistant</span>
            </div>
            <button
              onClick={clearChat}
              className="btn btn-secondary"
              style={{ padding: '6px 12px', fontSize: '12px' }}
            >
              <RefreshCw size={14} />
              New Chat
            </button>
          </div>

          {/* Messages Area */}
          <div style={{ 
            flex: 1, 
            overflowY: 'auto', 
            padding: '16px',
            display: 'flex',
            flexDirection: 'column',
            gap: '16px'
          }}>
            {messages.map((message) => (
              <div
                key={message.id}
                style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '12px',
                  flexDirection: message.role === 'user' ? 'row-reverse' : 'row'
                }}
              >
                {/* Avatar */}
                <div style={{
                  width: '32px',
                  height: '32px',
                  borderRadius: '50%',
                  backgroundColor: message.role === 'user' ? '#4299e1' : '#38a169',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: 'white',
                  fontSize: '14px',
                  flexShrink: 0
                }}>
                  {message.role === 'user' ? <User size={16} /> : <Bot size={16} />}
                </div>

                {/* Message Content */}
                <div style={{
                  backgroundColor: message.role === 'user' ? '#4299e1' : '#f7fafc',
                  color: message.role === 'user' ? 'white' : '#2d3748',
                  padding: '12px 16px',
                  borderRadius: '12px',
                  maxWidth: '80%',
                  wordWrap: 'break-word'
                }}>
                  <div 
                    dangerouslySetInnerHTML={{ 
                      __html: formatMessage(message.content) 
                    }}
                  />
                  
                  {/* Show search button for ready_to_search action */}
                  {message.action === 'ready_to_search' && message.role === 'assistant' && (
                    <button
                      onClick={executeSearch}
                      className="btn btn-primary"
                      style={{ 
                        marginTop: '12px',
                        padding: '8px 16px',
                        fontSize: '14px',
                        backgroundColor: '#4299e1',
                        color: 'white',
                        border: 'none'
                      }}
                      disabled={isLoading}
                      title={isLoading ? 'Please wait for current operation to complete' : 'Search for candidates'}
                    >
                      <Search size={14} />
                      {isLoading ? 'Searching...' : 'Search for Candidates'}
                    </button>
                  )}
                </div>
              </div>
            ))}
            
            {/* Loading indicator */}
            {isLoading && (
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '12px'
              }}>
                <div style={{
                  width: '32px',
                  height: '32px',
                  borderRadius: '50%',
                  backgroundColor: '#38a169',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: 'white'
                }}>
                  <Bot size={16} />
                </div>
                <div style={{
                  backgroundColor: '#f7fafc',
                  padding: '12px 16px',
                  borderRadius: '12px',
                  color: '#718096'
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <div className="spinner" style={{ width: '16px', height: '16px' }} />
                    Thinking...
                  </div>
                </div>
              </div>
            )}
            
            <div ref={messagesEndRef} />
          </div>

          {/* Input Area */}
          <div style={{ 
            padding: '16px', 
            borderTop: '1px solid #e2e8f0',
            display: 'flex',
            gap: '8px'
          }}>
            <textarea
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Ask me about your hiring needs..."
              style={{
                flex: 1,
                padding: '12px',
                border: '1px solid #e2e8f0',
                borderRadius: '8px',
                resize: 'none',
                minHeight: '44px',
                maxHeight: '120px',
                fontFamily: 'inherit'
              }}
              rows={1}
            />
            <button
              onClick={() => sendMessage()}
              disabled={!inputMessage.trim() || isLoading}
              className="btn btn-primary"
              title={isLoading ? 'Please wait for response' : 'Send message'}
              style={{
                padding: '12px 16px',
                borderRadius: '8px',
                backgroundColor: '#4299e1',
                color: 'white',
                border: 'none',
                cursor: !inputMessage.trim() || isLoading ? 'not-allowed' : 'pointer',
                opacity: !inputMessage.trim() || isLoading ? 0.6 : 1
              }}
            >
              <Send size={16} />
            </button>
          </div>
        </div>

        {/* Sidebar */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          
          {/* Quick Suggestions */}
          {suggestions.length > 0 && (
            <div className="card">
              <h3 style={{ fontSize: '16px', fontWeight: '600', marginBottom: '12px' }}>
                💡 Quick Suggestions
              </h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {suggestions.map((suggestion, index) => (
                  <button
                    key={index}
                    onClick={() => sendMessage(suggestion)}
                    className="btn btn-secondary"
                    style={{
                      padding: '8px 12px',
                      fontSize: '12px',
                      textAlign: 'left',
                      justifyContent: 'flex-start',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px'
                    }}
                  >
                    <ChevronRight size={14} />
                    {suggestion}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Search Results Summary */}
          {searchResults && (
            <div className="card">
              <h3 style={{ fontSize: '16px', fontWeight: '600', marginBottom: '12px' }}>
                🎯 Search Results
              </h3>
              <div style={{ fontSize: '14px', color: '#4a5568' }}>
                <p><strong>Total CVs:</strong> {searchResults.total_cvs_processed}</p>
                <p><strong>Matches:</strong> {searchResults.matches?.length || 0}</p>
                <p><strong>Processing Time:</strong> {searchResults.processing_time}</p>
              </div>
              
              {searchResults.matches && searchResults.matches.length > 0 && (
                <div style={{ marginTop: '12px' }}>
                  <h4 style={{ fontSize: '14px', fontWeight: '600', marginBottom: '8px' }}>
                    Top Candidates:
                  </h4>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    {searchResults.matches.slice(0, 3).map((match, index) => (
                      <div 
                        key={index}
                        style={{
                          padding: '8px',
                          backgroundColor: '#f7fafc',
                          borderRadius: '6px',
                          fontSize: '12px'
                        }}
                      >
                        <div style={{ fontWeight: '500' }}>
                          {match.candidate_name || match.cv_filename}
                        </div>
                        <div style={{ 
                          color: getScoreColor(match.relevance_score),
                          fontWeight: '600'
                        }}>
                          {Math.round(match.relevance_score)}% match
                        </div>
                      </div>
                    ))}
                  </div>
                  
                  <button
                    onClick={() => setShowResults(true)}
                    className="btn btn-primary"
                    style={{
                      marginTop: '12px',
                      width: '100%',
                      padding: '8px 12px',
                      fontSize: '12px'
                    }}
                  >
                    View All Results
                  </button>
                </div>
              )}
            </div>
          )}

          {/* Conversation History */}
          {conversationHistory.length > 0 && (
            <div className="card">
              <h3 style={{ fontSize: '16px', fontWeight: '600', marginBottom: '12px' }}>
                📋 Recent Chats
              </h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                {conversationHistory.slice(0, 5).map((conv) => (
                  <div 
                    key={conv.id}
                    style={{
                      padding: '8px',
                      backgroundColor: '#f7fafc',
                      borderRadius: '6px',
                      fontSize: '12px',
                      cursor: 'pointer'
                    }}
                    onClick={() => {
                      // Load conversation logic here
                      console.log('Load conversation:', conv.session_id);
                    }}
                  >
                    <div style={{ fontWeight: '500' }}>
                      {conv.message_count} messages
                    </div>
                    <div style={{ color: '#718096' }}>
                      {new Date(conv.updated_at).toLocaleDateString()}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Results Modal */}
      {showResults && searchResults && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000,
          padding: '20px'
        }}>
          <div style={{
            backgroundColor: 'white',
            borderRadius: '8px',
            padding: '24px',
            maxWidth: '900px',
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
                Resume Matching Results
              </h2>
              <button
                onClick={() => setShowResults(false)}
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
              <div style={{ display: 'flex', gap: '24px', fontSize: '14px' }}>
                <span><strong>Total CVs:</strong> {searchResults.total_cvs_processed}</span>
                <span><strong>Matches:</strong> {searchResults.matches?.length || 0}</span>
                <span><strong>Processing Time:</strong> {searchResults.processing_time}</span>
              </div>
            </div>

            <div style={{ display: 'grid', gap: '16px' }}>
              {searchResults.matches?.map((match, index) => (
                <div 
                  key={index}
                  style={{
                    border: '1px solid #e2e8f0',
                    borderRadius: '8px',
                    padding: '16px'
                  }}
                >
                  <div style={{ 
                    display: 'flex', 
                    justifyContent: 'space-between', 
                    alignItems: 'center',
                    marginBottom: '12px'
                  }}>
                    <div>
                      <h4 style={{ fontSize: '16px', fontWeight: '600', marginBottom: '4px' }}>
                        {match.candidate_name || match.cv_filename}
                      </h4>
                      <div style={{ fontSize: '14px', color: '#718096' }}>
                        {match.cv_filename}
                      </div>
                    </div>
                    <div style={{ textAlign: 'right' }}>
                      <div style={{ 
                        fontSize: '18px',
                        fontWeight: '600',
                        color: getScoreColor(match.relevance_score)
                      }}>
                        {Math.round(match.relevance_score)}%
                      </div>
                      <div style={{ fontSize: '12px', color: '#718096' }}>
                        Match Score
                      </div>
                    </div>
                  </div>
                  
                  {match.candidate_summary && (
                    <div style={{ marginBottom: '12px' }}>
                      <h5 style={{ fontSize: '14px', fontWeight: '600', marginBottom: '4px' }}>
                        Summary:
                      </h5>
                      <p style={{ fontSize: '13px', color: '#4a5568', lineHeight: '1.4' }}>
                        {match.candidate_summary}
                      </p>
                    </div>
                  )}
                  
                  {match.key_skills && (
                    <div style={{ marginBottom: '12px' }}>
                      <h5 style={{ fontSize: '14px', fontWeight: '600', marginBottom: '4px' }}>
                        Key Skills:
                      </h5>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                        {JSON.parse(match.key_skills || '[]').map((skill, skillIndex) => (
                          <span 
                            key={skillIndex}
                            style={{
                              backgroundColor: '#edf2f7',
                              padding: '2px 8px',
                              borderRadius: '12px',
                              fontSize: '11px',
                              color: '#4a5568'
                            }}
                          >
                            {skill}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  {match.match_analysis && (
                    <div style={{ marginBottom: '12px' }}>
                      <h5 style={{ fontSize: '14px', fontWeight: '600', marginBottom: '4px' }}>
                        Match Analysis:
                      </h5>
                      <div style={{ 
                        fontSize: '13px', 
                        color: '#4a5568',
                        backgroundColor: '#f7fafc',
                        padding: '12px',
                        borderRadius: '6px',
                        whiteSpace: 'pre-wrap'
                      }}>
                        {match.match_analysis}
                      </div>
                    </div>
                  )}
                  
                  {match.download_url && (
                    <div>
                      <a
                        href={match.download_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="btn btn-primary"
                        style={{
                          padding: '8px 16px',
                          fontSize: '14px',
                          textDecoration: 'none',
                          display: 'inline-block'
                        }}
                      >
                        Download CV
                      </a>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ChatAgent;