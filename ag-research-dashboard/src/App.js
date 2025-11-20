// src/App.js
import React, { useState } from "react";

// Import new components
import Navbar from "./components/Navbar";
import Footer from "./components/Footer";

import MapComponent from "./components/MapComponent";
import DataAnalyticsPanel from "./components/DataAnalyticsPanel";
import WeatherOverview from "./components/WeatherOverview";
import Modal from "./components/Modal";
import "./App.css";



function App() {
  
  const [selectedStation, setSelectedStation] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  const handleViewData = (station) => {
    if (!station) return;
    if (station.type === "weather station") {
      if (station.externalUrl) {
        window.open(station.externalUrl, "_blank", "noopener,noreferrer");
      }
      return;
    }
    // datalogger → open modal
    setSelectedStation(station);
    setIsModalOpen(true);
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setSelectedStation(null);
  };

  return (
    <div className="app-container">
      <Navbar /> {/* Add Navbar here */}
      
      {/* This new div will hold the main content */}
      <div className="main-content">
        <div className="map-pane">
          <MapComponent onViewData={handleViewData} />
        </div>
        <div className="overview-pane">
          <WeatherOverview />
        </div>
      </div>
      
      <Footer /> {/* Add Footer here */}
      
      {/* Modal is unaffected by layout changes */}
      <Modal isOpen={isModalOpen} onClose={handleCloseModal}>
        {selectedStation && <DataAnalyticsPanel station={selectedStation} />}
      </Modal>
    </div>
  );
}

export default App;