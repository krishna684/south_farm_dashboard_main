// src/components/DataAnalyticsPanel.js
import React, { useEffect, useState } from "react";

const API_BASE = process.env.REACT_APP_API_BASE_URL || ""; // set in .env or use CRA proxy

// ---- helpers ----
async function getJSON(url, init) {
  const res = await fetch(url, init);
  const ct = res.headers.get("content-type") || "";
  const txt = await res.text();
  if (!ct.includes("application/json")) {
    throw new Error(
      `Expected JSON but got ${ct}. URL=${url}\nFirst 200 chars:\n${txt.slice(0, 200)}`
    );
  }
  let data;
  try {
    data = JSON.parse(txt);
  } catch (e) {
    throw new Error(`Invalid JSON: ${e.message}\nFirst 200 chars:\n${txt.slice(0, 200)}`);
  }
  if (!res.ok) throw new Error(data?.error || `HTTP ${res.status}`);
  return data;
}

export default function DataAnalyticsPanel({ station }) {
  const [dev, setDev] = useState(null); // device payload picked from /api/combined_all
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let stop = false;
    async function load() {
      try {
        setErr("");
        setLoading(true);
        const sn = station?.deviceSn || process.env.REACT_APP_DEVICE_SN;
        if (!sn) throw new Error("Missing deviceSn for station");

        console.log(`Fetching data for device: ${sn}`);
        const json = await getJSON(`${API_BASE}/api/combined_all`);
        console.log('Combined API response:', json);
        
        const found = json?.devices?.find(d => d.device_sn === sn);
        console.log(`Found device ${sn}:`, found);
        
        if (!found) {
          const have = (json?.devices || []).map(d => d.device_sn).join(", ") || "(none)";
          throw new Error(`Device ${sn} not found in /api/combined_all. Have: ${have}`);
        }
        
        // Check if device has error
        if (found.error) {
          throw new Error(`Device ${sn} error: ${found.error}`);
        }
        
        console.log(`Device ${sn} latest data:`, found.latest);
        console.log(`Device ${sn} ports data:`, found.ports);
        console.log(`Device ${sn} soil data:`, found.soil);
        
        // Debug port data availability
        const ports = found.ports || {};
        const hasAnyPortData = Object.values(ports).some(val => val != null);
        console.log(`Device ${sn} has port data:`, hasAnyPortData);
        console.log(`Device ${sn} port keys:`, Object.keys(ports));
        
        // Debug individual port values
        Object.entries(ports).forEach(([key, value]) => {
          if (value != null) {
            console.log(`  ${key}: ${value}`);
          }
        });
        
        if (!stop) setDev(found);
      } catch (e) {
        if (!stop) setErr(e.message || "Failed to load");
      } finally {
        if (!stop) setLoading(false);
      }
    }
    load();
    return () => { stop = true; };
  }, [station]);

  const latest = dev?.latest || {};
  const ports  = dev?.ports  || {};
  const extUrl = station?.externalUrl || dev?.links?.zentracloud;

  return (
    <div>
      <h2 style={{marginTop:0}}>{station?.name || dev?.device_sn || "Datalogger"}</h2>

      {loading && <p>Loading data for {station?.name || 'device'}...</p>}
      {err && (
        <div style={{color:"#e88", padding: '10px', border: '1px solid #e88', borderRadius: '4px'}}>
          <p><strong>Error:</strong> {err}</p>
          <p><strong>Device SN:</strong> {station?.deviceSn || 'Unknown'}</p>
          <p><strong>API Endpoint:</strong> {API_BASE}/api/combined_all</p>
          <button onClick={() => window.location.reload()} style={{marginTop: '10px'}}>
            Retry
          </button>
        </div>
      )}

      {!loading && !err && (
        <>
          {/* Connection Status */}
          <div style={{
            padding: '10px', 
            backgroundColor: (dev && Object.values(ports).some(val => val != null)) ? '#e8f5e8' : '#ffebee', 
            borderRadius: '6px', 
            marginBottom: '15px',
            border: `1px solid ${(dev && Object.values(ports).some(val => val != null)) ? '#4caf50' : '#f44336'}`
          }}>
            <div style={{display: 'flex', alignItems: 'center', gap: '8px'}}>
              <span style={{fontSize: '16px'}}>
                {(dev && Object.values(ports).some(val => val != null)) ? '🟢' : '🔴'}
              </span>
              <strong style={{color: (dev && Object.values(ports).some(val => val != null)) ? '#2e7d32' : '#c62828'}}>
                {(dev && Object.values(ports).some(val => val != null)) ? 'Device Online' : 'Device Offline'}
              </strong>
            </div>
            <div style={{fontSize: '13px', color: '#666', marginTop: '4px'}}>
              Device: {station?.deviceSn} | Last Update: {latest?.time || 'Never'}
            </div>
          </div>

          {/* Section Header with Real Data */}
          <div style={{
            padding: '20px',
            backgroundColor: '#f8f9fa',
            borderRadius: '8px',
            marginBottom: '20px',
            border: '1px solid #dee2e6'
          }}>
            <h3 style={{margin: '0 0 12px 0', color: '#2c5530', fontSize: '20px'}}>
              📊 {station?.name} - Live Sensor Data
            </h3>
            <div style={{fontSize: '14px', color: '#666', lineHeight: '1.4'}}>
              <strong>Device ID:</strong> {dev?.device_sn}<br />
              <strong>Last Update:</strong> {latest?.time || 'No recent data'}
            </div>
          </div>

          {/* Plot 1 - Show available data */}
          {(ports?.P1_vwc10_pct || ports?.P2_vwc20_pct || ports?.P3_wp_kpa || latest?.soil10_pct || latest?.soil20_pct || ports?.P1_temp10_c || ports?.P2_temp20_c || ports?.P1_ec10_us_cm || ports?.P2_ec20_us_cm) && (
            <section style={card}>
              <h3 style={{margin: '0 0 15px 0', color: '#2c5530', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '18px'}}>
                <span>🌱</span> Plot 1 - Soil Sensors
              </h3>
              <div style={{display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '20px'}}>
                {/* 10cm Depth */}
                {(ports?.P1_vwc10_pct || latest?.soil10_pct || ports?.P1_temp10_c || ports?.P1_ec10_us_cm) && (
                  <div style={depthCard}>
                    <h4 style={depthHeader}>📏 10cm Depth {latest?.soil10_pct && '- Active'}</h4>
                    <div style={sensorGrid}>
                      {renderSensorValue('💧 Soil Moisture:', ports?.P1_vwc10_pct || latest?.soil10_pct, '%')}
                      {ports?.P1_temp10_c ? 
                        renderSensorValue('🌡️ Soil Temperature:', ports?.P1_temp10_c, '°C') :
                        <div style={{display: 'flex', justifyContent: 'space-between', padding: '4px 0', opacity: 0.6}}>
                          <span>🌡️ Soil Temperature:</span>
                          <span style={{fontSize: '12px', color: '#999'}}>Not configured</span>
                        </div>
                      }
                      {ports?.P1_ec10_us_cm ? 
                        renderSensorValue('⚡ Electrical Conductivity:', ports?.P1_ec10_us_cm, 'µS/cm') :
                        <div style={{display: 'flex', justifyContent: 'space-between', padding: '4px 0', opacity: 0.6}}>
                          <span>⚡ Electrical Conductivity:</span>
                          <span style={{fontSize: '12px', color: '#999'}}>Not configured</span>
                        </div>
                      }
                    </div>
                  </div>
                )}
                
                {/* 20cm Depth */}
                {(ports?.P2_vwc20_pct || latest?.soil20_pct || ports?.P2_temp20_c || ports?.P2_ec20_us_cm || ports?.P3_wp_kpa) && (
                  <div style={depthCard}>
                    <h4 style={depthHeader}>📏 20cm Depth {(latest?.soil20_pct || ports?.P2_vwc20_pct) && '- Active'}</h4>
                    <div style={sensorGrid}>
                      {(ports?.P2_vwc20_pct || latest?.soil20_pct) ? 
                        renderSensorValue('💧 Soil Moisture:', ports?.P2_vwc20_pct || latest?.soil20_pct, '%') :
                        <div style={{display: 'flex', justifyContent: 'space-between', padding: '4px 0', opacity: 0.6}}>
                          <span>💧 Soil Moisture:</span>
                          <span style={{fontSize: '12px', color: '#999'}}>No 20cm sensor</span>
                        </div>
                      }
                      {ports?.P2_temp20_c ? 
                        renderSensorValue('🌡️ Soil Temperature:', ports?.P2_temp20_c, '°C') :
                        <div style={{display: 'flex', justifyContent: 'space-between', padding: '4px 0', opacity: 0.6}}>
                          <span>🌡️ Soil Temperature:</span>
                          <span style={{fontSize: '12px', color: '#999'}}>Not configured</span>
                        </div>
                      }
                      {ports?.P2_ec20_us_cm ? 
                        renderSensorValue('⚡ Electrical Conductivity:', ports?.P2_ec20_us_cm, 'µS/cm') :
                        <div style={{display: 'flex', justifyContent: 'space-between', padding: '4px 0', opacity: 0.6}}>
                          <span>⚡ Electrical Conductivity:</span>
                          <span style={{fontSize: '12px', color: '#999'}}>Not configured</span>
                        </div>
                      }
                      {ports?.P3_wp_kpa ? 
                        renderSensorValue('🔬 Matric Potential:', ports?.P3_wp_kpa, 'kPa') :
                        <div style={{display: 'flex', justifyContent: 'space-between', padding: '4px 0', opacity: 0.6}}>
                          <span>🔬 Matric Potential:</span>
                          <span style={{fontSize: '12px', color: '#999'}}>Not configured</span>
                        </div>
                      }
                    </div>
                  </div>
                )}
              </div>
            </section>
          )}

          {/* Plot 2 - Show sensor status */}
          <section style={card}>
            <h3 style={{margin: '0 0 15px 0', color: '#2c5530', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '18px'}}>
              <span>🌿</span> Plot 2 - Soil Sensors
            </h3>
            
            {/* Show Plot 2 is not configured if no data */}
            {!(ports?.P4_vwc10_pct || ports?.P5_vwc20_pct || ports?.P6_wp_kpa || ports?.P4_temp10_c || ports?.P5_temp20_c || ports?.P4_ec10_us_cm || ports?.P5_ec20_us_cm) ? (
              <div style={{
                padding: '20px',
                backgroundColor: '#f8f9fa',
                border: '1px solid #dee2e6',
                borderRadius: '6px',
                textAlign: 'center'
              }}>
                <div style={{marginBottom: '8px'}}>📭 <strong>Plot 2 Configuration</strong></div>
                <div style={{fontSize: '14px', color: '#666'}}>
                  No sensors configured for Plot 2 on this datalogger.<br />
                  This section focuses on Plot 1 soil monitoring.
                </div>
              </div>
            ) : (
              <div style={{display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '20px'}}>
                {/* 10cm Depth */}
                {(ports?.P4_vwc10_pct || ports?.P4_temp10_c || ports?.P4_ec10_us_cm) && (
                  <div style={depthCard}>
                    <h4 style={depthHeader}>📏 10cm Depth</h4>
                    <div style={sensorGrid}>
                      {renderSensorValue('💧 Soil Moisture:', ports?.P4_vwc10_pct, '%')}
                      {renderSensorValue('🌡️ Soil Temperature:', ports?.P4_temp10_c, '°C')}
                      {renderSensorValue('⚡ Electrical Conductivity:', ports?.P4_ec10_us_cm, 'µS/cm')}
                    </div>
                  </div>
                )}
                
                {/* 20cm Depth */}
                {(ports?.P5_vwc20_pct || ports?.P5_temp20_c || ports?.P5_ec20_us_cm || ports?.P6_wp_kpa) && (
                  <div style={depthCard}>
                    <h4 style={depthHeader}>📏 20cm Depth</h4>
                    <div style={sensorGrid}>
                      {renderSensorValue('💧 Soil Moisture:', ports?.P5_vwc20_pct, '%')}
                      {renderSensorValue('🌡️ Soil Temperature:', ports?.P5_temp20_c, '°C')}
                      {renderSensorValue('⚡ Electrical Conductivity:', ports?.P5_ec20_us_cm, 'µS/cm')}
                      {renderSensorValue('🔬 Matric Potential:', ports?.P6_wp_kpa, 'kPa')}
                    </div>
                  </div>
                )}
              </div>
            )}
          </section>

          {/* Environmental Conditions Summary - Only show if has environmental data */}
          {(latest?.temp_f || latest?.vpd_kpa || latest?.precip_in || latest?.solar_w_m2) && (
            <section style={card}>
              <h3 style={{margin: '0 0 15px 0', color: '#2c5530', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '18px'}}>
                <span>🌤️</span> Environmental Summary
              </h3>
              <div style={{display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px'}}>
                {latest?.temp_f && (
                  <div style={envItem}>
                    <span style={envLabel}>🌡️ Air Temperature:</span>
                    <span style={envValue}>{latest.temp_f.toFixed(1)}°F</span>
                  </div>
                )}
                {latest?.vpd_kpa && (
                  <div style={envItem}>
                    <span style={envLabel}>💨 VPD:</span>
                    <span style={envValue}>{latest.vpd_kpa.toFixed(2)} kPa</span>
                  </div>
                )}
                {latest?.precip_in && (
                  <div style={envItem}>
                    <span style={envLabel}>🌧️ Precipitation:</span>
                    <span style={envValue}>{latest.precip_in.toFixed(3)} in</span>
                  </div>
                )}
                {latest?.solar_w_m2 && (
                  <div style={envItem}>
                    <span style={envLabel}>☀️ Solar Radiation:</span>
                    <span style={envValue}>{latest.solar_w_m2.toFixed(0)} W/m²</span>
                  </div>
                )}
              </div>
            </section>
          )}





          {/* Show message if no soil sensor data */}
          {!Object.values(ports || {}).some(val => val != null) && !latest?.soil10_pct && !latest?.soil20_pct && (
            <div style={{
              padding: '15px',
              backgroundColor: '#ffebee',
              borderRadius: '6px',
              fontSize: '14px',
              color: '#c62828',
              textAlign: 'center',
              border: '1px solid #f44336',
              marginBottom: '15px'
            }}>
              <div style={{marginBottom: '8px'}}>
                <strong>🚫 No Sensor Data Available</strong>
              </div>
              <div style={{fontSize: '12px'}}>
                This datalogger is not transmitting any soil sensor data.
                <br />Check device power, connectivity, and sensor configuration in Zentra Cloud.
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

// Helper function to render sensor values (hides N/A values)
const renderSensorValue = (label, value, unit) => {
  // Only render if value exists and is not null
  if (value == null || value === 'N/A' || value === undefined) {
    return null; // Don't render N/A values
  }
  
  const formattedValue = typeof value === 'number' ? value.toFixed(1) : value;
  
  return (
    <div style={sensorRow} key={label}>
      <span style={sensorLabel}>{label}</span>
      <span style={sensorValue}>{formattedValue}{unit}</span>
    </div>
  );
};

// styles
const card = { 
  border:"1px solid #ddd", 
  borderRadius: 8, 
  padding: 16, 
  marginBottom: 16,
  backgroundColor: '#fafafa'
};

const sensorLabel = {
  display: 'inline-block',
  minWidth: '140px',
  fontSize: '13px',
  color: '#555'
};

const envItem = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  padding: '8px 0',
  borderBottom: '1px solid #eee'
};

const envLabel = {
  fontSize: '13px',
  color: '#555'
};

const envValue = {
  fontWeight: 'bold',
  color: '#2c5530'
};

const depthCard = {
  padding: '15px',
  backgroundColor: 'white',
  border: '1px solid #e0e0e0',
  borderRadius: '6px',
  boxShadow: '0 1px 3px rgba(0,0,0,0.1)'
};

const depthHeader = {
  margin: '0 0 12px 0',
  color: '#444',
  fontSize: '16px',
  fontWeight: 'bold',
  paddingBottom: '8px',
  borderBottom: '2px solid #FDB719'
};

const sensorGrid = {
  display: 'flex',
  flexDirection: 'column',
  gap: '8px'
};

const sensorRow = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  padding: '6px 0',
  borderBottom: '1px solid #f0f0f0'
};

const sensorValue = {
  fontWeight: 'bold',
  color: '#2c5530',
  fontSize: '14px'
};