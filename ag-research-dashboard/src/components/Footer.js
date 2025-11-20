// src/components/Footer.js
import React, { useState, useEffect } from 'react';
import './Footer.css';

function Footer() {
  const [currentDateTime, setCurrentDateTime] = useState(new Date());

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentDateTime(new Date());
    }, 1000); // Update every second
    return () => clearInterval(timer); // Cleanup on component unmount
  }, []);

  const formattedDate = currentDateTime.toLocaleString('en-US', {
    dateStyle: 'full',
    timeStyle: 'medium',
  });

  return (
    <footer className="footer">
      <div className="footer-content">
        <span>&copy; {new Date().getFullYear()} Hydrology Lab - University of Missouri | Columbia, Missouri</span>
        <span>{formattedDate}</span>
      </div>
    </footer>
  );
}

export default Footer;