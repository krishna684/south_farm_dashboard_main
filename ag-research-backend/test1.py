# app.py
# One-file Flask backend with a new endpoint:
#   GET /api/table/<device_sn>
# Returns table-ready rows for:
#   Time | Temp (°F) | Precip (in) | Solar Rad (W/m²) | VPD (kPa) | Soil10 (%) | Soil20 (%)
#
# Env (.env or environment):
#   ZENTRA_API_TOKEN=...      # REQUIRED
#   ZENTRA_DEVICE_SN=z6-23000 # optional (default shown)
#   CACHE_TTL_MINUTES=10      # optional
#
# Run:
#   pip install flask flask-cors python-dotenv requests
#   python app.py
#
# Test:
#   http://127.0.0.1:5000/api/table/z6-23000

import os
import re
import json
from math import isfinite
from datetime import datetime, timedelta, timezone

import requests
from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# -----------------------------------------------------------------------------
# Config
# -----------------------------------------------------------------------------
load_dotenv()

API_TOKEN = os.getenv("ZENTRA_API_TOKEN", "").strip()
DEVICE_SN = os.getenv("ZENTRA_DEVICE_SN", "z6-23000").strip()
CACHE_TTL_MINUTES = int(os.getenv("CACHE_TTL_MINUTES", "10"))
CACHE_FILE = "data_cache.json"

ZENTRA_URL = "https://zentracloud.com/api/v3/get_readings/"

app = Flask(__name__)
CORS(app)  # keep wide-open for now (dev)

# -----------------------------------------------------------------------------
# Helpers: label/port detection and conversions
# -----------------------------------------------------------------------------

_WC_LABEL_TOKENS = (
    "water content",
    "volumetric water content",
    "soil vwc",
    "vwc",
)

def _is_water_content_label(label: str) -> bool:
    if not isinstance(label, str):
        return False
    lo = label.lower()
    return any(tok in lo for tok in _WC_LABEL_TOKENS)

def _series_port(series: dict):
    """Try to extract Port 1/2 from common fields or from label text."""
    # numeric-ish direct fields
    for key in ("port", "port_num", "source_port", "channel", "port_number"):
        if key in series and series[key] is not None:
            try:
                return int(series[key])
            except (TypeError, ValueError):
                pass

    # nested dicts sometimes exist
    for nest in ("sensor", "metadata", "source", "info"):
        sub = series.get(nest)
        if isinstance(sub, dict):
            for key in ("port", "port_num", "source_port", "channel", "port_number"):
                if key in sub and sub[key] is not None:
                    try:
                        return int(sub[key])
                    except (TypeError, ValueError):
                        pass

    # parse possible strings like "Port 1", "(Port 2)", "P2", "Ch 1"
    label_fields = ("series_label", "label", "name", "sensor_name", "series_name", "title")
    port_regexes = [
        re.compile(r"(?:port|p)\s*[:#]?\s*(\d+)", re.IGNORECASE),
        re.compile(r"\(.*port\s*(\d+).*\)", re.IGNORECASE),
        re.compile(r"\bch(?:annel)?\s*[:#]?\s*(\d+)", re.IGNORECASE),
        re.compile(r"\b(\d+)\s*cm\b", re.IGNORECASE),  # sometimes depth shows up
    ]
    for lf in label_fields:
        val = series.get(lf)
        if isinstance(val, str):
            for rgx in port_regexes:
                m = rgx.search(val)
                if m:
                    try:
                        return int(m.group(1))
                    except ValueError:
                        pass
    return None

def _reading_list(series):
    out = []
    for r in series.get("readings", []):
        v = r.get("value")
        try:
            v = float(v)
        except (TypeError, ValueError):
            pass
        out.append({"time": r.get("datetime"), "value": v})
    return out

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

# -----------------------------------------------------------------------------
# Fetch + normalize + cache
# -----------------------------------------------------------------------------

def fetch_fresh_data() -> dict:
    """Fetch last 24h from Zentra and normalize into label -> [{time, value}, ...]."""
    if not API_TOKEN:
        raise RuntimeError("ZENTRA_API_TOKEN is not set")

    now_utc = datetime.now(timezone.utc)
    params = {
        "device_sn": DEVICE_SN,
        "start_date": (now_utc - timedelta(hours=24)).strftime("%Y-%m-%d %H:%M"),
        "end_date": now_utc.strftime("%Y-%m-%d %H:%M"),
        "output_format": "json",
        "per_page": 1000,
    }

    # Your app previously sent Authorization as the raw token; keep that behavior
    headers = {
        "Authorization": API_TOKEN,
        "Accept": "application/json",
    }

    resp = requests.get(ZENTRA_URL, headers=headers, params=params, timeout=20)
    resp.raise_for_status()
    raw = resp.json()

    data = raw.get("data", {})
    sensors = {}

    for label, series_list in data.items():
        if _is_water_content_label(label):
            # Split Water Content/VWC by port → 10cm (Port 1) and 20cm (Port 2)
            for series in series_list:
                p = _series_port(series)
                readings = _reading_list(series)

                if p == 1:
                    sensors["TEROS 12 Soil VWC @ 10cm"] = readings
                elif p == 2:
                    sensors["TEROS 12 Soil VWC @ 20cm"] = readings
                else:
                    sensors.setdefault("Water Content", []).extend(readings)
        else:
            readings = []
            for series in series_list:
                readings.extend(_reading_list(series))
            sensors[label] = readings

    return sensors

def get_cached_data() -> dict:
    """Return cached data if fresh; otherwise fetch and update cache."""
    # Use cache if within TTL
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                cached = json.load(f)
            ts = datetime.fromisoformat(cached["timestamp"])
            if (datetime.now(timezone.utc) - ts) < timedelta(minutes=CACHE_TTL_MINUTES):
                return cached["data"]
        except Exception:
            pass

    # Otherwise fetch and cache
    fresh = fetch_fresh_data()
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump({"timestamp": datetime.now(timezone.utc).isoformat(), "data": fresh}, f)
    except Exception:
        pass
    return fresh

# -----------------------------------------------------------------------------
# Build table rows for the new endpoint
# -----------------------------------------------------------------------------

def _build_table_rows(data: dict):
    """
    Produce rows for:
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
    # If port-splitting didn't hit yet, fall back to generic Water Content for soil10
    soil10_s = _series(data, keys["soil10"]) or _series(data, "Water Content")
    soil20_s = _series(data, keys["soil20"])

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

# -----------------------------------------------------------------------------
# Routes
# -----------------------------------------------------------------------------

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

@app.route("/healthz")
def healthz():
    return jsonify({"ok": True, "time": datetime.now(timezone.utc).isoformat()})

# -----------------------------------------------------------------------------

if __name__ == "__main__":
    # Dev server
    app.run(host="127.0.0.1", port=5000, debug=True)
