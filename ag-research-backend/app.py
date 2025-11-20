import os
import re
import json
import time
from math import isfinite
from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import requests

# Load .env variables
load_dotenv()

app = Flask(__name__)
CORS(app)  # Enable Cross-Origin requests

# Configuration
API_TOKEN = os.getenv("ZENTRA_API_TOKEN")
DEVICE_SN = os.getenv("ZENTRA_DEVICE_SN") or "z6-23000"
CLIMATE_ENGINE_TOKEN = os.getenv("CLIMATE_ENGINE_API_TOKEN")
BASE_URL = "https://zentracloud.com/api/v3/get_readings/"
CLIMATE_ENGINE_BASE_URL = "https://api.climateengine.org"
CACHE_FILE = "data_cache.json"
ETO_CACHE_FILE = "eto_cache.json"
TEMP_FORECAST_CACHE_FILE = "temp_forecast_cache.json"
CACHE_TTL_MINUTES = 1  # 1 minute cache to respect Zentra API rate limit of 1 call per minute

# ---------------------- helpers: ports & conversions -------------------------

def _series_port(series: dict):
    """
    Try to extract the port number from Zentra series metadata.
    Checks common fields, then tries to parse out "Port 1"/"(Port 2)" from labels.
    Returns 1/2 as int if found, else None.
    """
    # direct numeric fields first
    for key in ("port", "port_num", "source_port", "channel", "port_number"):
        if key in series and series[key] is not None:
            try:
                return int(series[key])
            except (TypeError, ValueError):
                pass

    # Strings that may contain "Port 1", "(Port 2)", "P2", etc.
    label_fields = ("series_label", "label", "name", "sensor_name", "series_name")
    port_regex = re.compile(r"(?:port|p)\s*[:#]?\s*(\d+)", re.IGNORECASE)
    for lf in label_fields:
        val = series.get(lf)
        if isinstance(val, str):
            m = port_regex.search(val)
            if m:
                try:
                    return int(m.group(1))
                except ValueError:
                    pass
    return None

def _to_pct(val):
    try:
        v = float(val)
    except (TypeError, ValueError):
        return None
    if not isfinite(v):
        return None
    # If Zentra sends fraction (0–1), convert to percent
    return round(v * 100, 1) if v <= 1 else round(v, 1)

def _to_f(c):
    try:
        v = float(c)
    except (TypeError, ValueError):
        return None
    if not isfinite(v):
        return None
    return round(v * 9/5 + 32, 1)

def _to_in(mm):
    try:
        v = float(mm)
    except (TypeError, ValueError):
        return None
    if not isfinite(v):
        return None
    return round(v / 25.4, 3)

def _series(data: dict, key: str):
    """Safe getter for a series list by label (case-sensitive fallback)."""
    return data.get(key) or data.get(key.title()) or []

# ------------------------- fetch & normalize (cached) ------------------------

# Fetch from ZENTRA API and normalize
def fetch_fresh_data():
    headers = {
        "Authorization": API_TOKEN,   # keeping your header format unchanged
        "Accept": "application/json"
    }
    now_utc = datetime.now(timezone.utc)
    params = {
        "device_sn": DEVICE_SN,
        "start_date": (now_utc - timedelta(hours=30)).strftime("%Y-%m-%d %H:%M"),  # Extended to 30 hours to ensure 24+ hours coverage
        "end_date": now_utc.strftime("%Y-%m-%d %H:%M"),
        "output_format": "json",
        "per_page": 1000
    }

    # Implement retry logic for rate limiting
    max_retries = 3
    retry_delay = 1  # Start with 1 second
    
    for attempt in range(max_retries):
        try:
            resp = requests.get(BASE_URL, headers=headers, params=params, timeout=15)
            
            if resp.status_code == 429:
                print(f"Rate limited by Zentra API (attempt {attempt + 1}/{max_retries}). Waiting {retry_delay} seconds...")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                    continue
                else:
                    raise Exception(f"Zentra API rate limit exceeded after {max_retries} attempts. Please try again later.")
            
            resp.raise_for_status()
            raw_data = resp.json()
            break  # Success - exit retry loop
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                print(f"Rate limited by Zentra API (attempt {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                else:
                    raise Exception(f"Zentra API rate limit exceeded. Please reduce request frequency.")
            else:
                raise e

    data = raw_data.get("data", {})
    sensors = {}

    for label, series_list in data.items():
        # Special handling: Split TEROS 12 Water Content by port -> 10cm (Port 1) and 20cm (Port 2)
        if label == "Water Content" or label.lower() in ("volumetric water content", "vwc", "soil vwc"):
            for series in series_list:
                p = _series_port(series)
                if p == 1:
                    dest_key = "TEROS 12 Soil VWC @ 10cm"
                elif p == 2:
                    dest_key = "TEROS 12 Soil VWC @ 20cm"
                else:
                    dest_key = None  # unknown port → keep generic below

                readings = []
                for r in series.get("readings", []):
                    v = r.get("value")
                    try:
                        v = float(v)
                    except (TypeError, ValueError):
                        pass
                    readings.append({
                        "time": r.get("datetime"),
                        "value": v
                    })

                if dest_key:
                    sensors[dest_key] = readings
                else:
                    # Fallback if port can't be detected
                    sensors.setdefault("Water Content", []).extend(readings)

        else:
            # Default behavior for all other labels (Air Temperature, Precipitation, Solar Radiation, VPD, etc.)
            readings = []
            for series in series_list:
                for r in series.get("readings", []):
                    readings.append({
                        "time": r.get("datetime"),
                        "value": r.get("value")
                    })
            sensors[label] = readings

    return sensors

# Cache wrapper with better error handling
def get_cached_data():
    # return fresh cache if still within TTL
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                cached = json.load(f)
            ts = datetime.fromisoformat(cached["timestamp"])
            if (datetime.now(timezone.utc) - ts) < timedelta(minutes=CACHE_TTL_MINUTES):
                print(f"Using cached data from {cached['timestamp']}")
                return cached["data"]
        except Exception:
            # ignore cache read/parse errors and fetch fresh
            pass

    # Try to fetch fresh data
    try:
        fresh = fetch_fresh_data()
        try:
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump({"timestamp": datetime.now(timezone.utc).isoformat(), "data": fresh}, f)
            print("Successfully fetched and cached fresh data")
        except Exception:
            # don't break serving just because cache write failed
            pass
        return fresh
    except Exception as e:
        print(f"Error fetching fresh data: {e}")
        
        # If fresh fetch fails, try to return stale cache data
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, "r", encoding="utf-8") as f:
                    cached = json.load(f)
                print(f"Returning stale cached data from {cached['timestamp']} due to API error")
                return cached["data"]
            except Exception:
                pass
        
        # If all fails, return empty data structure
        print("No cached data available, returning empty data")
        return {}

