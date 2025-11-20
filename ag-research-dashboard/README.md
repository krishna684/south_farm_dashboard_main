# 🌾 Agriculture Research Dashboard

This React application is the frontend of the AG Research Web Platform. It visualizes field datalogger and weather station data: soil moisture (VWC), soil temperature, matric potential, precipitation, ETO (evapotranspiration), radiation, wind, and humidity. It pairs with the Flask backend found in `../ag-research-backend`.

## ✨ Core Features

* Interactive Leaflet map of 4 dataloggers + 1 weather station
* Unified data loading via backend `/api/combined_all` endpoint
* Chart.js visualizations (precipitation vs ETO, temperatures, solar, wind, soil moisture depth comparison)
* Fallback data generation to keep charts rendering when external APIs fail
* Station detail panels and analytics modal components

## 🗂 Data Flow Summary

```
React Components → weatherDataService.js → Flask API (/api/combined_all)
Flask Backend → Zentra Cloud (cached per device) + Climate Engine
Climate Engine (direct calls for forecast) → Forecast charts
```

## 🛠 Tech Stack

| Layer      | Tools |
|------------|-------|
| Framework  | React 19 |
| Charts     | Chart.js 4 + react-chartjs-2 |
| Mapping    | Leaflet + react-leaflet |
| Time utils | date-fns |
| Styling    | Plain CSS |

## 🚀 Local Development

### 1. Clone root repository
```bash
git clone <repo-url>
cd ag-research-web
```

### 2. Backend (Flask) – run first in separate terminal
```powershell
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process
cd ag-research-backend
./myenv/Scripts/python.exe -m pip install -r requirements.txt
./myenv/Scripts/python.exe app.py
```
Environment variables required in `ag-research-backend/.env`:
```
ZENTRA_API_TOKEN=Token YOUR_ZENTRA_TOKEN
CLIMATE_ENGINE_API_TOKEN=YOUR_CLIMATE_ENGINE_TOKEN (optional if only frontend direct calls)
ZENTRA_DEVICE_SN=z6-23000
```

### 3. Frontend (this directory)
```powershell
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process
cd ag-research-dashboard
npm install
npm start
```
Visit: http://localhost:3000 (proxy calls backend at :5000).

## 🔑 Configuration Files
* `src/config/apiConfig.js` – API tokens, base URLs, refresh intervals, field coordinates
* `src/services/weatherDataService.js` – Fetch logic for Climate Engine & Flask endpoints
* `src/data/mockData.js` – Station coordinates + fallback data builders

## 🧪 Scripts
* `npm start` – Dev server with auto-reload
* `npm test` – Jest/react-testing-library (basic CRA harness)
* `npm run build` – Production build

## 🛡 Resilience & Fallbacks
When Climate Engine or Zentra calls fail, components inject generated fallback values (maintaining chart structure). LocalStorage may retain prior forecast data to bridge gaps.

## 📁 Structure (abridged)
```
src/
  components/            # Charts, Map, Panels, Modals
  services/weatherDataService.js
  config/apiConfig.js
  data/mockData.js
  App.js / App.css
  index.js
```

## 🧭 Naming Conventions (Sensors)
* TEROS 12 VWC: `TEROS 12 Soil VWC @ 10cm`, `TEROS 12 Soil VWC @ 20cm`
* Ports (extended): `TEROS 12 Soil VWC @ 10cm (P1)` etc.
* Matric Potential: `TEROS 21 Matric Potential (P3/P6)`

## 🔄 Refresh Intervals
* Table data: 5 min
* Chart/forecast data: 15 min

## ✅ Production Notes
* Avoid committing real API tokens – move them to `.env` files
* Run `npm audit` periodically; address high severity issues
* Consider adding service worker / PWA only if offline needs emerge

## 📌 Future Enhancements
* Unified token refresh for Climate Engine (JWT expiration handling)
* Port-dynamic sensor labeling UI
* Historical aggregation (daily rollups) endpoint

## 📄 License
Internal research tool – add license text if external distribution planned.

---
For backend architecture details see `.github/copilot-instructions.md` in repository root.