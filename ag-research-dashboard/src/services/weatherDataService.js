// src/services/weatherDataService.js
import { 
  CLIMATE_ENGINE_CONFIG, 
  FLASK_API_CONFIG, 
  FIELD_LOCATION 
} from '../config/apiConfig';

/**
 * Fetch ETO forecast from Climate Engine API
 */
async function fetchETOForecast() {
  const headers = {
    "Authorization": `Bearer ${CLIMATE_ENGINE_CONFIG.API_TOKEN}`
  };
  
  const params = new URLSearchParams({
    dataset: "CFS_GRIDMET",
    variable: "eto",
    model: "ens_mean",
    area_reducer: "mean",
    start_day: "day01",
    end_day: "day05",
    coordinates: `[[${FIELD_LOCATION.lon},${FIELD_LOCATION.lat}]]`,
    export_format: "json"
  });

  try {
    const response = await fetch(`${CLIMATE_ENGINE_CONFIG.BASE_URL}/timeseries/native/forecasts/coordinates?${params}`, {
      headers,
      timeout: 30000
    });
    
    if (!response.ok) {
      throw new Error(`Climate Engine API error: ${response.status}`);
    }
    
    const data = await response.json();
    
    // Parse Climate Engine response structure
    const dataBlocks = data.Data || data.data || [];
    if (!dataBlocks.length) {
      throw new Error("No data blocks in Climate Engine response");
    }
    
    const innerData = dataBlocks[0].Data || dataBlocks[0].data || [];
    if (!innerData.length) {
      throw new Error("No inner data in Climate Engine response");
    }
    
    return innerData.map(row => ({
      date: row.Date || row.date,
      eto_mm: parseFloat(row["eto (mm)"] || row.value || 0),
      eto_in: (parseFloat(row["eto (mm)"] || row.value || 0) / 25.4)
    }));
    
  } catch (error) {
    console.warn("Failed to fetch ETO forecast from Climate Engine:", error);
    // Return mock forecast data as fallback
    return generateMockETOForecast();
  }
}

/**
 * Generate mock ETO forecast data as fallback
 */
function generateMockETOForecast() {
  const mockData = [];
  const today = new Date();
  
  for (let i = 0; i < 5; i++) {
    const date = new Date(today);
    date.setDate(today.getDate() + i);
    
    mockData.push({
      date: date.toISOString().split('T')[0],
      eto_mm: 3 + Math.random() * 2, // 3-5mm typical range
      eto_in: (3 + Math.random() * 2) / 25.4
    });
  }
  
  return mockData;
}

/**
 * Fetch historical weather data from Flask API
 */
async function fetchHistoricalData() {
  try {
    const response = await fetch(`${FLASK_API_CONFIG.BASE_URL}/api/live/z6-23000`);
    if (!response.ok) {
      throw new Error(`Flask API error: ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error("Failed to fetch historical data from Flask API:", error);
    throw error;
  }
}

/**
 * Convert Flask API data to chart format
 */
function processHistoricalData(apiData) {
  const processedData = [];
  
  // Get the sensor data - using first 6 hours (current + 5 past)
  const tempData = apiData["Air Temperature"] || [];
  const precipData = apiData["Precipitation"] || [];
  
  for (let i = 0; i < Math.min(6, tempData.length); i++) {
    const time = tempData[i]?.time;
    const tempC = parseFloat(tempData[i]?.value || 0);
    const precipMM = parseFloat(precipData[i]?.value || 0);
    
    // Convert to proper units
    const tempF = (tempC * 9/5) + 32;
    const precipIn = precipMM / 25.4;
    
    processedData.push({
      time: formatTimeForChart(time, i),
      type: "historical",
      tempMin: tempF - 2,  // Approximate min/max from single reading
      tempMax: tempF + 3,
      tempAvg: tempF,
      precipitation: precipIn,
      eto: null // No historical ETO data available
    });
  }
  
  return processedData.reverse(); // Show oldest to newest
}

/**
 * Process future forecast data
 */
function processForecastData(etoForecast) {
  return etoForecast.map((forecast, index) => ({
    time: `Day +${index + 1}`,
    type: "forecast",
    tempMin: null, // No temperature forecast from Climate Engine
    tempMax: null,
    tempAvg: null,
    precipitation: null, // Could add precipitation forecast if needed
    eto: forecast.eto_in
  }));
}

/**
 * Format time for chart display
 */
function formatTimeForChart(timeString, hoursAgo) {
  if (!timeString) {
    return hoursAgo === 0 ? "Now" : `-${hoursAgo}h`;
  }
  
  try {
    const date = new Date(timeString);
    if (hoursAgo === 0) {
      return "Now";
    }
    return date.toLocaleTimeString('en-US', { 
      hour: 'numeric', 
      minute: '2-digit',
      hour12: true 
    });
  } catch {
    return hoursAgo === 0 ? "Now" : `-${hoursAgo}h`;
  }
}

/**
 * Main function to fetch combined weather data for chart
 */
export async function fetchCombinedWeatherData() {
  try {
    console.log("Fetching weather data...");
    
    // Fetch both historical and forecast data in parallel
    const [historicalData, etoForecast] = await Promise.all([
      fetchHistoricalData(),
      fetchETOForecast()
    ]);
    
    // Process the data
    const historical = processHistoricalData(historicalData);
    const forecast = processForecastData(etoForecast);
    
    // Combine historical and forecast data
    const combinedData = [...historical, ...forecast];
    
    console.log("Combined weather data:", combinedData);
    return combinedData;
    
  } catch (error) {
    console.error("Error fetching combined weather data:", error);
    
    // Return fallback mock data
    return generateFallbackData();
  }
}

/**
 * Generate fallback data when APIs fail
 */
function generateFallbackData() {
  const fallback = [];
  
  // Past 6 hours (including current)
  for (let i = 5; i >= 0; i--) {
    fallback.push({
      time: i === 0 ? "Now" : `-${i}h`,
      type: "historical",
      tempMin: 70 - i,
      tempMax: 80 - i,
      tempAvg: 75 - i,
      precipitation: Math.random() * 0.1,
      eto: null
    });
  }
  
  // Next 5 days forecast
  for (let i = 1; i <= 5; i++) {
    fallback.push({
      time: `Day +${i}`,
      type: "forecast",
      tempMin: null,
      tempMax: null,
      tempAvg: null,
      precipitation: null,
      eto: (3 + Math.random() * 2) / 25.4 // 3-5mm converted to inches
    });
  }
  
  return fallback;
}