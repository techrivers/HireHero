import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import API_CONFIG from '../config/api';
import { toast } from 'react-toastify';
import { 
  MessageCircle, 
  Send, 
  X, 
  Minimize2,
  Bot,
  User,
  RefreshCw
} from 'lucide-react';
import './FloatingChatWidget.css';

const FloatingChatWidget = ({ context = 'candidates', contextData = {} }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [isMinimized, setIsMinimized] = useState(false);
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    axios.defaults.baseURL = API_CONFIG.baseURL;
    if (isOpen && !sessionId) {
      initializeChat();
    }
  }, [isOpen]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const initializeChat = async () => {
    try {
      const contextMessage = getContextMessage();
      const response = await axios.post('/chat', {
        message: contextMessage,
        session_id: sessionId,
        context: {
          page: context,
          data: {
            ...contextData,
            candidates_visible: contextData.candidatesData?.slice(0, 10) || []
          }
        }
      });
      
      const newSessionId = response.data.session_id;
      setSessionId(newSessionId);
      setMessages([{
        id: Date.now(),
        role: 'assistant',
        content: response.data.message,
        timestamp: response.data.timestamp
      }]);
      
    } catch (error) {
      console.error('Error initializing chat:', error);
      setMessages([{
        id: Date.now(),
        role: 'assistant',
        content: 'Hi! I\'m here to help you with your candidates. How can I assist you today?',
        timestamp: new Date().toISOString()
      }]);
    }
  };

  const getContextMessage = () => {
    switch (context) {
      case 'candidates':
        const totalCandidates = contextData.totalCandidates || 0;
        const filteredCandidates = contextData.filteredCandidates || 0;
        const candidatesData = contextData.candidatesData || [];
        
        // Prepare detailed candidate information for AI context
        const candidatesSummary = candidatesData.slice(0, 10).map(candidate => ({
          name: candidate.name,
          experience_years: candidate.experience_years,
          skills: candidate.skills_json?.skills || candidate.skills_json || [],
          professional_summary: candidate.professional_summary,
          availability_status: candidate.availability_status,
          avg_match_score: candidate.avg_match_score
        }));
        
        return `I'm viewing the candidates page with ${totalCandidates} total candidates (${filteredCandidates} currently shown). Here are the current candidates I can see:

${candidatesSummary.map((c, i) => `
${i+1}. ${c.name}
   - Experience: ${c.experience_years || 0} years
   - Skills: ${Array.isArray(c.skills) ? c.skills.slice(0, 5).join(', ') : 'N/A'}
   - Availability: ${c.availability_status || 'Unknown'}
   - Match Score: ${c.avg_match_score ? Math.round(c.avg_match_score) + '%' : 'N/A'}
   - Summary: ${c.professional_summary ? c.professional_summary.substring(0, 100) + '...' : 'N/A'}
`).join('')}

Please help me analyze these candidates, answer questions about their skills, experience, or provide insights about the talent pool. You can also help with searching, filtering, or candidate management tasks.`;
      case 'jobs':
        return `I'm on the jobs page. Help me with job management, posting, or matching jobs with candidates.`;
      case 'career-pages':
        return `I'm viewing career pages. Help me with scraping career pages, managing configurations, or troubleshooting scraping issues.`;
      default:
        return 'Hello! How can I help you today?';
    }
  };

  const getSuggestions = () => {
    switch (context) {
      case 'candidates':
        return [
          "Analyze the skill distribution of these candidates",
          "Who are the most experienced candidates shown?",
          "Which candidates are available for immediate hire?",
          "Compare the candidates by their technical skills",
          "Summarize the strengths of the top candidates",
          "What roles would these candidates be best suited for?",
          "Find candidates with specific technology combinations"
        ];
      case 'jobs':
        return [
          "Help me create a new job posting",
          "Find matching candidates for this job",
          "What are the trending job requirements?",
          "Help me optimize my job descriptions"
        ];
      case 'career-pages':
        return [
          "Help me troubleshoot scraping issues",
          "Add a new career page to scrape",
          "Why is my scraping not finding jobs?",
          "Configure custom scraping rules"
        ];
      default:
        return [];
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

    try {
      const response = await axios.post('/chat', {
        message: message,
        session_id: sessionId,
        context: {
          page: context,
          data: {
            ...contextData,
            candidates_visible: contextData.candidatesData?.slice(0, 10) || []
          }
        }
      });

      const aiMessage = {
        id: Date.now() + 1,
        role: 'assistant',
        content: response.data.message,
        timestamp: response.data.timestamp
      };
      setMessages(prev => [...prev, aiMessage]);
      
    } catch (error) {
      console.error('Error sending message:', error);
      const errorMessage = {
        id: Date.now() + 1,
        role: 'assistant',
        content: 'I apologize, but I encountered an error. Please try again.',
        timestamp: new Date().toISOString()
      };
      setMessages(prev => [...prev, errorMessage]);
      toast.error('Failed to send message');
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
    initializeChat();
  };

  if (!isOpen) {
    return (
      <div className="floating-chat-button" onClick={() => setIsOpen(true)}>
        <MessageCircle size={24} />
        <div className="chat-tooltip">Ask AI Assistant</div>
      </div>
    );
  }

  return (
    <div className={`floating-chat-widget ${isMinimized ? 'minimized' : ''}`}>
      <div className="chat-header">
        <div className="chat-title">
          <Bot size={18} />
          <span>AI Assistant</span>
          <span className="context-tag">{context}</span>
        </div>
        <div className="chat-controls">
          <button
            onClick={clearChat}
            className="chat-control-btn"
            title="New conversation"
          >
            <RefreshCw size={16} />
          </button>
          <button
            onClick={() => setIsMinimized(!isMinimized)}
            className="chat-control-btn"
            title={isMinimized ? "Expand" : "Minimize"}
          >
            <Minimize2 size={16} />
          </button>
          <button
            onClick={() => setIsOpen(false)}
            className="chat-control-btn"
            title="Close chat"
          >
            <X size={16} />
          </button>
        </div>
      </div>

      {!isMinimized && (
        <>
          <div className="chat-messages">
            {messages.map((message) => (
              <div
                key={message.id}
                className={`chat-message ${message.role}`}
              >
                <div className="message-avatar">
                  {message.role === 'user' ? (
                    <User size={16} />
                  ) : (
                    <Bot size={16} />
                  )}
                </div>
                <div className="message-content">
                  {message.content}
                </div>
              </div>
            ))}
            
            {isLoading && (
              <div className="chat-message assistant loading">
                <div className="message-avatar">
                  <Bot size={16} />
                </div>
                <div className="message-content">
                  <div className="typing-indicator">
                    <span></span>
                    <span></span>
                    <span></span>
                  </div>
                </div>
              </div>
            )}
            
            <div ref={messagesEndRef} />
          </div>

          <div className="chat-input">
            <input
              type="text"
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder={`Ask about ${context}...`}
              disabled={isLoading}
            />
            <button
              onClick={() => sendMessage()}
              disabled={!inputMessage.trim() || isLoading}
              className="send-button"
            >
              <Send size={16} />
            </button>
          </div>
        </>
      )}
    </div>
  );
};

export default FloatingChatWidget;