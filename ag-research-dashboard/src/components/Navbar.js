// src/components/Navbar.js
import React, { useState, useEffect } from 'react';
import './Navbar.css';

function Navbar() {
  const [currentTime, setCurrentTime] = useState(new Date());
  const [systemStatus, setSystemStatus] = useState('online');

  // Update time every minute
  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date());
    }, 60000);
    return () => clearInterval(timer);
  }, []);

  // Check system status (could be enhanced to check actual API health)
  useEffect(() => {
    const checkSystemStatus = async () => {
      try {
        // Simple health check - could be enhanced with actual API call
        setSystemStatus('online');
      } catch (error) {
        setSystemStatus('offline');
      }
    };
    checkSystemStatus();
  }, []);

  const formatTime = (date) => {
    return date.toLocaleTimeString('en-US', { 
      hour: '2-digit', 
      minute: '2-digit',
      hour12: true 
    });
  };

  const formatDate = (date) => {
    return date.toLocaleDateString('en-US', { 
      month: 'short', 
      day: 'numeric',
      year: 'numeric'
    });
  };

  return (
    <nav className="navbar">
      <div className="navbar-brand">
        <div className="brand-icon">🌾</div>
        <div className="brand-text">
          <div className="brand-title">SOUTH FARM RESEARCH CENTER</div>
          <div className="brand-subtitle">Agricultural IoT Dashboard</div>
        </div>
      </div>
      


      <div className="navbar-actions">
        <div className="status-indicators">
          <div className="system-status">
            <span className={`status-dot ${systemStatus}`}></span>
            <span className="status-text">System {systemStatus === 'online' ? 'Online' : 'Offline'}</span>
          </div>
          <div className="datetime-display">
            <div className="time">{formatTime(currentTime)}</div>
            <div className="date">{formatDate(currentTime)}</div>
          </div>
        </div>
        
        <div className="action-buttons">
          <button 
            className="weather-station-btn"
            onClick={() => window.open("https://meter-weather-station.onrender.com/", "_blank")}
            title="Open Weather Station Dashboard"
          >
            <span className="btn-icon">🌡️</span>
            <span className="btn-text">Weather Station</span>
          </button>
          
          <button 
            className="control-dashboard-btn" 
            onClick={() => window.open("https://homeassistant.tail41a295.ts.net/local/index.html", "_blank")}
            title="Open Control Dashboard"
          >
            <span className="btn-icon">⚙️</span>
            <span className="btn-text">Control Panel</span>
          </button>
        </div>
      </div>
    </nav>
  );
}

export default Navbar;