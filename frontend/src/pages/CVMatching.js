import React, { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import axios from 'axios';
import API_CONFIG from '../config/api';
import { toast } from 'react-toastify';
import { 
  FileSearch, 
  Play, 
  Download, 
  Star,
  User,
  Award,
  ExternalLink
} from 'lucide-react';

const CVMatching = () => {
  const [results, setResults] = useState(null);
  const [isMatching, setIsMatching] = useState(false);
  const [matchId, setMatchId] = useState(null);
  const [cancelTokenSource, setCancelTokenSource] = useState(null);
  const [progressStep, setProgressStep] = useState(0);
  const [progressMessage, setProgressMessage] = useState('');
  
  // Ensure clean initial state
  useEffect(() => {
    setIsMatching(false);
    setProgressMessage('');
    setProgressStep(0);
  }, []);

  // Function to highlight positive and negative statements in text
  const highlightAnalysisText = (text) => {
    if (!text) return text;

    // Split text into STRENGTHS, GAPS, and RECOMMENDATION sections
    const sections = [];
    
    // Check for STRENGTHS section
    const strengthMatch = text.match(/🟢\s*STRENGTHS?:\s*(.*?)(?=🔴\s*GAPS?:|💡\s*RECOMMENDATION:|\|\s*🔴|\|\s*💡|$)/is);
    if (strengthMatch) {
      sections.push({
        type: 'strengths',
        content: strengthMatch[1].trim()
      });
    }
    
    // Check for GAPS section
    const gapMatch = text.match(/🔴\s*GAPS?:\s*(.*?)(?=💡\s*RECOMMENDATION:|\|\s*💡|$)/is);
    if (gapMatch) {
      sections.push({
        type: 'gaps', 
        content: gapMatch[1].trim()
      });
    }
    
    // Check for RECOMMENDATION section
    const recommendationMatch = text.match(/💡\s*RECOMMENDATION:\s*(.*?)$/is);
    if (recommendationMatch) {
      sections.push({
        type: 'recommendation',
        content: recommendationMatch[1].trim()
      });
    }
    
    // If no emojis found, try to detect sections by keywords and pipe separators
    if (sections.length === 0) {
      // Handle pipe-separated format: "🟢 STRENGTHS: ... | 🔴 GAPS: ... | 💡 RECOMMENDATION: ..."
      const pipeSections = text.split('|').map(s => s.trim());
      
      for (const section of pipeSections) {
        if (section.match(/STRENGTHS?:/i)) {
          const content = section.replace(/^.*?STRENGTHS?:\s*/i, '').trim();
          if (content) {
            sections.push({ type: 'strengths', content });
          }
        } else if (section.match(/GAPS?:/i)) {
          const content = section.replace(/^.*?GAPS?:\s*/i, '').trim();
          if (content) {
            sections.push({ type: 'gaps', content });
          }
        } else if (section.match(/RECOMMENDATION:/i)) {
          const content = section.replace(/^.*?RECOMMENDATION:\s*/i, '').trim();
          if (content) {
            sections.push({ type: 'recommendation', content });
          }
        }
      }
      
      // Fallback: try basic keyword detection
      if (sections.length === 0) {
        const strengthsStart = text.search(/STRENGTHS?:/i);
        const gapsStart = text.search(/GAPS?:/i);
        const recStart = text.search(/RECOMMENDATION:/i);
        
        if (strengthsStart !== -1) {
          const strengthsEnd = Math.min(
            gapsStart !== -1 ? gapsStart : text.length,
            recStart !== -1 ? recStart : text.length
          );
          const strengthsContent = text.substring(strengthsStart, strengthsEnd)
            .replace(/^STRENGTHS?:\s*/i, '').trim();
          if (strengthsContent) {
            sections.push({ type: 'strengths', content: strengthsContent });
          }
        }
        
        if (gapsStart !== -1) {
          const gapsEnd = recStart !== -1 ? recStart : text.length;
          const gapsContent = text.substring(gapsStart, gapsEnd)
            .replace(/^GAPS?:\s*/i, '').trim();
          if (gapsContent) {
            sections.push({ type: 'gaps', content: gapsContent });
          }
        }
        
        if (recStart !== -1) {
          const recContent = text.substring(recStart)
            .replace(/^RECOMMENDATION:\s*/i, '').trim();
          if (recContent) {
            sections.push({ type: 'recommendation', content: recContent });
          }
        }
      }
    }
    
    return sections.map((section, sectionIndex) => {
      // Clean the section content
      let cleanContent = section.content
        .replace(/^\[|\]$/g, '') // Remove array brackets
        .replace(/",\s*"/g, '. ') // Replace array separators with periods
        .replace(/^"|"$/g, '') // Remove quotes
        .replace(/^🟢\s*|^🔴\s*|^💡\s*/g, '') // Remove emoji prefixes
        .trim();
      
      if (section.type === 'strengths') {
        return (
          <div key={`strength-${sectionIndex}`} style={{
            marginBottom: '16px' // Space after strengths
          }}>
            <div style={{ 
              display: 'flex',
              alignItems: 'flex-start',
              gap: '8px',
              padding: '12px 16px',
              borderRadius: '8px',
              background: 'linear-gradient(135deg, rgba(154, 230, 180, 0.1), rgba(129, 230, 167, 0.05))',
              border: '1px solid rgba(129, 230, 167, 0.2)'
            }}>
              <div style={{
                width: '8px',
                height: '8px',
                borderRadius: '50%',
                backgroundColor: '#38a169',
                marginTop: '6px',
                flexShrink: 0
              }} />
              <div>
                <div style={{
                  color: '#2f855a',
                  fontWeight: '600',
                  fontSize: '13px',
                  marginBottom: '6px',
                  textTransform: 'uppercase',
                  letterSpacing: '0.5px'
                }}>
                  STRENGTHS
                </div>
                <span style={{ 
                  color: '#2f855a', 
                  fontWeight: '400',
                  lineHeight: '1.6',
                  fontSize: '14px'
                }}>
                  {cleanContent}
                </span>
              </div>
            </div>
          </div>
        );
      } else if (section.type === 'gaps') {
        return (
          <div key={`gap-${sectionIndex}`} style={{
            marginBottom: '16px' // Space after gaps
          }}>
            <div style={{ 
              display: 'flex',
              alignItems: 'flex-start',
              gap: '8px',
              padding: '12px 16px',
              borderRadius: '8px',
              background: 'linear-gradient(135deg, rgba(254, 178, 178, 0.1), rgba(252, 129, 129, 0.05))',
              border: '1px solid rgba(252, 129, 129, 0.2)'
            }}>
              <div style={{
                width: '8px',
                height: '8px',
                borderRadius: '50%',
                backgroundColor: '#e53e3e',
                marginTop: '6px',
                flexShrink: 0
              }} />
              <div>
                <div style={{
                  color: '#c53030',
                  fontWeight: '600',
                  fontSize: '13px',
                  marginBottom: '6px',
                  textTransform: 'uppercase',
                  letterSpacing: '0.5px'
                }}>
                  GAPS
                </div>
                <span style={{ 
                  color: '#c53030', 
                  fontWeight: '400',
                  lineHeight: '1.6',
                  fontSize: '14px'
                }}>
                  {cleanContent}
                </span>
              </div>
            </div>
          </div>
        );
      } else if (section.type === 'recommendation') {
        return (
          <div key={`recommendation-${sectionIndex}`} style={{
            marginBottom: '8px'
          }}>
            <div style={{ 
              display: 'flex',
              alignItems: 'flex-start',
              gap: '8px',
              padding: '12px 16px',
              borderRadius: '8px',
              background: 'linear-gradient(135deg, rgba(173, 216, 230, 0.1), rgba(135, 206, 250, 0.05))',
              border: '1px solid rgba(135, 206, 250, 0.3)'
            }}>
              <div style={{
                width: '8px',
                height: '8px',
                borderRadius: '50%',
                backgroundColor: '#3182ce',
                marginTop: '6px',
                flexShrink: 0
              }} />
              <div>
                <div style={{
                  color: '#2c5aa0',
                  fontWeight: '600',
                  fontSize: '13px',
                  marginBottom: '6px',
                  textTransform: 'uppercase',
                  letterSpacing: '0.5px'
                }}>
                  RECOMMENDATION
                </div>
                <span style={{ 
                  color: '#2c5aa0', 
                  fontWeight: '400',
                  lineHeight: '1.6',
                  fontSize: '14px'
                }}>
                  {cleanContent}
                </span>
              </div>
            </div>
          </div>
        );
      } else {
        // Handle fallback text
        return (
          <span key={`neutral-${sectionIndex}`} style={{ 
            color: '#4a5568',
            lineHeight: '1.6',
            fontSize: '14px'
          }}>
            {cleanContent}
          </span>
        );
      }
    }).filter(Boolean);
  };
  
  // Enhanced progress messages for Resume matching process
  const progressMessages = [
    "🔗 Establishing secure connection to Google Drive...",
    "📂 Locating and accessing your Resume folder...", 
    "📄 Downloading Resume documents for analysis...",
    "🔍 Extracting text content from Resume files...",
    "🧠 Running AI-powered job requirement analysis...",
    "🎯 Analyzing each Resume against job criteria...",
    "⚡ Computing compatibility scores and rankings...",
    "📊 Generating detailed match insights...",
    "✨ Preparing comprehensive results...",
    "🔄 Finalizing analysis and formatting output..."
  ];

  // FIXED: Function to animate progress messages
  const animateProgress = () => {
    console.log('🚀 STARTING PROGRESS ANIMATION');
    let step = 0;
    setProgressStep(0);
    setProgressMessage(progressMessages[0]);
    console.log('📨 Set initial message:', progressMessages[0]);
    
    const progressInterval = setInterval(() => {
      step++;
      console.log('⏰ Progress step:', step);
      if (step < progressMessages.length) {
        setProgressStep(step);
        setProgressMessage(progressMessages[step]);
        console.log('📨 Updated message:', progressMessages[step]);
      } else {
        // Loop back to middle messages for very long operations
        const loopIndex = 4 + (step % 4); // Loop through messages 4-7
        setProgressMessage(progressMessages[loopIndex]);
        console.log('📨 Loop message:', progressMessages[loopIndex]);
      }
    }, 2000); // Change message every 2 seconds for faster updates
    
    return progressInterval;
  };

  useEffect(() => {
    // Set axios base URL
    axios.defaults.baseURL = API_CONFIG.baseURL;
    axios.defaults.timeout = API_CONFIG.timeout;
  }, []);
  
  const {
    register,
    handleSubmit,
    formState: { errors },
    watch
  } = useForm();

  const jobDescription = watch('job_description');

  const onSubmit = async (data) => {
    console.log('🚀 FORM SUBMITTED - STARTING RESUME MATCHING');
    setIsMatching(true);
    setResults(null);
    setProgressStep(0);
    setProgressMessage('🚀 INITIALIZING RESUME MATCHING PROCESS...'); // Set initial message
    
    console.log('⏰ State updated: isMatching=true, starting animation...');
    
    // Start progress animation immediately
    let progressInterval = animateProgress();
    
    // Create cancel token for request cancellation
    const source = axios.CancelToken.source();
    setCancelTokenSource(source);
    
    try {
      const response = await axios.post('/resume-matching/match', data, {
        cancelToken: source.token,
        timeout: 300000, // 5 minute timeout
      });
      
      // Clear progress animation
      clearInterval(progressInterval);
      
      setResults(response.data);
      setMatchId(response.data.match_id);
      
      // Handle different response scenarios
      const resultsCount = response.data.results?.length || 0;
      if (resultsCount > 0) {
        toast.success(`Found ${resultsCount} matching Resumes!`);
      } else {
        // Show specific message based on status
        const message = response.data.message || 'No matching Resumes found';
        if (response.data.status === 'google_drive_not_configured') {
          toast.warning('Please configure Google Drive first to access your Resume files');
        } else if (response.data.status === 'no_files_found') {
          toast.info(`No files found in '${response.data.folder_name || 'resumes'}' folder. Please upload Resume files to your Google Drive.`);
        } else {
          toast.info(message);
        }
      }
    } catch (error) {
      // Clear progress animation on error
      clearInterval(progressInterval);
      
      if (axios.isCancel(error)) {
        toast.info('Resume matching was cancelled');
      } else {
        const message = error.response?.data?.detail || 'Matching failed';
        if (error.code === 'ECONNABORTED') {
          toast.error('Request timeout: Resume matching took too long. Try with a simpler job description.');
        } else {
          toast.error(message);
        }
      }
    } finally {
      setIsMatching(false);
      setCancelTokenSource(null);
      setProgressMessage('');
      setProgressStep(0);
      // Clear progress animation
      if (progressInterval) {
        clearInterval(progressInterval);
      }
    }
  };

  const cancelMatching = () => {
    if (cancelTokenSource) {
      cancelTokenSource.cancel('Operation cancelled by user');
      toast.info('Cancelling Resume matching...');
      setProgressMessage('');
      setProgressStep(0);
    }
  };

  const getScoreColor = (score) => {
    if (score >= 80) return '#38a169';
    if (score >= 60) return '#d69e2e';
    return '#e53e3e';
  };

  const getScoreLabel = (score) => {
    if (score >= 80) return 'Excellent Match';
    if (score >= 60) return 'Good Match';
    return 'Partial Match';
  };

  const exportResults = async () => {
    if (!matchId) return;
    
    try {
      const response = await axios.get(`/resume-matching/export/${matchId}`, {
        responseType: 'blob'
      });
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `resume-match-results-${matchId}.json`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      
      toast.success('Results exported successfully!');
    } catch (error) {
      toast.error('Failed to export results');
    }
  };

  const downloadCV = async (googleDriveFileId, candidateName) => {
    console.log('🔄 Download Resume called with:', { googleDriveFileId, candidateName });
    
    if (!googleDriveFileId) {
      console.error('❌ No file ID provided');
      toast.error('File ID not available for download');
      return;
    }

    try {
      console.log('📥 Starting download request...');
      toast.info('Downloading CV...');
      
      const url = `/resume-matching/download-resume/${googleDriveFileId}`;
      console.log('🌐 Download URL:', url);
      
      const response = await axios.get(url, {
        responseType: 'blob'
      });
      
      console.log('✅ Download response received:', {
        status: response.status,
        contentType: response.headers['content-type'],
        contentLength: response.headers['content-length']
      });
      
      // Create download link
      const blobUrl = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = blobUrl;
      
      // Get filename from response headers or use default
      const contentDisposition = response.headers['content-disposition'];
      let filename = `${candidateName || 'candidate'}_Resume.pdf`;
      
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
        if (filenameMatch && filenameMatch[1]) {
          filename = filenameMatch[1].replace(/['"]/g, '');
        }
      }
      
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      
      // Clean up the URL object
      window.URL.revokeObjectURL(blobUrl);
      
      toast.success('Resume downloaded successfully!');
    } catch (error) {
      console.error('Download error:', error);
      if (error.response?.status === 404) {
        toast.error('Resume file not found or no longer available');
      } else if (error.response?.status === 400) {
        toast.error('Google Drive not properly configured');
      } else {
        toast.error('Failed to download Resume. Please try again.');
      }
    }
  };

  const downloadAllCVs = async (cvResults) => {
    console.log('🔍 downloadAllCVs called with:', cvResults);
    
    if (!cvResults || cvResults.length === 0) {
      toast.error('No Resumes to download');
      return;
    }

    // Debug: Log each Resume result to see what fields are available
    cvResults.forEach((cv, index) => {
      console.log(`Resume ${index + 1}:`, {
        filename: cv.cv_filename,
        candidate: cv.candidate_name,
        google_drive_file_id: cv.google_drive_file_id,
        download_url: cv.download_url,
        allFields: Object.keys(cv)
      });
    });

    const validCVs = cvResults.filter(cv => cv.google_drive_file_id);
    console.log(`📊 Found ${validCVs.length} valid Resumes out of ${cvResults.length} total Resumes`);
    
    if (validCVs.length === 0) {
      toast.error('No valid Resumes found for download - missing Google Drive file IDs');
      return;
    }

    toast.info(`Starting download of ${validCVs.length} Resumes...`);
    
    let successCount = 0;
    let failCount = 0;

    // Download Resumes with a small delay between each to avoid overwhelming the server
    for (let i = 0; i < validCVs.length; i++) {
      const cv = validCVs[i];
      try {
        await downloadCV(cv.google_drive_file_id, cv.candidate_name);
        successCount++;
        
        // Add small delay between downloads (except for last one)
        if (i < validCVs.length - 1) {
          await new Promise(resolve => setTimeout(resolve, 500));
        }
      } catch (error) {
        console.error(`Failed to download Resume for ${cv.candidate_name}:`, error);
        failCount++;
      }
    }

    // Show summary
    if (successCount === validCVs.length) {
      toast.success(`All ${successCount} Resumes downloaded successfully!`);
    } else if (successCount > 0) {
      toast.warning(`${successCount} Resumes downloaded, ${failCount} failed`);
    } else {
      toast.error('Failed to download any Resumes');
    }
  };

  return (
    <div className="container">
      <div style={{ marginBottom: '32px' }}>
        <h1 style={{ fontSize: '32px', fontWeight: '700', marginBottom: '8px' }}>
          Resume Matching
          <span style={{ fontSize: '12px', color: '#a0a0a0', marginLeft: '10px' }}>v2.0</span>
        </h1>
        <p style={{ color: '#718096' }}>
          Find the best candidates by matching Resumes to your job description
        </p>
      </div>

      {/* Job Description Input */}
      <div className="card">
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '20px' }}>
          <FileSearch size={24} style={{ color: '#3182ce' }} />
          <h2 style={{ fontSize: '20px', fontWeight: '600' }}>
            Job Description
          </h2>
        </div>

        <form onSubmit={handleSubmit(onSubmit)}>
          <div className="form-group">
            <label className="form-label" htmlFor="job_description">
              Enter the job description you want to match Resumes against
            </label>
            <textarea
              id="job_description"
              className="form-input form-textarea"
              placeholder="e.g., Looking for a senior Python developer with FastAPI experience, machine learning knowledge, and 5+ years of backend development experience..."
              {...register('job_description', { 
                required: 'Job description is required',
                minLength: {
                  value: 50,
                  message: 'Job description should be at least 50 characters'
                }
              })}
            />
            {errors.job_description && (
              <p className="error-text">{errors.job_description.message}</p>
            )}
            <div style={{ 
              fontSize: '12px', 
              color: '#718096', 
              marginTop: '4px' 
            }}>
              {jobDescription?.length || 0} characters
            </div>
          </div>

          <div style={{ display: 'flex', gap: '10px' }}>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={isMatching}
            >
              {isMatching ? (
                <>
                  <div className="spinner" style={{ width: '16px', height: '16px' }} />
                  Matching Resumes...
                </>
              ) : (
                <>
                  <Play size={16} />
                  Match Resumes
                </>
              )}
            </button>
            
            {isMatching && (
              <button
                type="button"
                className="btn btn-secondary"
                onClick={cancelMatching}
              >
                Cancel
              </button>
            )}
          </div>
          
          {/* Modern Professional Progress Indicator */}
          {isMatching && (
            <div 
              style={{
                marginTop: '24px',
                padding: '28px',
                background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                border: '1px solid rgba(255, 255, 255, 0.2)',
                borderRadius: '16px',
                boxShadow: '0 20px 40px rgba(102, 126, 234, 0.15), 0 8px 16px rgba(102, 126, 234, 0.1)',
                position: 'relative',
                overflow: 'hidden'
              }}
            >
              {/* Animated background overlay */}
              <div style={{
                position: 'absolute',
                top: 0,
                left: '-100%',
                width: '100%',
                height: '100%',
                background: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.1), transparent)',
                animation: 'shimmer 2s infinite'
              }} />
              
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '16px',
                marginBottom: '20px',
                position: 'relative',
                zIndex: 1
              }}>
                <div 
                  className="spinner" 
                  style={{ 
                    width: '28px', 
                    height: '28px',
                    borderWidth: '3px',
                    borderColor: '#ffffff rgba(255,255,255,0.3) #ffffff rgba(255,255,255,0.3)'
                  }} 
                />
                <span style={{
                  fontSize: '20px',
                  fontWeight: '700',
                  color: '#ffffff',
                  letterSpacing: '0.5px'
                }}>
                  🤖 AI-Powered Resume Analysis in Progress
                </span>
              </div>
              
              <div 
                style={{
                  fontSize: '16px',
                  color: 'rgba(255, 255, 255, 0.95)',
                  fontWeight: '500',
                  lineHeight: '1.5',
                  paddingLeft: '44px',
                  marginBottom: '16px',
                  position: 'relative',
                  zIndex: 1
                }}
              >
                {progressMessage || '🔄 Initializing intelligent Resume analysis...'}
              </div>
              
              <div style={{
                display: 'flex',
                flexDirection: 'column',
                gap: '8px',
                paddingLeft: '44px',
                position: 'relative',
                zIndex: 1
              }}>
                <div style={{
                  fontSize: '14px',
                  color: 'rgba(255, 255, 255, 0.9)',
                  fontWeight: '500',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px'
                }}>
                  <span style={{
                    width: '6px',
                    height: '6px',
                    backgroundColor: '#4ade80',
                    borderRadius: '50%',
                    animation: 'pulse 2s infinite'
                  }} />
                  Processing typically takes 2-5 minutes
                </div>
                <div style={{
                  fontSize: '14px',
                  color: 'rgba(255, 255, 255, 0.9)',
                  fontWeight: '500',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px'
                }}>
                  <span style={{
                    width: '6px',
                    height: '6px',
                    backgroundColor: '#60a5fa',
                    borderRadius: '50%',
                    animation: 'pulse 2s infinite 0.5s'
                  }} />
                  Advanced AI analyzing candidate compatibility
                </div>
              </div>
            </div>
          )}
          
          {/* Modern Professional Debug Panel */}
          {isMatching && (
            <div style={{
              marginTop: '16px',
              padding: '20px',
              background: 'linear-gradient(135deg, #1e293b 0%, #334155 100%)',
              border: '1px solid #475569',
              borderRadius: '12px',
              boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)',
              fontFamily: 'Monaco, Consolas, "Courier New", monospace'
            }}>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                marginBottom: '16px'
              }}>
                <span style={{
                  width: '8px',
                  height: '8px',
                  backgroundColor: '#10b981',
                  borderRadius: '50%',
                  animation: 'pulse 1.5s infinite'
                }} />
                <span style={{
                  fontSize: '14px',
                  fontWeight: '600',
                  color: '#e2e8f0',
                  letterSpacing: '0.5px'
                }}>
                  SYSTEM STATUS
                </span>
              </div>
              
              <div style={{
                display: 'grid',
                gap: '12px',
                fontSize: '13px',
                color: '#cbd5e1'
              }}>
                <div style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '8px 12px',
                  backgroundColor: 'rgba(59, 130, 246, 0.1)',
                  borderRadius: '6px',
                  border: '1px solid rgba(59, 130, 246, 0.2)'
                }}>
                  <span style={{ color: '#93c5fd' }}>Processing Status:</span>
                  <span style={{
                    color: '#10b981',
                    fontWeight: '600',
                    fontSize: '12px',
                    padding: '2px 8px',
                    backgroundColor: 'rgba(16, 185, 129, 0.2)',
                    borderRadius: '4px'
                  }}>ACTIVE</span>
                </div>
                
                <div style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '8px 12px',
                  backgroundColor: 'rgba(139, 92, 246, 0.1)',
                  borderRadius: '6px',
                  border: '1px solid rgba(139, 92, 246, 0.2)'
                }}>
                  <span style={{ color: '#c4b5fd' }}>Current Step:</span>
                  <span style={{
                    color: '#e2e8f0',
                    fontWeight: '500',
                    fontSize: '12px'
                  }}>{progressStep || 0}</span>
                </div>
                
                <div style={{
                  padding: '8px 12px',
                  backgroundColor: 'rgba(34, 197, 94, 0.1)',
                  borderRadius: '6px',
                  border: '1px solid rgba(34, 197, 94, 0.2)'
                }}>
                  <div style={{ color: '#86efac', marginBottom: '4px', fontSize: '12px' }}>Progress Message:</div>
                  <div style={{
                    color: '#f1f5f9',
                    fontWeight: '500',
                    fontSize: '12px',
                    lineHeight: '1.4'
                  }}>
                    {progressMessage || 'Initializing...'}
                  </div>
                </div>
              </div>
            </div>
          )}
        </form>
      </div>

      {/* Results */}
      {results && (
        <div className="card">
          <div style={{ 
            display: 'flex', 
            justifyContent: 'space-between', 
            alignItems: 'center', 
            marginBottom: '20px' 
          }}>
            <h2 style={{ fontSize: '20px', fontWeight: '600' }}>
              Matching Results ({results.results?.length || 0})
            </h2>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button
                onClick={() => downloadAllCVs(results.results)}
                className="btn btn-primary"
                disabled={!results.results || results.results.length === 0}
                style={{ 
                  fontSize: '13px',
                  opacity: (!results.results || results.results.length === 0) ? 0.5 : 1
                }}
              >
                <Download size={14} />
                Download All Resumes
              </button>
              <button
                onClick={exportResults}
                className="btn btn-secondary"
                style={{ fontSize: '13px' }}
              >
                <ExternalLink size={14} />
                Export Results
              </button>
            </div>
          </div>

          {(results.results?.length || 0) === 0 ? (
            <div style={{ 
              textAlign: 'center', 
              padding: '40px', 
              color: '#718096' 
            }}>
              <FileSearch size={48} style={{ opacity: 0.3, marginBottom: '16px' }} />
              <p>{results.message || 'No matching Resumes found for this job description.'}</p>
              <p style={{ fontSize: '14px', marginTop: '8px' }}>
                {results.status === 'google_drive_not_configured' 
                  ? 'Please set up Google Drive integration first.'
                  : results.status === 'no_files_found'
                  ? `Upload Resume files to your '${results.folder_name || 'resumes'}' folder in Google Drive.`
                  : 'Try adjusting your job description or check your Resume folder configuration.'
                }
              </p>
            </div>
          ) : (
            <div style={{ display: 'grid', gap: '16px' }}>
              {(results.results || []).map((result, index) => (
                <div 
                  key={index}
                  className="match-result"
                  style={{ 
                    background: 'white',
                    border: '1px solid #e2e8f0',
                    borderRadius: '8px',
                    padding: '20px'
                  }}
                >
                  <div style={{ 
                    display: 'flex', 
                    justifyContent: 'space-between', 
                    alignItems: 'flex-start',
                    marginBottom: '16px'
                  }}>
                    <div style={{ flex: 1 }}>
                      {/* File Name */}
                      <h3 style={{ 
                        fontSize: '18px', 
                        fontWeight: '600', 
                        marginBottom: '8px',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px',
                        color: '#2d3748'
                      }}>
                        <FileSearch size={16} />
                        {result.cv_filename}
                      </h3>
                      
                      {/* Candidate Name */}
                      {result.candidate_name && (
                        <div style={{ 
                          fontSize: '16px', 
                          fontWeight: '500',
                          color: '#4a5568',
                          marginBottom: '12px',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '6px'
                        }}>
                          <User size={14} />
                          {result.candidate_name}
                        </div>
                      )}
                    </div>
                    
                    <div style={{ textAlign: 'right' }}>
                      <div style={{ 
                        display: 'flex', 
                        alignItems: 'center', 
                        gap: '4px',
                        marginBottom: '4px'
                      }}>
                        <Star size={16} style={{ color: getScoreColor(result.relevance_score) }} />
                        <span style={{ 
                          fontSize: '20px', 
                          fontWeight: '700',
                          color: getScoreColor(result.relevance_score)
                        }}>
                          {result.relevance_score}%
                        </span>
                      </div>
                      <div style={{ 
                        fontSize: '12px', 
                        color: getScoreColor(result.relevance_score),
                        fontWeight: '500'
                      }}>
                        {getScoreLabel(result.relevance_score)}
                      </div>
                      
                      {result.google_drive_file_id ? (
                        <div style={{ marginTop: '8px' }}>
                          <button
                            onClick={() => {
                              console.log('🔍 Download button clicked for:', result.candidate_name, 'File ID:', result.google_drive_file_id);
                              downloadCV(result.google_drive_file_id, result.candidate_name);
                            }}
                            style={{
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '4px',
                              padding: '6px 12px',
                              background: '#3182ce',
                              color: 'white',
                              border: 'none',
                              borderRadius: '4px',
                              fontSize: '12px',
                              fontWeight: '500',
                              cursor: 'pointer',
                              transition: 'background 0.2s'
                            }}
                            onMouseOver={(e) => e.target.style.background = '#2c5aa0'}
                            onMouseOut={(e) => e.target.style.background = '#3182ce'}
                          >
                            <Download size={12} />
                            Download Resume
                          </button>
                        </div>
                      ) : (
                        <div style={{ marginTop: '8px' }}>
                          <span style={{
                            fontSize: '11px',
                            color: '#718096',
                            fontStyle: 'italic'
                          }}>
                            Download not available (File ID: {result.google_drive_file_id || 'missing'})
                          </span>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Match Analysis Section */}
                  {result.match_analysis && (
                    <div style={{ marginBottom: '16px' }}>
                      <h4 style={{ 
                        fontSize: '15px', 
                        fontWeight: '600', 
                        marginBottom: '8px',
                        color: '#2d3748',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px'
                      }}>
                        AI Match Analysis
                        <div style={{ 
                          fontSize: '10px', 
                          background: '#e2e8f0', 
                          color: '#4a5568',
                          padding: '2px 6px',
                          borderRadius: '4px',
                          fontWeight: '400'
                        }}>
                          🟢 Strengths • 🔴 Gaps • 💡 Recommendation
                        </div>
                      </h4>
                      <div style={{ 
                        fontSize: '14px', 
                        lineHeight: '1.6',
                        background: '#f7fafc',
                        padding: '14px',
                        borderRadius: '8px',
                        border: '1px solid #e2e8f0',
                        marginBottom: '0'
                      }}>
                        {highlightAnalysisText(result.match_analysis)}
                      </div>
                      <div style={{
                        fontSize: '11px',
                        color: '#718096',
                        marginTop: '8px',
                        display: 'flex',
                        gap: '15px',
                        flexWrap: 'wrap'
                      }}>
                        <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                          🟢 <strong>Strengths:</strong> Skills and qualifications that match
                        </span>
                        <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                          🔴 <strong>Gaps:</strong> Missing requirements or areas for improvement
                        </span>
                        <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                          💡 <strong>Recommendation:</strong> Overall assessment and next steps
                        </span>
                      </div>
                    </div>
                  )}

                  {/* Key Skills & Qualifications Section */}
                  <div style={{ marginBottom: '16px' }}>
                    <h4 style={{ 
                      fontSize: '15px', 
                      fontWeight: '600', 
                      marginBottom: '10px',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px',
                      color: '#2d3748'
                    }}>
                      <Award size={15} />
                      Key Skills & Qualifications
                    </h4>
                    <div style={{ 
                      display: 'flex', 
                      flexWrap: 'wrap', 
                      gap: '8px' 
                    }}>
                      {result.key_skills && result.key_skills.length > 0 ? (
                        result.key_skills.map((skill, skillIndex) => (
                          <span
                            key={skillIndex}
                            style={{ 
                              background: '#3182ce', 
                              color: 'white',
                              padding: '6px 12px', 
                              borderRadius: '6px', 
                              fontSize: '13px',
                              fontWeight: '500'
                            }}
                          >
                            {skill}
                          </span>
                        ))
                      ) : (
                        <span style={{ 
                          background: '#f7fafc', 
                          color: '#718096',
                          padding: '6px 12px', 
                          borderRadius: '6px', 
                          fontSize: '13px',
                          fontStyle: 'italic',
                          border: '1px solid #e2e8f0'
                        }}>
                          No key skills mentioned
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default CVMatching;