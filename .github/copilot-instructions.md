# AG Research Web Platform - AI Coding Assistant Guide

## Architecture Overview

This is an agricultural IoT data platform with a **Flask backend** (`ag-research-backend/`) and **React dashboard** (`ag-research-dashboard/`) for visualizing soil sensor and weather data from 4 field dataloggers.

### Key Components
- **Backend**: Flask API with per-device JSON caching (TTL: 10min)
- **Frontend**: React dashboard with Chart.js visualizations and Leaflet maps  
- **Data Sources**: Zentra Cloud API (soil sensors) + Climate Engine API (weather forecasts)
- **Virtual Environments**: Uses `myenv/` or `nrnenv/` Python environments
- **Rate Limiting**: Zentra API has rate limits - backend uses 30min cache TTL and exponential backoff

## Critical Development Patterns

### Multi-Device Architecture
The system supports **exactly 4 dataloggers** with hardcoded device serial numbers:
```python
ALLOWED_DEVICE_SNS = ["z6-32396", "z6-20881", "z6-27574", "z6-27573"]
```

**Essential endpoint pattern**: Always prefer `/api/combined_all` over individual device calls - it returns data for all 4 devices in one efficient request.

### Sensor Data Normalization (Critical for Backend Changes)
The backend extensively processes Zentra API responses using port-based sensor identification:
- **Port extraction regex**: `(?:port|p)\s*[:#]?\s*(\d+)` (case-insensitive)
- **VWC sensors**: 10cm depth (Port 1) → "TEROS 12 Soil VWC @ 10cm", 20cm depth (Port 2) → "TEROS 12 Soil VWC @ 20cm" 
- **Unit conversions**: Celsius→Fahrenheit, mm→inches, raw fractions→percentages
- **Fallback logic**: Generic "Water Content" used when port-specific data unavailable

### Configuration Management (Required for Setup)
**Environment variables are mandatory** - both directories need `.env` files:
- `ZENTRA_API_TOKEN`: Required for all sensor data fetching
- `CLIMATE_ENGINE_API_TOKEN`: Required for weather forecasts
- `ZENTRA_DEVICE_SN`: Default device (fallback: "z6-23000")

**Frontend config centralized** in `src/config/apiConfig.js` with refresh intervals and coordinates.

## Development Workflows

### Backend Development (Windows PowerShell)
```powershell
# ALWAYS run this first in any new PowerShell session/tab/directory
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process
cd ag-research-backend
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process  # Run again after cd
.\myenv\Scripts\Activate.ps1  # or .\nrnenv\Scripts\python.exe
pip install -r requirements.txt
python app.py  # Runs on localhost:5000
```

### Frontend Development (PowerShell)
```powershell
# ALWAYS run this first in any new PowerShell session/tab/directory
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process
cd ag-research-dashboard
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process  # Run again after cd
npm install
npm start  # Runs on localhost:3000, proxies to Flask backend
```

### Essential Endpoints for Testing
- `/api/combined_all` - **Primary endpoint** for all 4 devices (use this first)
- `/api/live/<device_sn>` - Raw sensor readings per device
- `/api/table/<device_sn>` - Formatted table data with proper units
- `/healthz` - Health check and cache status

## Component Architecture Patterns

### Chart Components (Consistent Structure)
All chart components follow this exact pattern:
```javascript
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement } from 'chart.js';
ChartJS.register(CategoryScale, LinearScale, BarElement);
// Use react-chartjs-2 wrappers (Line, Bar, etc.)
// Data processing via weatherDataService.js functions
```

### Map Integration Pattern
- **react-leaflet** with OpenStreetMap tiles
- Station coordinates from `src/data/mockData.js` (precise GPS coordinates for 4 dataloggers + 1 weather station)
- Device serial numbers (`deviceSn`) link map markers to API data

### Error Handling & Fallback (Critical)
**Every API call MUST have fallback data generators**:
```javascript
// Pattern: Always return valid data structure even when APIs fail
return generateFallbackData(); // from mockData.js
```

## Key Files (Architecture Understanding)

### Backend Core
- `app.py` - Main Flask server with caching logic and `_series_port()` function
- `requirements.txt` - Minimal deps: Flask, Flask-Cors, python-dotenv, requests
- `data_cache_<device-sn>.json` - Per-device cache files (auto-generated)

### Frontend Core  
- `src/services/weatherDataService.js` - **Central API integration layer**
- `src/config/apiConfig.js` - All endpoints, tokens, coordinates, refresh intervals
- `src/data/mockData.js` - Station GPS coordinates + fallback data generators
- `src/components/WeatherOverview.js` - Main dashboard with sensor data table

## Data Flow & Integration Points

### Request Chain
1. **React components** → `weatherDataService.js` → Flask API (`/api/combined_all`)
2. **Flask API** → Zentra Cloud API (with caching) → normalized sensor data
3. **Parallel**: Climate Engine API → weather forecasts → chart data
4. **Polling intervals**: 5min (table data), 15min (chart data)

### API Response Structure (Must Maintain)
Flask endpoints return standardized format:
```json
{
  "latest": {...},  // Most recent readings
  "units": {...},   // Field units (°F, inches, %, etc.) 
  "rows": [...]     // Time-series data
}
```

### Cross-Component Communication
- Components share `weatherDataService.js` utility functions
- Error objects include fallback data to prevent UI breaks  
- Time formatting and unit conversions centralized in service layer

### Climate Engine API Patterns (Precipitation & ETO)
**Direct frontend calls** to Climate Engine API bypass Flask backend for forecast data:
- **Dataset**: `CFS_GRIDMET` for forecasts, `GRIDMET` for historical
- **Variables**: `eto` (evapotranspiration), `pr` (precipitation)  
- **Endpoint**: `/timeseries/native/forecasts/coordinates` with coordinates array format
- **Chart colors**: Precipitation = blue (`rgba(54, 162, 235)`), ETO = green (`rgba(75, 192, 75)`)
- **Authentication**: JWT tokens expire - get new token from https://app.climateengine.org/ and update `src/config/apiConfig.js`

**When modifying APIs**: Always update both Flask route handler AND corresponding `weatherDataService.js` function - they expect matched JSON structures.