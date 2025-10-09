import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './index.css';

// Configure axios base URL based on environment
const API_BASE_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8000';
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
});

function App() {
  const [selectedFile, setSelectedFile] = useState(null);
  const [analysisResult, setAnalysisResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [rateLimitStatus, setRateLimitStatus] = useState(null);
  const [dragOver, setDragOver] = useState(false);
  const [demoInfo, setDemoInfo] = useState(null);

  // Fetch rate limit status
  const fetchRateLimitStatus = async () => {
    try {
      const response = await api.get('/api/status');
      setRateLimitStatus(response.data.rate_limit);
    } catch (err) {
      console.error('Failed to fetch rate limit status:', err);
    }
  };

  // Fetch demo info on component mount
  useEffect(() => {
    const fetchDemoInfo = async () => {
      try {
        const response = await api.get('/api/demo-info');
        setDemoInfo(response.data);
      } catch (err) {
        console.error('Failed to fetch demo info:', err);
      }
    };

    fetchDemoInfo();
    fetchRateLimitStatus();

    // Update rate limit status every 5 seconds
    const interval = setInterval(fetchRateLimitStatus, 5000);
    return () => clearInterval(interval);
  }, []);

  // Handle file selection
  const handleFileSelect = (event) => {
    const file = event.target.files[0];
    setSelectedFile(file);
    setError(null);
    setAnalysisResult(null);
  };

  // Handle drag and drop
  const handleDrop = (event) => {
    event.preventDefault();
    setDragOver(false);
    const file = event.dataTransfer.files[0];
    if (file && file.type.startsWith('image/')) {
      setSelectedFile(file);
      setError(null);
      setAnalysisResult(null);
    } else {
      setError('Please drop an image file');
    }
  };

  const handleDragOver = (event) => {
    event.preventDefault();
    setDragOver(true);
  };

  const handleDragLeave = () => {
    setDragOver(false);
  };

  // Analyze image
  const analyzeImage = async () => {
    if (!selectedFile) {
      setError('Please select an image first');
      return;
    }

    setLoading(true);
    setError(null);
    setAnalysisResult(null);

    try {
      const formData = new FormData();
      formData.append('file', selectedFile);

      const response = await api.post('/api/analyze-image', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      setAnalysisResult(response.data);
      fetchRateLimitStatus(); // Update rate limit status
    } catch (err) {
      if (err.response?.status === 429) {
        setError('Rate limit exceeded! Please wait before trying again.');
      } else {
        setError(err.response?.data?.error || 'Failed to analyze image');
      }
      fetchRateLimitStatus(); // Update rate limit status
    } finally {
      setLoading(false);
    }
  };

  // Test rate limiting
  const testRateLimit = async () => {
    setLoading(true);
    setError(null);

    try {
      const promises = Array.from({ length: 12 }, (_, i) =>
        api.get('/api/test').catch(err => ({ error: err.response?.status === 429 }))
      );

      const results = await Promise.all(promises);
      const successCount = results.filter(r => !r.error).length;
      const rateLimitCount = results.filter(r => r.error).length;

      setError(`Rate limit test: ${successCount} successful, ${rateLimitCount} rate limited`);
      fetchRateLimitStatus();
    } catch (err) {
      setError('Failed to test rate limiting');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="App">
      <div className="container">
        <div className="header">
          <h1>🤖 AI Image Analyzer</h1>
          <p>Enterprise Demo - Rate Limiting & Azure Integration</p>
          {demoInfo && (
            <p style={{ fontSize: '0.9rem', color: '#7f8c8d' }}>
              Environment: {demoInfo.environment} | Version: {demoInfo.version}
            </p>
          )}
        </div>

        <div className="demo-grid">
          {/* Image Analysis Section */}
          <div className="demo-section">
            <h2>📸 Image Analysis</h2>

            <div
              className={`upload-area ${dragOver ? 'drag-over' : ''}`}
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onClick={() => document.getElementById('file-input').click()}
            >
              <div className="upload-icon">📤</div>
              <p className="upload-text">
                {selectedFile
                  ? `Selected: ${selectedFile.name}`
                  : 'Drag & drop an image or click to select'
                }
              </p>
              <input
                id="file-input"
                type="file"
                accept="image/*"
                onChange={handleFileSelect}
                className="file-input"
              />
              <button className="upload-btn" onClick={analyzeImage} disabled={loading || !selectedFile}>
                {loading ? 'Analyzing...' : 'Analyze Image'}
              </button>
            </div>

            {loading && (
              <div className="loading">
                <div className="loading-spinner"></div>
                <p>Analyzing your image...</p>
              </div>
            )}

            {error && (
              <div className="error">
                {error}
              </div>
            )}

            {analysisResult && (
              <div className="analysis-result">
                <div className="result-header">
                  <span className="result-icon">✅</span>
                  <span className="result-title">Analysis Complete</span>
                </div>

                <div className="result-details">
                  <div className="result-section">
                    <h4>Objects Detected</h4>
                    <ul className="result-list">
                      {analysisResult.analysis.objects_detected.map((object, index) => (
                        <li key={index}>
                          {object}
                          <div
                            className="confidence-bar"
                            style={{ width: `${analysisResult.analysis.confidence_scores[index] * 100}%` }}
                          ></div>
                        </li>
                      ))}
                    </ul>
                  </div>

                  <div className="result-section">
                    <h4>File Information</h4>
                    <ul className="result-list">
                      <li>Size: {(analysisResult.file_size / 1024).toFixed(1)} KB</li>
                      <li>Type: {analysisResult.content_type}</li>
                      <li>Faces: {analysisResult.analysis.faces_detected}</li>
                      <li>Colors: {analysisResult.analysis.colors.join(', ')}</li>
                    </ul>
                  </div>
                </div>

                <div style={{ marginTop: '15px', padding: '10px', background: 'white', borderRadius: '5px' }}>
                  <strong>Description:</strong> {analysisResult.analysis.description}
                </div>
              </div>
            )}
          </div>

          {/* Rate Limiting Demo Section */}
          <div className="demo-section">
            <h2>⏱️ Rate Limiting Demo</h2>

            {rateLimitStatus && (
              <div className="rate-limit-status">
                <div className="status-item">
                  <div className="status-label">Requests Remaining</div>
                  <div className="status-value" style={{
                    color: rateLimitStatus.remaining <= 2 ? '#e74c3c' : '#27ae60'
                  }}>
                    {rateLimitStatus.remaining}/{rateLimitStatus.limit}
                  </div>
                </div>
                <div className="status-item">
                  <div className="status-label">Window</div>
                  <div className="status-value">{rateLimitStatus.window_seconds}s</div>
                </div>
              </div>
            )}

            <div className="test-buttons">
              <button
                className="test-btn primary"
                onClick={() => api.get('/api/test').then(() => fetchRateLimitStatus())}
                disabled={loading}
              >
                Single Request
              </button>
              <button
                className="test-btn secondary"
                onClick={testRateLimit}
                disabled={loading}
              >
                Test Rate Limit
              </button>
            </div>

            <div style={{ background: '#f8f9fa', padding: '15px', borderRadius: '8px', fontSize: '0.9rem' }}>
              <strong>How it works:</strong>
              <ul style={{ marginTop: '10px', paddingLeft: '20px' }}>
                <li>Each IP address is limited to 10 requests per minute</li>
                <li>Requests exceeding the limit return HTTP 429</li>
                <li>Rate limit resets on a sliding window basis</li>
                <li>Both image analysis and test endpoints are rate limited</li>
              </ul>
            </div>
          </div>
        </div>

        {/* Demo Features */}
        {demoInfo && (
          <div className="demo-section" style={{ marginTop: '20px' }}>
            <h2>🚀 Demo Features</h2>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '15px' }}>
              {demoInfo.demo_features.map((feature, index) => (
                <div key={index} style={{
                  background: '#f8f9fa',
                  padding: '12px 15px',
                  borderRadius: '8px',
                  borderLeft: '3px solid #3498db'
                }}>
                  ✅ {feature}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
