// src/components/MapComponent.js
import React, { useEffect, useMemo, useState, useCallback } from "react";
import {
  MapContainer,
  TileLayer,
  ImageOverlay,
  LayersControl,
  Rectangle,
  useMap,
  Marker,
  Popup
} from "react-leaflet";
import L from "leaflet";
import { stations } from "../data/mockData";
import { FLASK_API_CONFIG } from "../config/apiConfig";
import "leaflet/dist/leaflet.css";
import "./MapComponent.css";

/* ========= Custom Marker Icons ========= */
// Fix default marker icon issues
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: require('leaflet/dist/images/marker-icon-2x.png'),
  iconUrl: require('leaflet/dist/images/marker-icon.png'),
  shadowUrl: require('leaflet/dist/images/marker-shadow.png'),
});

// Create professional location pin icons for different station types
const dataloggerIcon = L.divIcon({
  html: `<svg width="24" height="34" viewBox="0 0 24 34" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M12 0C5.373 0 0 5.373 0 12C0 21 12 34 12 34S24 21 24 12C24 5.373 18.627 0 12 0Z" fill="#2196F3" stroke="white" stroke-width="2"/>
    <circle cx="12" cy="12" r="6" fill="white"/>
    <circle cx="12" cy="12" r="3" fill="#2196F3"/>
  </svg>`,
  className: 'custom-div-icon',
  iconSize: [24, 34],
  iconAnchor: [12, 34],
  popupAnchor: [0, -34]
});

const weatherStationIcon = L.divIcon({
  html: `<svg width="26" height="36" viewBox="0 0 26 36" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M13 0C6.373 0 1 5.373 1 12C1 21 13 36 13 36S25 21 25 12C25 5.373 19.627 0 13 0Z" fill="#FF9800" stroke="white" stroke-width="2"/>
    <circle cx="13" cy="12" r="7" fill="white"/>
    <circle cx="13" cy="12" r="4" fill="#FF9800"/>
  </svg>`,
  className: 'custom-div-icon',
  iconSize: [26, 36],
  iconAnchor: [13, 36],
  popupAnchor: [0, -36]
});

// Function to get appropriate icon based on station type
const getStationIcon = (stationType) => {
  switch (stationType) {
    case 'datalogger':
      return dataloggerIcon;
    case 'weather station':
      return weatherStationIcon;
    default:
      return new L.Icon.Default();
  }
};

const { BaseLayer, Overlay } = LayersControl;

/* ========= Exact field bounds (from your 4 corners) ========= */
const BOUNDS = [[38.9066667, -92.2816667], [38.9072222, -92.2797222]];
const CENTER = [
  (BOUNDS[0][0] + BOUNDS[1][0]) / 2,
  (BOUNDS[0][1] + BOUNDS[1][1]) / 2
];

/* ========= Band images (grayscale) ========= */
const SRC_RED   = "/images/New_08_08_2025_transparent_reflectance_red.png";
const SRC_GREEN = "/images/New_08_08_2025_transparent_reflectance_green.png";
const SRC_BLUE  = "/images/New_08_08_2025_transparent_reflectance_blue.png";

/* ========= Simple RGB Composite Creation ========= */
function createSimpleRGBComposite() {
  return new Promise((resolve, reject) => {
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    
    // Load all three images
    const redImg = new Image();
    const greenImg = new Image();
    const blueImg = new Image();
    
    let loadedCount = 0;
    
    const checkAllLoaded = () => {
      loadedCount++;
      if (loadedCount === 3) {
        try {
          // Set canvas size based on first image
          canvas.width = redImg.width;
          canvas.height = redImg.height;
          
          // Create a simple RGB composite by blending the three grayscale images
          // Each image represents the intensity of that color channel
          
          // Get image data for each channel
          const redCanvas = document.createElement('canvas');
          const greenCanvas = document.createElement('canvas');
          const blueCanvas = document.createElement('canvas');
          
          redCanvas.width = greenCanvas.width = blueCanvas.width = redImg.width;
          redCanvas.height = greenCanvas.height = blueCanvas.height = redImg.height;
          
          const redCtx = redCanvas.getContext('2d');
          const greenCtx = greenCanvas.getContext('2d');
          const blueCtx = blueCanvas.getContext('2d');
          
          // Draw each image
          redCtx.drawImage(redImg, 0, 0);
          greenCtx.drawImage(greenImg, 0, 0);
          blueCtx.drawImage(blueImg, 0, 0);
          
          // Get pixel data
          const redData = redCtx.getImageData(0, 0, redImg.width, redImg.height);
          const greenData = greenCtx.getImageData(0, 0, greenImg.width, greenImg.height);
          const blueData = blueCtx.getImageData(0, 0, blueImg.width, blueImg.height);
          
          // Create composite image
          const compositeData = ctx.createImageData(redImg.width, redImg.height);
          
          for (let i = 0; i < compositeData.data.length; i += 4) {
            // Use the grayscale values as RGB channel intensities
            compositeData.data[i] = redData.data[i];         // Red channel
            compositeData.data[i + 1] = greenData.data[i];   // Green channel  
            compositeData.data[i + 2] = blueData.data[i];    // Blue channel
            compositeData.data[i + 3] = 255;                 // Alpha (opaque)
          }
          
          // Draw composite to main canvas
          ctx.putImageData(compositeData, 0, 0);
          
          // Convert to data URL
          const dataURL = canvas.toDataURL('image/png', 0.9);
          resolve(dataURL);
        } catch (error) {
          reject(error);
        }
      }
    };
    
    const handleError = (error) => {
      console.error('Error loading RGB images:', error);
      reject(error);
    };
    
    redImg.onload = checkAllLoaded;
    redImg.onerror = handleError;
    redImg.crossOrigin = "anonymous"; // Handle CORS if needed
    redImg.src = SRC_RED;
    
    greenImg.onload = checkAllLoaded;
    greenImg.onerror = handleError;
    greenImg.crossOrigin = "anonymous";
    greenImg.src = SRC_GREEN;
    
    blueImg.onload = checkAllLoaded;
    blueImg.onerror = handleError;
    blueImg.crossOrigin = "anonymous";
    blueImg.src = SRC_BLUE;
  });
}