# ----------------------------- ETO & climate data functions ------------------

def fetch_eto_data():
    """
    Fetch ETO (Evapotranspiration) data from z6-23000 device via Zentra API.
    Look for ETO fields in the sensor data.
    """
    headers = {
        "Authorization": API_TOKEN,
        "Accept": "application/json"
    }
    now_utc = datetime.now(timezone.utc)
    params = {
        "device_sn": DEVICE_SN,
        "start_date": (now_utc - timedelta(days=7)).strftime("%Y-%m-%d %H:%M"),
        "end_date": now_utc.strftime("%Y-%m-%d %H:%M"),
        "output_format": "json",
        "per_page": 1000
    }

    try:
        resp = requests.get(BASE_URL, headers=headers, params=params, timeout=15)
        resp.raise_for_status()
        raw_data = resp.json()
        
        data = raw_data.get("data", {})
        eto_data = []
        
        # Look for ETO-related series in the data
        for label, series_list in data.items():
            if any(term in label.lower() for term in ["eto", "evapotranspiration", "et", "reference et"]):
                for series in series_list:
                    for reading in series.get("readings", []):
                        eto_data.append({
                            "time": reading.get("datetime"),
                            "value": reading.get("value"),
                            "label": label,
                            "units": series.get("metadata", {}).get("units", "mm")
                        })
        
        return sorted(eto_data, key=lambda x: x["time"] if x["time"] else "")
    
    except Exception as e:
        print(f"Error fetching ETO data: {e}")
        return []

