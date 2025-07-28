import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import API_CONFIG from '../config/api';
import { toast } from 'react-toastify';
import { 
  Send, 
  Bot, 
  User, 
  Search, 
  Plus,
  Menu,
  Download,
  Trash2,
  MessageCircle,
  ChevronRight
} from 'lucide-react';

const ChatHistoryItem = ({ chat, onLoadChat, onDeleteChat }) => {
  const [isHovered, setIsHovered] = useState(false);
  
  return (
    <div
      style={{
        padding: '12px',
        margin: '4px 0',
        borderRadius: '6px',
        backgroundColor: chat.isActive ? '#2d2d2d' : 'transparent',
        cursor: 'pointer',
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
        fontSize: '14px',
        position: 'relative'
      }}
      onClick={() => onLoadChat(chat.id)}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <MessageCircle size={16} style={{ opacity: 0.7 }} />
      <div style={{ flex: 1, overflow: 'hidden' }}>
        <div style={{ 
          whiteSpace: 'nowrap', 
          overflow: 'hidden', 
          textOverflow: 'ellipsis' 
        }}>
          {chat.title}
        </div>
        <div style={{ 
          fontSize: '12px', 
          color: '#999', 
          marginTop: '2px' 
        }}>
          {new Date(chat.timestamp).toLocaleDateString()}
        </div>
      </div>
      {isHovered && (
        <button
          onClick={(e) => {
            e.stopPropagation();
            onDeleteChat(chat.id);
          }}
          style={{
            background: 'none',
            border: 'none',
            color: '#999',
            cursor: 'pointer',
            padding: '4px'
          }}
        >
          <Trash2 size={14} />
        </button>
      )}
    </div>
  );
};

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
  const [currentChatTitle, setCurrentChatTitle] = useState('New Chat');
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [chatHistory, setChatHistory] = useState([]);
  const [quotaExceeded, setQuotaExceeded] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    axios.defaults.baseURL = API_CONFIG.baseURL;
    axios.defaults.timeout = API_CONFIG.timeout;
    
    initializeWebSocket();
    initializeChat();
    loadConversationHistory();
    
    return () => {
      if (wsConnection) {
        wsConnection.close();
      }
    };
  }, []);

  useEffect(() => {
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
      
      const newSessionId = response.data.session_id;
      setSessionId(newSessionId);
      setMessages([{
        id: Date.now(),
        role: 'assistant',
        content: response.data.message,
        timestamp: response.data.timestamp,
        action: response.data.action
      }]);
      setSuggestions(response.data.suggestions || []);
      
      const newChat = {
        id: newSessionId,
        title: 'New Chat',
        timestamp: new Date().toISOString(),
        messageCount: 1,
        isActive: true
      };
      
      setChatHistory(prev => [newChat, ...prev.map(chat => ({ ...chat, isActive: false }))]);
      
    } catch (error) {
      console.error('Error initializing chat:', error);
      toast.error('Failed to initialize chat agent');
    }
  };

  const loadConversationHistory = async () => {
    try {
      const response = await axios.get('/chat/conversations');
      setConversationHistory(response.data);
      
      const transformedHistory = await Promise.all(
        response.data.map(async (conv) => {
          try {
            const messagesResponse = await axios.get(`/chat/conversation/${conv.session_id}/messages`);
            const messages = messagesResponse.data;
            const firstUserMessage = messages.find(msg => msg.role === 'user');
            
            const title = firstUserMessage 
              ? (firstUserMessage.content.length > 50 
                 ? firstUserMessage.content.substring(0, 50) + '...' 
                 : firstUserMessage.content)
              : 'New Chat';
            
            return {
              id: conv.session_id,
              title: title,
              timestamp: conv.updated_at,
              messageCount: conv.message_count,
              isActive: conv.session_id === sessionId
            };
          } catch (error) {
            console.error(`Error loading messages for conversation ${conv.session_id}:`, error);
            return {
              id: conv.session_id,
              title: 'New Chat',
              timestamp: conv.updated_at,
              messageCount: conv.message_count,
              isActive: conv.session_id === sessionId
            };
          }
        })
      );
      
      setChatHistory(transformedHistory);
    } catch (error) {
      console.error('Error loading conversation history:', error);
    }
  };

  const sendMessage = async (messageText = null) => {
    const message = messageText || inputMessage.trim();
    if (!message) return;

    setIsLoading(true);
    setInputMessage('');

    const userMessage = {
      id: Date.now(),
      role: 'user',
      content: message,
      timestamp: new Date().toISOString()
    };
    setMessages(prev => [...prev, userMessage]);

    if (messages.length === 1 && currentChatTitle === 'New Chat') {
      const title = message.length > 50 ? message.substring(0, 50) + '...' : message;
      setCurrentChatTitle(title);
      
      setChatHistory(prev => prev.map(chat => 
        chat.id === sessionId 
          ? { ...chat, title: title }
          : chat
      ));
    }

    try {
      const response = await axios.post('/chat', {
        message: message,
        session_id: sessionId
      });

      const aiMessage = {
        id: Date.now() + 1,
        role: 'assistant',
        content: response.data.message,
        timestamp: response.data.timestamp,
        action: response.data.action
      };
      setMessages(prev => [...prev, aiMessage]);
      
      setSuggestions(response.data.suggestions || []);
      
      // Check if the response indicates quota issues
      if (response.data.message?.includes('quota') || response.data.message?.includes('OpenAI API quota') || 
          response.data.suggestions?.some(s => s.includes('OpenAI billing'))) {
        setQuotaExceeded(true);
      }
      
      setChatHistory(prev => prev.map(chat => 
        chat.id === sessionId 
          ? { 
              ...chat, 
              messageCount: messages.length + 2,
              timestamp: new Date().toISOString()
            }
          : chat
      ));
      
      if (response.data.action === 'show_results' && response.data.results) {
        setSearchResults(response.data.results);
        setShowResults(true);
      }
      
    } catch (error) {
      console.error('Error sending message:', error);
      
      let errorContent = 'I apologize, but I encountered an error. Please try again.';
      let toastMessage = 'Failed to send message';
      
      // Check for specific error types
      if (error.response?.status === 429 || error.message?.includes('quota') || error.message?.includes('rate limit')) {
        setQuotaExceeded(true);
        errorContent = '⚠️ **OpenAI API Quota Exceeded**\n\nThe enhanced AI features are temporarily unavailable due to API quota limits. The system will use basic matching instead.\n\n**To restore full features:**\n• Visit https://platform.openai.com/account/billing\n• Add credits to your OpenAI account\n• Enhanced matching will resume automatically';
        toastMessage = 'OpenAI quota exceeded - using basic features';
        toast.warning(toastMessage);
      } else if (error.response?.status >= 500) {
        errorContent = '🔧 **Server Error**\n\nThere seems to be a server issue. Please try again in a moment.';
        toastMessage = 'Server error occurred';
        toast.error(toastMessage);
      } else {
        toast.error(toastMessage);
      }
      
      const errorMessage = {
        id: Date.now() + 1,
        role: 'assistant',
        content: errorContent,
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
      
      const searchMessage = {
        id: Date.now(),
        role: 'assistant',
        content: response.data.message,
        timestamp: response.data.timestamp,
        action: response.data.action
      };
      setMessages(prev => [...prev, searchMessage]);
      
      setSuggestions(response.data.suggestions || []);
      
      if (response.data.results) {
        setSearchResults(response.data.results);
        setShowResults(true);
      }
      
    } catch (error) {
      console.error('Error executing search:', error);
      
      let toastMessage = 'Failed to execute search';
      
      // Check for specific error types
      if (error.response?.status === 429 || error.message?.includes('quota') || error.message?.includes('rate limit')) {
        setQuotaExceeded(true);
        toastMessage = 'Search using basic matching - OpenAI quota exceeded';
        toast.warning(toastMessage);
        
        // Add a message about quota issue
        const quotaMessage = {
          id: Date.now(),
          role: 'assistant',
          content: '⚠️ **Search completed with basic matching**\n\nOpenAI quota limits prevent enhanced AI matching. Results may be less accurate.\n\n**To restore enhanced matching:**\nAdd credits at https://platform.openai.com/account/billing',
          timestamp: new Date().toISOString(),
          action: 'quota_warning'
        };
        setMessages(prev => [...prev, quotaMessage]);
      } else {
        toast.error(toastMessage);
      }
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
    setCurrentChatTitle('New Chat');
    initializeChat();
  };

  const loadChat = async (chatId) => {
    try {
      const response = await axios.get(`/chat/conversation/${chatId}/messages`);
      const messagesData = response.data;
      
      const transformedMessages = messagesData.map(msg => ({
        id: msg.id,
        role: msg.role,
        content: msg.content,
        timestamp: msg.created_at,
        action: msg.message_metadata?.action
      }));
      
      const firstUserMessage = transformedMessages.find(msg => msg.role === 'user');
      const title = firstUserMessage 
        ? (firstUserMessage.content.length > 50 
           ? firstUserMessage.content.substring(0, 50) + '...' 
           : firstUserMessage.content)
        : 'Chat';
      
      setSessionId(chatId);
      setCurrentChatTitle(title);
      setMessages(transformedMessages);
      setSuggestions([]);
      setSearchResults(null);
      setShowResults(false);
      
      setChatHistory(prev => prev.map(chat => ({
        ...chat,
        isActive: chat.id === chatId
      })));
      
      toast.success('Chat loaded successfully');
    } catch (error) {
      console.error('Error loading chat:', error);
      toast.error('Failed to load chat');
    }
  };

  const deleteChat = async (chatId) => {
    try {
      await axios.delete(`/chat/conversation/${chatId}`);
      setChatHistory(prev => prev.filter(chat => chat.id !== chatId));
      if (sessionId === chatId) {
        clearChat();
      }
      toast.success('Chat deleted successfully');
    } catch (error) {
      console.error('Error deleting chat:', error);
      toast.error('Failed to delete chat');
    }
  };

  const downloadCV = async (downloadUrl, filename) => {
    try {
      const response = await fetch(downloadUrl);
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.style.display = 'none';
      a.href = url;
      a.download = filename || 'resume.pdf';
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      toast.success('CV downloaded successfully');
    } catch (error) {
      console.error('Error downloading CV:', error);
      toast.error('Failed to download CV');
    }
  };

  const formatMessage = (content) => {
    return content
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/•/g, '&bull;')
      .replace(/\n/g, '<br>');
  };

  const getScoreColor = (score) => {
    if (score >= 80) return '#16a34a';
    if (score >= 60) return '#ca8a04';
    return '#dc2626';
  };

  return (
    <div style={{ 
      display: 'flex', 
      height: '100vh', 
      backgroundColor: '#ffffff',
      fontFamily: 'system-ui, -apple-system, sans-serif'
    }}>
      
      {/* Left Sidebar - Chat History */}
      <div style={{
        width: isSidebarOpen ? '260px' : '0px',
        backgroundColor: '#171717',
        color: 'white',
        transition: 'width 0.3s ease',
        overflow: 'hidden',
        display: 'flex',
        flexDirection: 'column'
      }}>
        <div style={{
          padding: '12px',
          borderBottom: '1px solid #404040'
        }}>
          <button
            onClick={clearChat}
            style={{
              width: '100%',
              padding: '12px',
              backgroundColor: 'transparent',
              border: '1px solid #404040',
              borderRadius: '6px',
              color: 'white',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              cursor: 'pointer',
              fontSize: '14px'
            }}
          >
            <Plus size={16} />
            New chat
          </button>
        </div>

        <div style={{
          flex: 1,
          overflowY: 'auto',
          padding: '8px'
        }}>
          {chatHistory.map((chat) => (
            <ChatHistoryItem 
              key={chat.id} 
              chat={chat} 
              onLoadChat={loadChat} 
              onDeleteChat={deleteChat} 
            />
          ))}
        </div>
      </div>

      {/* Main Chat Area */}
      <div style={{ 
        flex: 1, 
        display: 'flex', 
        flexDirection: 'column',
        backgroundColor: '#ffffff'
      }}>
        
        {/* Top Header */}
        <div style={{
          height: '60px',
          borderBottom: '1px solid #e5e5e5',
          display: 'flex',
          alignItems: 'center',
          paddingLeft: '16px',
          paddingRight: '16px',
          gap: '12px'
        }}>
          <button
            onClick={() => setIsSidebarOpen(!isSidebarOpen)}
            style={{
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              padding: '8px',
              borderRadius: '6px',
              color: '#666'
            }}
          >
            <Menu size={20} />
          </button>
          <h1 style={{
            fontSize: '18px',
            fontWeight: '600',
            color: '#333',
            margin: 0
          }}>
            {currentChatTitle}
          </h1>
          
          {/* Quota Status Indicator */}
          {quotaExceeded && (
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '6px 12px',
              backgroundColor: '#fef3c7',
              border: '1px solid #f59e0b',
              borderRadius: '6px',
              fontSize: '12px',
              color: '#92400e'
            }}>
              <span>⚠️</span>
              <span>Basic Mode - OpenAI Quota Exceeded</span>
              <a 
                href="https://platform.openai.com/account/billing" 
                target="_blank" 
                rel="noopener noreferrer"
                style={{
                  color: '#1d4ed8',
                  textDecoration: 'underline',
                  fontSize: '11px'
                }}
              >
                Add Credits
              </a>
            </div>
          )}
        </div>

        {/* Messages Container */}
        <div style={{
          flex: 1,
          display: 'flex'
        }}>
          
          {/* Messages Area */}
          <div style={{
            flex: 1,
            display: 'flex',
            flexDirection: 'column'
          }}>

            {/* Messages Scroll Area */}
            <div style={{ 
              flex: 1, 
              overflowY: 'auto', 
              padding: '24px',
              display: 'flex',
              flexDirection: 'column',
              gap: '24px',
              maxWidth: '800px',
              margin: '0 auto',
              width: '100%'
            }}>
              {messages.map((message) => (
                <div
                  key={message.id}
                  style={{
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: '16px',
                    maxWidth: '100%'
                  }}
                >
                  <div style={{
                    width: '30px',
                    height: '30px',
                    borderRadius: '2px',
                    backgroundColor: message.role === 'user' ? '#19c37d' : '#ab68ff',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: 'white',
                    fontSize: '14px',
                    flexShrink: 0,
                    fontWeight: '600'
                  }}>
                    {message.role === 'user' ? 'U' : 'AI'}
                  </div>

                  <div style={{
                    flex: 1,
                    color: '#374151',
                    fontSize: '16px',
                    lineHeight: '1.6',
                    wordWrap: 'break-word'
                  }}>
                    <div 
                      dangerouslySetInnerHTML={{ 
                        __html: formatMessage(message.content) 
                      }}
                    />
                    
                    {message.action === 'ready_to_search' && message.role === 'assistant' && (
                      <button
                        onClick={executeSearch}
                        style={{ 
                          marginTop: '12px',
                          padding: '10px 20px',
                          fontSize: '14px',
                          backgroundColor: '#10a37f',
                          color: 'white',
                          border: 'none',
                          borderRadius: '6px',
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '8px'
                        }}
                        disabled={isLoading}
                        title={isLoading ? 'Please wait for current operation to complete' : 'Search for candidates'}
                      >
                        <Search size={16} />
                        {isLoading ? 'Searching...' : 'Search for Candidates'}
                      </button>
                    )}
                  </div>
                </div>
              ))}
              
              {isLoading && (
                <div style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '16px'
                }}>
                  <div style={{
                    width: '30px',
                    height: '30px',
                    borderRadius: '2px',
                    backgroundColor: '#ab68ff',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: 'white',
                    fontSize: '14px',
                    fontWeight: '600'
                  }}>
                    AI
                  </div>
                  <div style={{
                    color: '#374151',
                    fontSize: '16px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px'
                  }}>
                    <div className="spinner" style={{ width: '16px', height: '16px' }} />
                    Thinking...
                  </div>
                </div>
              )}
              
              <div ref={messagesEndRef} />
            </div>

            {/* Input Area */}
            <div style={{ 
              padding: '24px',
              borderTop: '1px solid #e5e5e5'
            }}>
              <div style={{
                position: 'relative',
                maxWidth: '800px',
                margin: '0 auto',
                width: '100%'
              }}>
                <textarea
                  value={inputMessage}
                  onChange={(e) => setInputMessage(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="Message ChatGPT..."
                  style={{
                    width: '100%',
                    padding: '12px 50px 12px 16px',
                    border: '1px solid #d1d5db',
                    borderRadius: '12px',
                    resize: 'none',
                    minHeight: '52px',
                    maxHeight: '200px',
                    fontSize: '16px',
                    outline: 'none',
                    boxSizing: 'border-box'
                  }}
                  rows={1}
                />
                <button
                  onClick={() => sendMessage()}
                  disabled={!inputMessage.trim() || isLoading}
                  style={{
                    position: 'absolute',
                    right: '8px',
                    top: '50%',
                    transform: 'translateY(-50%)',
                    width: '36px',
                    height: '36px',
                    borderRadius: '6px',
                    backgroundColor: inputMessage.trim() && !isLoading ? '#10a37f' : '#d1d5db',
                    color: 'white',
                    border: 'none',
                    cursor: inputMessage.trim() && !isLoading ? 'pointer' : 'not-allowed',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center'
                  }}
                >
                  <Send size={16} />
                </button>
              </div>
            </div>
          </div>

          {/* Right Sidebar */}
          <div style={{ 
            width: '280px', 
            backgroundColor: '#f9fafb',
            borderLeft: '1px solid #e5e5e5',
            display: 'flex',
            flexDirection: 'column',
            padding: '16px'
          }}>
            
            {/* Quick Suggestions */}
            {suggestions.length > 0 && (
              <div style={{
                backgroundColor: 'white',
                borderRadius: '8px',
                padding: '16px',
                marginBottom: '16px',
                boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)'
              }}>
                <h3 style={{ 
                  fontSize: '14px', 
                  fontWeight: '600', 
                  marginBottom: '12px',
                  color: '#374151'
                }}>
                  💡 Quick Suggestions
                </h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  {suggestions.map((suggestion, index) => (
                    <button
                      key={index}
                      onClick={() => sendMessage(suggestion)}
                      style={{
                        padding: '8px 12px',
                        fontSize: '13px',
                        textAlign: 'left',
                        backgroundColor: '#f3f4f6',
                        border: '1px solid #e5e7eb',
                        borderRadius: '6px',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '6px',
                        color: '#374151'
                      }}
                      onMouseOver={(e) => {
                        e.currentTarget.style.backgroundColor = '#e5e7eb';
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.backgroundColor = '#f3f4f6';
                      }}
                    >
                      <ChevronRight size={12} />
                      {suggestion}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Search Results Summary */}
            {searchResults && (
              <div style={{
                backgroundColor: 'white',
                borderRadius: '8px',
                padding: '16px',
                marginBottom: '16px',
                boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)'
              }}>
                <h3 style={{ 
                  fontSize: '14px', 
                  fontWeight: '600', 
                  marginBottom: '12px',
                  color: '#374151'
                }}>
                  🎯 Search Results
                </h3>
                <div style={{ fontSize: '13px', color: '#6b7280' }}>
                  <p style={{ margin: '4px 0' }}><strong>Total CVs:</strong> {searchResults.total_cvs_processed}</p>
                  <p style={{ margin: '4px 0' }}><strong>Matches:</strong> {searchResults.matches?.length || 0}</p>
                  <p style={{ margin: '4px 0' }}><strong>Processing Time:</strong> {searchResults.processing_time}</p>
                </div>
                
                {searchResults.matches && searchResults.matches.length > 0 && (
                  <div style={{ marginTop: '12px' }}>
                    <h4 style={{ fontSize: '13px', fontWeight: '600', marginBottom: '8px', color: '#374151' }}>
                      Top Candidates:
                    </h4>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                      {searchResults.matches.slice(0, 3).map((match, index) => (
                        <div 
                          key={index}
                          style={{
                            padding: '8px',
                            backgroundColor: '#f9fafb',
                            borderRadius: '6px',
                            fontSize: '12px',
                            border: '1px solid #e5e7eb'
                          }}
                        >
                          <div style={{ fontWeight: '500', color: '#374151' }}>
                            {match.candidate_name || match.cv_filename}
                          </div>
                          <div style={{ 
                            color: getScoreColor(match.relevance_score),
                            fontWeight: '600',
                            marginTop: '2px'
                          }}>
                            {Math.round(match.relevance_score)}% match
                          </div>
                        </div>
                      ))}
                    </div>
                    
                    <button
                      onClick={() => setShowResults(true)}
                      style={{
                        marginTop: '12px',
                        width: '100%',
                        padding: '8px 12px',
                        fontSize: '13px',
                        backgroundColor: '#10a37f',
                        color: 'white',
                        border: 'none',
                        borderRadius: '6px',
                        cursor: 'pointer'
                      }}
                    >
                      View All Results
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
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
                      <button
                        onClick={() => downloadCV(match.download_url, match.cv_filename)}
                        style={{
                          padding: '10px 16px',
                          fontSize: '14px',
                          backgroundColor: '#10a37f',
                          color: 'white',
                          border: 'none',
                          borderRadius: '6px',
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '6px'
                        }}
                      >
                        <Download size={14} />
                        Download CV
                      </button>
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