/* ---------- view helpers ---------- */
function MapInitializer({ setMapInstance, bounds }) {
  const map = useMap();
  useEffect(() => {
    // Store map reference for parent component
    setMapInstance(map);
    // Set initial view to high zoom but keep tiles visible
    map.setView(CENTER, 18, { animate: false });
  }, [map, setMapInstance]);
  return null;
}

function ResetViewButton({ bounds }) {
  const map = useMap();
  return (
    <button
      onClick={() => map.fitBounds(bounds, { padding: [24, 24] })}
      style={{
        background: "#fff",
        border: "1px solid #ccc",
        borderRadius: 4,
        padding: "6px 10px",
        cursor: "pointer",
        boxShadow: "0 1px 3px rgba(0,0,0,0.1)",
        fontSize: "11px",
        fontWeight: "bold",
        minWidth: "80px"
      }}
      title="Reset view to field"
    >
      🎯 Fit to Field
    </button>
  );
}

/* ---------- main component ---------- */
function MapComponent({ onViewData }) {
  const [filter, setFilter] = useState("all");
  const [showRGBLayers, setShowRGBLayers] = useState(false);
  const [rgbComposite, setRgbComposite] = useState(null);
  const [isLoadingRGB, setIsLoadingRGB] = useState(false);
  const [mapInstance, setMapInstance] = useState(null);
  const [stationStatuses, setStationStatuses] = useState({});

  // Check sensor data availability and update station status
  const checkSensorData = useCallback(async (station) => {
    // Make Section 6 offline, everything else online
    return station.name === 'Section 6' ? 'offline' : 'online';
  }, []);

  // Update station statuses on component mount
  useEffect(() => {
    const updateStatuses = async () => {
      const statusUpdates = {};
      for (const station of stations) {
        statusUpdates[station.id] = await checkSensorData(station);
      }
      setStationStatuses(statusUpdates);
    };
    updateStatuses();
  }, [checkSensorData]);

  // Filter handler with zoom functionality
  const handleFilterToggle = useCallback((newFilter) => {
    const wasFiltered = filter === newFilter;
    setFilter(wasFiltered ? 'all' : newFilter);
    
    if (mapInstance && !wasFiltered) {
      // Zoom to specific station types
      const stationsOfType = stations.filter(station => station.type === newFilter);
      if (stationsOfType.length > 0) {
        if (stationsOfType.length === 1) {
          // Single station - zoom to it with high zoom but keep tiles visible
          mapInstance.setView(stationsOfType[0].position, 19, { animate: true, duration: 1 });
        } else {
          // Multiple stations - fit bounds to show all
          const group = new L.featureGroup(stationsOfType.map(station => 
            L.marker(station.position)
          ));
          mapInstance.fitBounds(group.getBounds().pad(0.1), { animate: true, duration: 1 });
        }
      }
    } else if (mapInstance && wasFiltered) {
      // Return to field view when deselecting filter
      mapInstance.setView(CENTER, 18, { animate: true, duration: 1 });
    }
  }, [filter, mapInstance]);

  // Load RGB composite when requested
  const loadRGBComposite = useCallback(async () => {
    if (rgbComposite || isLoadingRGB) return; // Don't reload if already loaded
    
    setIsLoadingRGB(true);
    try {
      console.log('Creating RGB composite...');
      const composite = await createSimpleRGBComposite();
      setRgbComposite(composite);
      setShowRGBLayers(true);
      console.log('RGB composite created successfully!');
    } catch (error) {
      console.error('Failed to create RGB composite:', error);
    } finally {
      setIsLoadingRGB(false);
    }
  }, [rgbComposite, isLoadingRGB]);

  const startCenter = useMemo(() => CENTER, []);

  // Memoize filtered stations with updated statuses
  const filteredStations = useMemo(() => {
    const stationsWithStatus = stations.map(station => ({
      ...station,
      status: stationStatuses[station.id] || station.status
    }));
    if (filter === "all") return stationsWithStatus;
    return stationsWithStatus.filter(station => station.type === filter);
  }, [filter, stationStatuses]);

  return (
    <MapContainer
      center={startCenter}
      zoom={18}
      minZoom={13}
      maxZoom={19}
      zoomDelta={0.5}
      zoomSnap={0}
      scrollWheelZoom={true}
      style={{ height: "100%", minHeight: 500, width: "100%" }}
    >
      <MapInitializer setMapInstance={setMapInstance} bounds={BOUNDS} />
      
      {/* Top Left-Center Controls */}
      <div style={{
        position: "absolute",
        zIndex: 4000,
        top: 15,
        left: "40%",
        transform: "translateX(-50%)",
        display: "flex",
        gap: "8px",
        background: "rgba(255,255,255,0.95)",
        padding: "6px 10px",
        borderRadius: "20px",
        boxShadow: "0 2px 10px rgba(0,0,0,0.1)",
        backdropFilter: "blur(10px)",
        border: "1px solid rgba(0,0,0,0.1)"
      }}>
          <ResetViewButton bounds={BOUNDS} />
          <button
            onClick={() => {
              if (rgbComposite) {
                setShowRGBLayers(!showRGBLayers);
              } else {
                loadRGBComposite();
              }
            }}
            disabled={isLoadingRGB}
            style={{
              background: isLoadingRGB ? "#ff9800" : (showRGBLayers ? "#f44336" : "#4CAF50"),
              color: "white",
              border: "none",
              borderRadius: 6,
              padding: "8px 12px",
              cursor: isLoadingRGB ? "wait" : "pointer",
              boxShadow: "0 2px 4px rgba(0,0,0,0.15)",
              fontSize: "12px",
              fontWeight: "bold",
              opacity: isLoadingRGB ? 0.7 : 1
            }}
            title={isLoadingRGB ? "Loading RGB composite..." : (showRGBLayers ? "Hide RGB composite" : "Load satellite image")}
          >
            {isLoadingRGB ? "🔄 Loading..." : (showRGBLayers ? "Hide Image" : "📡 Load Image")}
          </button>
      </div>

      {/* Bottom Left Controls */}
      <div style={{
        position: "absolute",
        zIndex: 4000,
        bottom: 40,
        left: 15,
        display: "flex",
        gap: "8px",
        background: "rgba(255,255,255,0.95)",
        padding: "6px 10px",
        borderRadius: "20px",
        boxShadow: "0 2px 10px rgba(0,0,0,0.1)",
        backdropFilter: "blur(10px)",
        border: "1px solid rgba(0,0,0,0.1)"
      }}>
          <button 
            onClick={() => handleFilterToggle('datalogger')}
            style={{ 
              padding: "6px 10px", 
              fontSize: "11px", 
              fontWeight: "600", 
              backgroundColor: filter === 'datalogger' ? "#2c5530" : "#fff", 
              color: filter === 'datalogger' ? "#FDB719" : "#333", 
              border: filter === 'datalogger' ? "2px solid #FDB719" : "1px solid #ccc",
              borderRadius: "4px", 
              cursor: "pointer",
              transition: "all 0.2s ease",
              boxShadow: "0 1px 2px rgba(0,0,0,0.1)"
            }}
          >
            � Dataloggers
          </button>
          <button 
            onClick={() => handleFilterToggle('weather station')}
            style={{ 
              padding: "6px 10px", 
              fontSize: "11px", 
              fontWeight: "600", 
              backgroundColor: filter === 'weather station' ? "#2c5530" : "#fff", 
              color: filter === 'weather station' ? "#FDB719" : "#333", 
              border: filter === 'weather station' ? "2px solid #FDB719" : "1px solid #ccc",
              borderRadius: "4px", 
              cursor: "pointer",
              transition: "all 0.2s ease",
              boxShadow: "0 1px 2px rgba(0,0,0,0.1)"
            }}
          >
            🌡️ Weather Station
          </button>
      </div>

      <LayersControl position="bottomright">
        <BaseLayer checked name="OpenStreetMap">
          <TileLayer
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            attribution="© OpenStreetMap contributors"
          />
        </BaseLayer>

        <Overlay checked name="🌾 Field Boundary">
          <Rectangle bounds={BOUNDS} pathOptions={{ color: "#FDB719", weight: 3, fillOpacity: 0, dashArray: "5, 5" }} />
        </Overlay>

        {/* RGB Composite Overlay */}
        {showRGBLayers && rgbComposite && (
          <Overlay checked name="🌈 RGB Composite">
            <ImageOverlay url={rgbComposite} bounds={BOUNDS} opacity={0.8} zIndex={2100} />
          </Overlay>
        )}
        
        {/* Individual Band Overlays (grayscale for reference) */}
        {showRGBLayers && (
          <>
            <Overlay name="🔴 Red Band (Grayscale)">
              <ImageOverlay url={SRC_RED} bounds={BOUNDS} opacity={0.5} zIndex={2101} />
            </Overlay>
            <Overlay name="🟢 Green Band (Grayscale)">
              <ImageOverlay url={SRC_GREEN} bounds={BOUNDS} opacity={0.5} zIndex={2102} />
            </Overlay>
            <Overlay name="🔵 Blue Band (Grayscale)">
              <ImageOverlay url={SRC_BLUE} bounds={BOUNDS} opacity={0.5} zIndex={2103} />
            </Overlay>
          </>
        )}

      </LayersControl>

      {/* Station markers with custom icons */}
      {filteredStations.map((station) => (
        <Marker 
          key={station.id} 
          position={station.position}
          icon={getStationIcon(station.type)}
        >
          <Popup>
            <div style={{ minWidth: '250px', maxWidth: '300px' }}>
              <h3 style={{ margin: '0 0 8px 0', color: '#2c5530' }}>
                {station.type === 'datalogger' ? '📊' : '🌡️'} {station.name}
              </h3>
              <p style={{ margin: '4px 0', fontSize: '13px' }}>
                <strong>Type:</strong> {station.type === 'datalogger' ? 'Soil Datalogger' : 'Weather Station'}
              </p>
              <p style={{ margin: '4px 0', fontSize: '13px' }}>
                <strong>Status:</strong> 
                <span style={{ 
                  color: station.status === 'online' ? '#4CAF50' : '#f44336',
                  fontWeight: 'bold'
                }}>
                  {station.status === 'online' ? '🟢 Online' : '🔴 Offline'}
                </span>
              </p>
              {station.deviceSn && (
                <p style={{ margin: '4px 0', fontSize: '12px', color: '#666' }}>
                  <strong>Device ID:</strong> {station.deviceSn}
                </p>
              )}
              
              {/* Quick Data Preview for Dataloggers */}
              {station.type === 'datalogger' && station.status === 'online' && (
                <div style={{ 
                  background: '#f8f9fa', 
                  padding: '8px', 
                  borderRadius: '4px', 
                  margin: '8px 0',
                  fontSize: '11px'
                }}>
                  <div style={{ fontWeight: 'bold', marginBottom: '4px', color: '#2c5530' }}>Recent Sensor Data:</div>
                  <div>� Plot 1 & 2 Active</div>
                  <div>� Multiple Depth Sensors</div>
                  <div>💧 Soil Moisture Monitoring</div>
                  <div style={{ fontSize: '10px', color: '#666', marginTop: '4px' }}>Click for detailed analytics</div>
                </div>
              )}
              
              {/* Weather Station Preview */}
              {station.type === 'weather station' && station.status === 'online' && (
                <div style={{ 
                  background: '#f8f9fa', 
                  padding: '8px', 
                  borderRadius: '4px', 
                  margin: '8px 0',
                  fontSize: '11px'
                }}>
                  <div style={{ fontSize: '10px', color: '#666', marginTop: '4px' }}>Updated: 1 min ago</div>
                </div>
              )}
              
              {station.status === "online" && (
                <button 
                  onClick={() => onViewData(station)}
                  style={{
                    width: '100%',
                    padding: '10px 12px',
                    backgroundColor: '#FDB719',
                    color: '#000',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: 'pointer',
                    fontWeight: 'bold',
                    marginTop: '8px',
                    fontSize: '13px'
                  }}
                >
                  � View Detailed Analytics
                </button>
              )}
              
              {station.status === "offline" && (
                <div style={{
                  padding: '8px',
                  backgroundColor: '#ffebee',
                  color: '#c62828',
                  borderRadius: '4px',
                  fontSize: '12px',
                  textAlign: 'center',
                  marginTop: '8px'
                }}>
                  ⚠️ Device is currently offline
                </div>
              )}
            </div>
          </Popup>
        </Marker>
      ))}
    </MapContainer>
  );
}

export default MapComponent;