def get_cached_eto_data():
    """Get cached ETO data with TTL"""
    if os.path.exists(ETO_CACHE_FILE):
        try:
            with open(ETO_CACHE_FILE, "r", encoding="utf-8") as f:
                cached = json.load(f)
            ts = datetime.fromisoformat(cached["timestamp"])
            if (datetime.now(timezone.utc) - ts) < timedelta(minutes=CACHE_TTL_MINUTES):
                return cached["data"]
        except Exception:
            pass

    fresh_eto = fetch_eto_data()
    try:
        with open(ETO_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump({"timestamp": datetime.now(timezone.utc).isoformat(), "data": fresh_eto}, f)
    except Exception:
        pass
    return fresh_eto

def fetch_climate_engine_forecast(lat=40.8176, lon=-96.6917):
    """
    Fetch temperature forecast data from Climate Engine API.
    Default coordinates are for Lincoln, Nebraska (approximate agricultural area).
    """
    if not CLIMATE_ENGINE_TOKEN:
        return {"error": "Climate Engine API token not configured"}
    
    headers = {
        "Authorization": f"Bearer {CLIMATE_ENGINE_TOKEN}",
        "Accept": "application/json"
    }
    
    # Use GridMET for temperature forecasts - 7 days ahead
    end_date = datetime.now() + timedelta(days=7)
    start_date = datetime.now()
    
    params = {
        "dataset": "GRIDMET",
        "variable": "tmmx",  # Maximum temperature
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d"),
        "lat": lat,
        "lon": lon
    }
    
    try:
        # Using timeseries endpoint for coordinate-based data
        url = f"{CLIMATE_ENGINE_BASE_URL}/timeseries/native/coordinates"
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        
        # Also get minimum temperature
        params["variable"] = "tmmn"
        resp_min = requests.get(url, headers=headers, params=params, timeout=30)
        resp_min.raise_for_status()
        min_data = resp_min.json()
        
        return {
            "max_temp": data,
            "min_temp": min_data,
            "location": {"lat": lat, "lon": lon},
            "dataset": "GRIDMET"
        }
    
    except Exception as e:
        return {"error": f"Error fetching Climate Engine data: {str(e)}"}

def get_cached_temperature_forecast(lat=40.8176, lon=-96.6917):
    """Get cached temperature forecast with TTL"""
    cache_key = f"temp_forecast_{lat}_{lon}.json"
    cache_file = cache_key
    
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                cached = json.load(f)
            ts = datetime.fromisoformat(cached["timestamp"])
            # Use longer TTL for forecast data (2 hours)
            if (datetime.now(timezone.utc) - ts) < timedelta(hours=2):
                return cached["data"]
        except Exception:
            pass

    fresh_forecast = fetch_climate_engine_forecast(lat, lon)
    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump({"timestamp": datetime.now(timezone.utc).isoformat(), "data": fresh_forecast}, f)
    except Exception:
        pass
    return fresh_forecast

# ----------------------------- table builder --------------------------------

def _build_table_rows(data: dict):
    """
    Produce rows for the dashboard table:
      Time | Temp (°F) | Precip (in) | Solar Rad (W/m²) | VPD (kPa) | Soil10 (%) | Soil20 (%)
    """
    keys = {
        "temp":   "Air Temperature",
        "precip": "Precipitation",
        "solar":  "Solar Radiation",
        "vpd":    "VPD",
        "soil10": "TEROS 12 Soil VWC @ 10cm",
        "soil20": "TEROS 12 Soil VWC @ 20cm",
    }

    temp_s   = _series(data, keys["temp"])
    precip_s = _series(data, keys["precip"])
    solar_s  = _series(data, keys["solar"])
    vpd_s    = _series(data, keys["vpd"])
    
    # Check for port-specific soil moisture data first
    soil10_s = _series(data, keys["soil10"]) 
    soil20_s = _series(data, keys["soil20"])
    
    # If no port-specific data, try to use generic Water Content
    if not soil10_s and not soil20_s:
        water_content = _series(data, "Water Content")
        if water_content:
            # If we have generic Water Content, use it for soil10 and leave soil20 empty
            soil10_s = water_content
            soil20_s = []

    # Choose base for alignment: Air Temp preferred, otherwise first non-empty
    bases = [s for s in (temp_s, precip_s, solar_s, vpd_s, soil10_s, soil20_s) if s]
    if not bases:
        return []

    base = bases[0]
    comp = [temp_s, precip_s, solar_s, vpd_s, soil10_s, soil20_s]
    min_len = min(len(s) if s else len(base) for s in comp + [base])

    rows = []
    for i in range(min_len):
        time_str = base[i].get("time")

        temp_f     = _to_f(  temp_s[i]["value"]   if i < len(temp_s)   and temp_s else None)
        precip_in  = _to_in( precip_s[i]["value"] if i < len(precip_s) and precip_s else None)
        solar      = float(  solar_s[i]["value"]  ) if i < len(solar_s)  and solar_s and solar_s[i].get("value") is not None else None
        vpd        = float(  vpd_s[i]["value"]    ) if i < len(vpd_s)    and vpd_s   and vpd_s[i].get("value")   is not None else None
        soil10_pct = _to_pct(soil10_s[i]["value"] if i < len(soil10_s)  and soil10_s else None)
        soil20_pct = _to_pct(soil20_s[i]["value"] if i < len(soil20_s)  and soil20_s else None)

        rows.append({
            "time": time_str,
            "temp_f": temp_f,
            "precip_in": precip_in,
            "solar_w_m2": solar,
            "vpd_kpa": vpd,
            "soil10_pct": soil10_pct,
            "soil20_pct": soil20_pct,
        })
    return rows

# --------------------------------- routes -----------------------------------

# Original API route (kept)
@app.route("/api/live/<device_sn>")
def api_live_device(device_sn):
    if device_sn != DEVICE_SN:
        return jsonify({"error": "Device not supported"}), 404
    return jsonify(get_cached_data())

# New table-friendly route
@app.route("/api/table/<device_sn>")
def api_table(device_sn):
    if device_sn != DEVICE_SN:
        return jsonify({"error": "Device not supported"}), 404
    try:
        data = get_cached_data()
        rows = _build_table_rows(data)
        return jsonify({
            "device_sn": device_sn,
            "count": len(rows),
            "units": {
                "temp_f": "°F",
                "precip_in": "in",
                "solar_w_m2": "W/m²",
                "vpd_kpa": "kPa",
                "soil10_pct": "%",
                "soil20_pct": "%"
            },
            "rows": rows
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 502

# ETO data route
@app.route("/api/eto/<device_sn>")
def api_eto(device_sn):
    if device_sn != DEVICE_SN:
        return jsonify({"error": "Device not supported"}), 404
    try:
        eto_data = get_cached_eto_data()
        return jsonify({
            "device_sn": device_sn,
            "count": len(eto_data),
            "data": eto_data
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 502

# Temperature forecast route
@app.route("/api/forecast/temperature")
def api_temperature_forecast():
    try:
        # Get coordinates from query parameters, default to Lincoln, NE
        lat = float(request.args.get('lat', 40.8176))
        lon = float(request.args.get('lon', -96.6917))
        
        forecast_data = get_cached_temperature_forecast(lat, lon)
        return jsonify({
            "forecast": forecast_data,
            "location": {"lat": lat, "lon": lon}
        })
    except ValueError:
        return jsonify({"error": "Invalid latitude or longitude"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 502

# Test Climate Engine API endpoint
@app.route("/api/test-climate-engine")
def test_climate_engine_api():
    """
    Simple test endpoint to verify Climate Engine API connectivity and authentication.
    """
    try:
        if not CLIMATE_ENGINE_TOKEN:
            return jsonify({"error": "Climate Engine API token not configured"}), 500
        
        headers = {
            "Authorization": f"Bearer {CLIMATE_ENGINE_TOKEN}",
            "Accept": "application/json"
        }
        
        # Simple test with just one day of GRIDMET data
        test_params = {
            "dataset": "GRIDMET",
            "variable": "eto",
            "start_date": "2024-10-01",  # Fixed known date
            "end_date": "2024-10-01",    # Same date
            "lat": 38.9069,
            "lon": -92.2808
        }
        
        url = f"{CLIMATE_ENGINE_BASE_URL}/timeseries/native/coordinates"
        print(f"TEST: URL: {url}")
        print(f"TEST: Parameters: {test_params}")
        print(f"TEST: Headers: {headers}")
        
        resp = requests.get(url, headers=headers, params=test_params, timeout=30)
        
        print(f"TEST: Response Status: {resp.status_code}")
        print(f"TEST: Response Headers: {dict(resp.headers)}")
        print(f"TEST: Response Text: {resp.text}")
        
        return jsonify({
            "status_code": resp.status_code,
            "response_headers": dict(resp.headers),
            "response_text": resp.text,
            "test_params": test_params,
            "url": url
        })
        
    except Exception as e:
        print(f"TEST ERROR: {str(e)}")
        return jsonify({"error": f"Test failed: {str(e)}"}), 500

# Precipitation and ETO forecast route
@app.route("/api/precipitation-eto-forecast")
def api_precipitation_eto_forecast():
    """
    Fetch precipitation and ETO forecast data from Climate Engine API.
    Uses the correct API structure based on working examples.
    """
    try:
        lat = float(request.args.get('lat', 38.9069))
        lon = float(request.args.get('lon', -92.2808))
        
        if not CLIMATE_ENGINE_TOKEN:
            return jsonify({"error": "Climate Engine API token not configured"}), 500
        
        headers = {
            "Authorization": f"Bearer {CLIMATE_ENGINE_TOKEN}",
            "Accept": "application/json"
        }
        
        # Coordinates format as array string (required by Climate Engine API)
        coordinates = [[-92.2808, 38.9069]]  # [lon, lat] format
        
        # Calculate date ranges
        today = datetime.now()
        historical_start = today - timedelta(days=5)
        forecast_end = today + timedelta(days=5)
        
        result_data = {}
        
        # Use proper Climate Engine API endpoint for timeseries data
        timeseries_url = f"{CLIMATE_ENGINE_BASE_URL}/timeseries/native/coordinates"
        forecast_url = f"{CLIMATE_ENGINE_BASE_URL}/timeseries/native/forecasts/coordinates"
        
        # Fetch historical ETO data (GRIDMET dataset)
        historical_eto_params = {
            "coordinates": str(coordinates),
            "simplify_geometry": 0,
            "buffer": None,
            "area_reducer": "mean",
            "dataset": "GRIDMET",
            "variable": ["eto"],  # As array
            "mask_image_id": None,
            "mask_band": None,
            "mask_value": None,
            "start_date": historical_start.strftime("%Y-%m-%d"),
            "end_date": today.strftime("%Y-%m-%d"),
            "export_path": None,
            "export_format": None
        }
        
        print(f"DEBUG: Historical ETO URL: {timeseries_url}")
        print(f"DEBUG: Historical ETO Params: {historical_eto_params}")
        
        eto_resp = requests.get(timeseries_url, headers=headers, params=historical_eto_params, timeout=30)
        print(f"DEBUG: Historical ETO Status: {eto_resp.status_code}")
        
        if eto_resp.status_code == 200:
            result_data['historical_eto'] = eto_resp.json()
            print(f"DEBUG: Historical ETO Success: {eto_resp.text[:200]}...")
        else:
            result_data['historical_eto_error'] = f"Status {eto_resp.status_code}: {eto_resp.text}"
            print(f"DEBUG: Historical ETO Error: {eto_resp.text}")
        
        # Fetch historical precipitation data (GRIDMET dataset)
        historical_precip_params = {
            "coordinates": str(coordinates),
            "simplify_geometry": 0,
            "buffer": None,
            "area_reducer": "mean", 
            "dataset": "GRIDMET",
            "variable": ["pr"],  # As array
            "mask_image_id": None,
            "mask_band": None,
            "mask_value": None,
            "start_date": historical_start.strftime("%Y-%m-%d"),
            "end_date": today.strftime("%Y-%m-%d"),
            "export_path": None,
            "export_format": None
        }
        
        print(f"DEBUG: Historical Precip Params: {historical_precip_params}")
        
        precip_resp = requests.get(timeseries_url, headers=headers, params=historical_precip_params, timeout=30)
        print(f"DEBUG: Historical Precip Status: {precip_resp.status_code}")
        
        if precip_resp.status_code == 200:
            result_data['historical_precipitation'] = precip_resp.json()
            print(f"DEBUG: Historical Precip Success: {precip_resp.text[:200]}...")
        else:
            result_data['historical_precipitation_error'] = f"Status {precip_resp.status_code}: {precip_resp.text}"
            print(f"DEBUG: Historical Precip Error: {precip_resp.text}")
        
        # Fetch forecast ETO data (CFS_GRIDMET dataset)
        forecast_eto_params = {
            "coordinates": str(coordinates),
            "area_reducer": "mean",
            "dataset": "CFS_GRIDMET", 
            "variable": "eto",  # Single variable for forecast
            "export_format": "json"
        }
        
        print(f"DEBUG: Forecast ETO URL: {forecast_url}")
        print(f"DEBUG: Forecast ETO Params: {forecast_eto_params}")
        
        forecast_eto_resp = requests.get(forecast_url, headers=headers, params=forecast_eto_params, timeout=30)
        print(f"DEBUG: Forecast ETO Status: {forecast_eto_resp.status_code}")
        
        if forecast_eto_resp.status_code == 200:
            result_data['forecast_eto'] = forecast_eto_resp.json()
            print(f"DEBUG: Forecast ETO Success: {forecast_eto_resp.text[:200]}...")
        else:
            result_data['forecast_eto_error'] = f"Status {forecast_eto_resp.status_code}: {forecast_eto_resp.text}"
            print(f"DEBUG: Forecast ETO Error: {forecast_eto_resp.text}")
        
        # Fetch forecast precipitation data (CFS_GRIDMET dataset)
        forecast_precip_params = {
            "coordinates": str(coordinates),
            "area_reducer": "mean",
            "dataset": "CFS_GRIDMET",
            "variable": "pr",  # Single variable for forecast
            "export_format": "json"
        }
        
        print(f"DEBUG: Forecast Precip Params: {forecast_precip_params}")
        
        forecast_precip_resp = requests.get(forecast_url, headers=headers, params=forecast_precip_params, timeout=30)
        print(f"DEBUG: Forecast Precip Status: {forecast_precip_resp.status_code}")
        
        if forecast_precip_resp.status_code == 200:
            result_data['forecast_precipitation'] = forecast_precip_resp.json()
            print(f"DEBUG: Forecast Precip Success: {forecast_precip_resp.text[:200]}...")
        else:
            result_data['forecast_precipitation_error'] = f"Status {forecast_precip_resp.status_code}: {forecast_precip_resp.text}"
            print(f"DEBUG: Forecast Precip Error: {forecast_precip_resp.text}")
        
        # Add rate limiting to prevent API overload
        time.sleep(0.5)
        
        return jsonify({
            "location": {"lat": lat, "lon": lon, "coordinates": coordinates},
            "data": result_data
        })
        
    except ValueError:
        return jsonify({"error": "Invalid latitude or longitude"}), 400
    except Exception as e:
        print(f"ERROR in precipitation-eto-forecast: {str(e)}")
        return jsonify({"error": f"Server error: {str(e)}"}), 500

# Combined data route (existing data + ETO + forecast)
@app.route("/api/combined/<device_sn>")
def api_combined(device_sn):
    if device_sn != DEVICE_SN:
        return jsonify({"error": "Device not supported"}), 404
    try:
        # Get coordinates from query parameters
        lat = float(request.args.get('lat', 40.8176))
        lon = float(request.args.get('lon', -96.6917))
        
        # Fetch all data
        sensor_data = get_cached_data()
        eto_data = get_cached_eto_data()
        forecast_data = get_cached_temperature_forecast(lat, lon)
        table_rows = _build_table_rows(sensor_data)
        
        return jsonify({
            "device_sn": device_sn,
            "sensor_data": sensor_data,
            "eto_data": eto_data,
            "temperature_forecast": forecast_data,
            "table_data": {
                "count": len(table_rows),
                "units": {
                    "temp_f": "°F",
                    "precip_in": "in",
                    "solar_w_m2": "W/m²",
                    "vpd_kpa": "kPa",
                    "soil10_pct": "%",
                    "soil20_pct": "%"
                },
                "rows": table_rows
            },
            "location": {"lat": lat, "lon": lon}
        })
    except ValueError:
        return jsonify({"error": "Invalid latitude or longitude"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 502

# ===================== APPEND-ONLY: multi-device endpoints =====================

# Four dataloggers
ALLOWED_DEVICE_SNS = [
    "z6-32396",  # Left Side Front
    "z6-20881",  # Left Side Back
    "z6-27574",  # Right Side Back
    "z6-27573",  # Right Side Front
]

_WC_LABEL_TOKENS = ("water content", "volumetric water content", "soil vwc", "vwc")
_MP_LABEL_TOKENS = ("matric potential", "water potential", "soil water potential")

def __label_is_wc(label: str) -> bool:
    if not isinstance(label, str): return False
    lo = label.lower()
    return any(tok in lo for tok in _WC_LABEL_TOKENS)

def __label_is_mp(label: str) -> bool:
    if not isinstance(label, str): return False
    lo = label.lower()
    return any(tok in lo for tok in _MP_LABEL_TOKENS)

def __reading_list(series):
    out = []
    for r in series.get("readings", []):
        v = r.get("value")
        try:
            v = float(v)
        except (TypeError, ValueError):
            pass
        out.append({"time": r.get("datetime"), "value": v})
    return out

def fetch_fresh_data_for(device_sn: str) -> dict:
    """
    Per-device fetch (last 24h) with port-aware mapping:
      VWC:  P1->10cm, P2->20cm, P4->10cm, P5->20cm
      MP :  P3->Matric Potential, P6->Matric Potential
      Soil Temp: P1->10cm, P2->20cm, P4->10cm, P5->20cm
      EC: P1->10cm, P2->20cm, P4->10cm, P5->20cm
    Also sets legacy keys for table builder:
      "TEROS 12 Soil VWC @ 10cm" and "TEROS 12 Soil VWC @ 20cm"
    """
    print(f"DEBUG: Fetching data for device {device_sn}")
    headers = {"Authorization": API_TOKEN, "Accept": "application/json"}
    now_utc = datetime.now(timezone.utc)
    params = {
        "device_sn": device_sn,
        "start_date": (now_utc - timedelta(hours=24)).strftime("%Y-%m-%d %H:%M"),
        "end_date": now_utc.strftime("%Y-%m-%d %H:%M"),
        "output_format": "json",
        "per_page": 1000,
    }
    print(f"DEBUG: Params: {params}")

    # Rate limiting - ensure at least 60 seconds between API calls
    rate_limit_file = f"rate_limit_{device_sn}.json"
    if os.path.exists(rate_limit_file):
        try:
            with open(rate_limit_file, "r") as f:
                last_call = json.load(f).get("last_call")
            if last_call:
                last_time = datetime.fromisoformat(last_call)
                time_diff = (datetime.now(timezone.utc) - last_time).total_seconds()
                if time_diff < 60:  # Less than 60 seconds
                    wait_time = 60 - time_diff
                    print(f"Rate limiting: waiting {wait_time:.1f} seconds for {device_sn}")
                    time.sleep(wait_time)
        except Exception:
            pass

    try:
        resp = requests.get(BASE_URL, headers=headers, params=params, timeout=20)
        print(f"DEBUG: Response status for {device_sn}: {resp.status_code}")
        
        # Record API call time for rate limiting
        try:
            with open(rate_limit_file, "w") as f:
                json.dump({"last_call": datetime.now(timezone.utc).isoformat()}, f)
        except Exception:
            pass
        
        resp.raise_for_status()
        raw = resp.json()
        print(f"DEBUG: Raw data keys for {device_sn}: {list(raw.get('data', {}).keys())}")
    except Exception as e:
        print(f"ERROR: Failed to fetch data for {device_sn}: {str(e)}")
        return {}

    data = raw.get("data", {})
    sensors = {}

    for label, series_list in data.items():
        label_lower = label.lower()
        
        # ---- Water Content / VWC ----
        if __label_is_wc(label):
            # For devices with multiple sensors, assign based on series index
            for i, series in enumerate(series_list):
                readings = __reading_list(series)
                # Map series index to logical ports (this is device-specific)
                if i == 0:  # First VWC sensor -> P1 (10cm)
                    sensors["TEROS 12 Soil VWC @ 10cm (P1)"] = readings
                    sensors["TEROS 12 Soil VWC @ 10cm"] = readings  # legacy for table
                elif i == 1:  # Second VWC sensor -> P2 (20cm)
                    sensors["TEROS 12 Soil VWC @ 20cm (P2)"] = readings
                    sensors["TEROS 12 Soil VWC @ 20cm"] = readings  # legacy for table
                elif i == 2:  # Third VWC sensor -> P4 (10cm)
                    sensors["TEROS 12 Soil VWC @ 10cm (P4)"] = readings
                elif i == 3:  # Fourth VWC sensor -> P5 (20cm)
                    sensors["TEROS 12 Soil VWC @ 20cm (P5)"] = readings
                else:
                    sensors.setdefault("Water Content", []).extend(readings)
            continue

        # ---- Soil Temperature ----
        if "soil temperature" in label_lower:
            for i, series in enumerate(series_list):
                readings = __reading_list(series)
                # Map series index to logical ports
                if i == 0:  # First temp sensor -> P1 (10cm)
                    sensors["TEROS 12 Soil Temperature @ 10cm (P1)"] = readings
                elif i == 1:  # Second temp sensor -> P2 (20cm)
                    sensors["TEROS 12 Soil Temperature @ 20cm (P2)"] = readings
                elif i == 2:  # Third temp sensor -> P4 (10cm)
                    sensors["TEROS 12 Soil Temperature @ 10cm (P4)"] = readings
                elif i == 3:  # Fourth temp sensor -> P5 (20cm)
                    sensors["TEROS 12 Soil Temperature @ 20cm (P5)"] = readings
                else:
                    sensors.setdefault("Soil Temperature", []).extend(readings)
            continue

        # ---- Electrical Conductivity ----
        if "electrical conductivity" in label_lower or "saturation extract ec" in label_lower or "ec" in label_lower:
            for i, series in enumerate(series_list):
                readings = __reading_list(series)
                # Map series index to logical ports
                if i == 0:  # First EC sensor -> P1 (10cm)
                    sensors["TEROS 12 Electrical Conductivity @ 10cm (P1)"] = readings
                elif i == 1:  # Second EC sensor -> P2 (20cm)
                    sensors["TEROS 12 Electrical Conductivity @ 20cm (P2)"] = readings
                elif i == 2:  # Third EC sensor -> P4 (10cm)
                    sensors["TEROS 12 Electrical Conductivity @ 10cm (P4)"] = readings
                elif i == 3:  # Fourth EC sensor -> P5 (20cm)
                    sensors["TEROS 12 Electrical Conductivity @ 20cm (P5)"] = readings
                else:
                    sensors.setdefault("Electrical Conductivity", []).extend(readings)
            continue

        # ---- Matric Potential (TEROS 21) ----
        if __label_is_mp(label):
            for i, series in enumerate(series_list):
                readings = __reading_list(series)
                # Map series index to logical ports (matric potential sensors)
                if i == 0:  # First MP sensor -> P3
                    sensors["TEROS 21 Matric Potential (P3)"] = readings
                elif i == 1:  # Second MP sensor -> P6
                    sensors["TEROS 21 Matric Potential (P6)"] = readings
                else:
                    sensors.setdefault("Matric Potential", []).extend(readings)
            continue

        # ---- Default passthrough ----
        readings = []
        for series in series_list:
            readings.extend(__reading_list(series))
        sensors[label] = readings

    return sensors

def get_cached_data_for(device_sn: str) -> dict:
    """
    Per-device cache; does NOT alter your existing global cache file.
    """
    cache_file = f"data_cache_{device_sn}.json"
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                cached = json.load(f)
            ts = datetime.fromisoformat(cached["timestamp"])
            if (datetime.now(timezone.utc) - ts) < timedelta(minutes=CACHE_TTL_MINUTES):
                return cached["data"]
        except Exception:
            pass

    fresh = fetch_fresh_data_for(device_sn)
    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump({"timestamp": datetime.now(timezone.utc).isoformat(), "data": fresh}, f)
    except Exception:
        pass
    return fresh

def __latest(series):
    return series[-1] if isinstance(series, list) and series else None

def __latest_row(rows):
    if not isinstance(rows, list) or not rows:
        return None
    def parse_iso(s):
        try:
            return datetime.fromisoformat(s)
        except Exception:
            return None
    ts_rows = [(parse_iso(r.get("time")), r) for r in rows if isinstance(r, dict)]
    ts_rows = [x for x in ts_rows if x[0] is not None]
    if ts_rows:
        ts_rows.sort(key=lambda x: x[0])
        return ts_rows[-1][1]
    return rows[-1]

def __percent_series(series):
    out = []
    for p in series or []:
        pct = _to_pct(p.get("value"))
        if pct is not None:
            out.append({"time": p.get("time"), "value_pct": pct})
    return out

def get_soil_moistvals_for_data(data: dict):
    """
    Returns aggregate 'moistval' from table-legacy keys:
      latest soil10_pct / soil20_pct and their average.
    """
    s10_raw = _series(data, "TEROS 12 Soil VWC @ 10cm") or _series(data, "Water Content")
    s20_raw = _series(data, "TEROS 12 Soil VWC @ 20cm")

    s10 = __percent_series(s10_raw)
    s20 = __percent_series(s20_raw)

    latest10 = s10[-1] if s10 else None
    latest20 = s20[-1] if s20 else None

    latest_time = latest10["time"] if latest10 else (latest20["time"] if latest20 else None)
    latest_avg = None
    if latest10 and latest20:
        latest_avg = round((latest10["value_pct"] + latest20["value_pct"]) / 2.0, 1)
    elif latest10:
        latest_avg = latest10["value_pct"]
    elif latest20:
        latest_avg = latest20["value_pct"]

    return {
        "latest": {
            "time": latest_time,
            "soil10_pct": latest10["value_pct"] if latest10 else None,
            "soil20_pct": latest20["value_pct"] if latest20 else None,
            "avg_pct": latest_avg,
        }
    }

def get_port_quick_values_for_data(data: dict):
    """Quick latest values per port: VWC in %, WP in kPa, Temp in °C, EC in µS/cm."""
    out = {}

    def latest_val_pct(label):
        lp = __latest(_series(data, label))
        return _to_pct(lp["value"]) if lp and lp.get("value") is not None else None

    def latest_val_float(label):
        lp = __latest(_series(data, label))
        try:
            return float(lp["value"]) if lp and lp.get("value") is not None else None
        except (TypeError, ValueError):
            return None

    # Port 1 (10cm depth)
    out["P1_vwc10_pct"] = latest_val_pct("TEROS 12 Soil VWC @ 10cm (P1)")
    out["P1_temp10_c"] = latest_val_float("TEROS 12 Soil Temperature @ 10cm (P1)")
    out["P1_ec10_us_cm"] = latest_val_float("TEROS 12 Electrical Conductivity @ 10cm (P1)")
    
    # Port 2 (20cm depth)
    out["P2_vwc20_pct"] = latest_val_pct("TEROS 12 Soil VWC @ 20cm (P2)")
    out["P2_temp20_c"] = latest_val_float("TEROS 12 Soil Temperature @ 20cm (P2)")
    out["P2_ec20_us_cm"] = latest_val_float("TEROS 12 Electrical Conductivity @ 20cm (P2)")
    
    # Port 3 (Matric Potential)
    out["P3_wp_kpa"] = latest_val_float("TEROS 21 Matric Potential (P3)")
    
    # Port 4 (10cm depth)
    out["P4_vwc10_pct"] = latest_val_pct("TEROS 12 Soil VWC @ 10cm (P4)")
    out["P4_temp10_c"] = latest_val_float("TEROS 12 Soil Temperature @ 10cm (P4)")
    out["P4_ec10_us_cm"] = latest_val_float("TEROS 12 Electrical Conductivity @ 10cm (P4)")
    
    # Port 5 (20cm depth)
    out["P5_vwc20_pct"] = latest_val_pct("TEROS 12 Soil VWC @ 20cm (P5)")
    out["P5_temp20_c"] = latest_val_float("TEROS 12 Soil Temperature @ 20cm (P5)")
    out["P5_ec20_us_cm"] = latest_val_float("TEROS 12 Electrical Conductivity @ 20cm (P5)")
    
    # Port 6 (Matric Potential)
    out["P6_wp_kpa"] = latest_val_float("TEROS 21 Matric Potential (P6)")
    
    return out

# ---- New endpoints (do not modify your existing ones) ----

@app.route("/api/soil/<device_sn>")
def api_soil_new(device_sn):
    if device_sn not in ALLOWED_DEVICE_SNS:
        return jsonify({"error": "Device not supported"}), 404
    data = get_cached_data_for(device_sn)
    moist = get_soil_moistvals_for_data(data)
    return jsonify({
        "device_sn": device_sn,
        "latest": moist["latest"],
        "units": {"soil_pct": "%"}
    })

@app.route("/api/combined_all")
def api_combined_all():
    """
    One call for all 4 devices:
      - latest 'table-like' row values (temp_f, precip_in, solar_w_m2, vpd_kpa, soil10/20 %)
      - moistval aggregate (soil10/20 and avg)
      - per-port quick values (P1..P6)
    Uses your existing _build_table_rows for the 'table-like' part.
    """
    devices = []
    for sn in ALLOWED_DEVICE_SNS:
        try:
            # Per-device normalized data
            data = get_cached_data_for(sn)

            # Table-like latest row from your existing builder (reuses conversion helpers)
            rows = _build_table_rows(data)
            latest = __latest_row(rows) or {}

            # Moistval aggregate + port quick snapshot
            moist = get_soil_moistvals_for_data(data)
            ports = get_port_quick_values_for_data(data)

            devices.append({
                "device_sn": sn,
                "latest": latest,       # includes time, temp_f, precip_in, solar_w_m2, vpd_kpa, soil10_pct, soil20_pct
                "soil": moist,          # { latest: { soil10_pct, soil20_pct, avg_pct, time } }
                "ports": ports          # { P1_vwc10_pct, P2_vwc20_pct, P3_wp_kpa, P4_vwc10_pct, P5_vwc20_pct, P6_wp_kpa }
            })
        except Exception as e:
            devices.append({"device_sn": sn, "error": str(e)})

    return jsonify({"count": len(devices), "devices": devices})
# =================== END APPEND-ONLY (leave your code above intact) ===================


if __name__ == "__main__":
    app.run(debug=True)
