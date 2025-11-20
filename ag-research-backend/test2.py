# app.py
# Backend providing ONE-CALL endpoint that returns data for ALL 4 dataloggers.
#
# Endpoints you can use:
#   GET /api/combined_all                -> one call returns latest table + soil + per-port quick values for all 4 SNs
#   (also available for debugging)
#   GET /api/live/<device_sn>            -> normalized raw series (cached per device)
#   GET /api/table/<device_sn>           -> table-ready rows (Temp°F, Precip in, Solar W/m², VPD kPa, Soil10/20 %)
#   GET /api/soil/<device_sn>            -> soil moisture “moistval” (latest + percent conversion)
#   GET /healthz
#
# .env (same folder):
#   ZENTRA_API_TOKEN=YOUR_TOKEN
#   CACHE_TTL_MINUTES=10
#   WEATHER_STATION_URL=https://example.com/your-weather-station   (optional)
#
# Run:
#   pip install flask flask-cors python-dotenv requests
#   python app.py
#
# Notes:
# - Caches are per device: data_cache_<SN>.json
# - Water Content (VWC) is split by ports:
#     P1 -> TEROS 12 Soil VWC @ 10cm (P1)   (+ legacy key "TEROS 12 Soil VWC @ 10cm")
#     P2 -> TEROS 12 Soil VWC @ 20cm (P2)   (+ legacy key "TEROS 12 Soil VWC @ 20cm")
#     P4 -> TEROS 12 Soil VWC @ 10cm (P4)
#     P5 -> TEROS 12 Soil VWC @ 20cm (P5)
# - Matric Potential (TEROS 21):
#     P3 -> TEROS 21 Matric Potential (P3)
#     P6 -> TEROS 21 Matric Potential (P6)

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
CACHE_TTL_MINUTES = int(os.getenv("CACHE_TTL_MINUTES", "10"))
WEATHER_STATION_URL = os.getenv("WEATHER_STATION_URL", "").strip()

BASE_URL = "https://zentracloud.com/api/v3/get_readings/"

# Your four dataloggers
ALLOWED_DEVICE_SNS = [
    "z6-32396",  # Left Side Front
    "z6-20881",  # Left Side Back
    "z6-27574",  # Right Side Back
    "z6-27573",  # Right Side Front
]

app = Flask(__name__)
CORS(app)

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

_WC_LABEL_TOKENS = (
    "water content",
    "volumetric water content",
    "soil vwc",
    "vwc",
)

_MP_LABEL_TOKENS = (
    "matric potential",
    "water potential",
    "soil water potential",
)

def _is_water_content_label(label: str) -> bool:
    if not isinstance(label, str):
        return False
    lo = label.lower()
    return any(tok in lo for tok in _WC_LABEL_TOKENS)

def _is_matric_potential_label(label: str) -> bool:
    if not isinstance(label, str):
        return False
    lo = label.lower()
    return any(tok in lo for tok in _MP_LABEL_TOKENS)

def _series_port(series: dict):
    """Return int port number if we can infer it, else None."""
    for key in ("port", "port_num", "source_port", "channel", "port_number"):
        if key in series and series[key] is not None:
            try:
                return int(series[key])
            except (TypeError, ValueError):
                pass

    for nest in ("sensor", "metadata", "source", "info"):
        sub = series.get(nest)
        if isinstance(sub, dict):
            for key in ("port", "port_num", "source_port", "channel", "port_number"):
                if key in sub and sub[key] is not None:
                    try:
                        return int(sub[key])
                    except (TypeError, ValueError):
                        pass

    label_fields = ("series_label", "label", "name", "sensor_name", "series_name", "title")
    port_regexes = [
        re.compile(r"(?:port|p)\s*[:#]?\s*(\d+)", re.IGNORECASE),
        re.compile(r"\(.*port\s*(\d+).*\)", re.IGNORECASE),
        re.compile(r"\bch(?:annel)?\s*[:#]?\s*(\d+)", re.IGNORECASE),
        re.compile(r"\b(\d+)\s*cm\b", re.IGNORECASE),
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
    """Safe getter for series list by label (case variants allowed)."""
    return data.get(key) or data.get(key.title()) or []

def _latest(series):
    return series[-1] if isinstance(series, list) and series else None

def _latest_row(rows):
    """Pick the most recent row by parsing the 'time' field when possible."""
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
    # fallback: last element
    return rows[-1]

# -----------------------------------------------------------------------------
# Fetch + normalize + cache (per device)
# -----------------------------------------------------------------------------

def fetch_fresh_data(device_sn: str) -> dict:
    """Fetch last 24h for a device and normalize into label -> [{time, value}, ...]."""
    if not API_TOKEN:
        raise RuntimeError("ZENTRA_API_TOKEN is not set")

    now_utc = datetime.now(timezone.utc)
    params = {
        "device_sn": device_sn,
        "start_date": (now_utc - timedelta(hours=24)).strftime("%Y-%m-%d %H:%M"),
        "end_date": now_utc.strftime("%Y-%m-%d %H:%M"),
        "output_format": "json",
        "per_page": 1000,
    }
    headers = {"Authorization": API_TOKEN, "Accept": "application/json"}

    resp = requests.get(BASE_URL, headers=headers, params=params, timeout=20)
    resp.raise_for_status()
    raw = resp.json()

    data = raw.get("data", {})
    sensors = {}

    for label, series_list in data.items():
        # ---- Water Content / VWC ----
        if _is_water_content_label(label):
            for series in series_list:
                p = _series_port(series)
                readings = _reading_list(series)
                if p == 1:
                    sensors["TEROS 12 Soil VWC @ 10cm (P1)"] = readings
                    sensors["TEROS 12 Soil VWC @ 10cm"] = readings  # legacy table key
                elif p == 2:
                    sensors["TEROS 12 Soil VWC @ 20cm (P2)"] = readings
                    sensors["TEROS 12 Soil VWC @ 20cm"] = readings  # legacy table key
                elif p == 4:
                    sensors["TEROS 12 Soil VWC @ 10cm (P4)"] = readings
                elif p == 5:
                    sensors["TEROS 12 Soil VWC @ 20cm (P5)"] = readings
                else:
                    sensors.setdefault("Water Content", []).extend(readings)
            continue

        # ---- Matric Potential (TEROS 21) ----
        if _is_matric_potential_label(label):
            for series in series_list:
                p = _series_port(series)
                readings = _reading_list(series)
                if p == 3:
                    sensors["TEROS 21 Matric Potential (P3)"] = readings
                elif p == 6:
                    sensors["TEROS 21 Matric Potential (P6)"] = readings
                else:
                    sensors.setdefault("Matric Potential", []).extend(readings)
            continue

        # ---- Default: aggregate by label ----
        readings = []
        for series in series_list:
            readings.extend(_reading_list(series))
        sensors[label] = readings

    return sensors

def get_cached_data(device_sn: str) -> dict:
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
    fresh = fetch_fresh_data(device_sn)
    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump({"timestamp": datetime.now(timezone.utc).isoformat(), "data": fresh}, f)
    except Exception:
        pass
    return fresh

# -----------------------------------------------------------------------------
# Table rows + soil moistval
# -----------------------------------------------------------------------------

def _build_table_rows(data: dict):
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
    soil10_s = _series(data, keys["soil10"]) or _series(data, "Water Content")
    soil20_s = _series(data, keys["soil20"])

    bases = [s for s in (temp_s, precip_s, solar_s, vpd_s, soil10_s, soil20_s) if s]
    if not bases:
        return []
    base = bases[0]
    comp = [temp_s, precip_s, solar_s, vpd_s, soil10_s, soil20_s]
    min_len = min(len(s) if s else len(base) for s in comp + [base])

    rows = []
    for i in range(min_len):
        time_str   = base[i].get("time")
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

def _percent_series(series):
    out = []
    for p in series or []:
        pct = _to_pct(p.get("value"))
        if pct is not None:
            out.append({"time": p.get("time"), "value_pct": pct})
    return out

def get_soil_moistvals(data: dict):
    s10_raw = _series(data, "TEROS 12 Soil VWC @ 10cm") or _series(data, "Water Content")
    s20_raw = _series(data, "TEROS 12 Soil VWC @ 20cm")

    s10 = _percent_series(s10_raw)
    s20 = _percent_series(s20_raw)

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

def get_port_quick_values(data: dict):
    """Return quick latest values per port (VWC in %, WP in kPa)."""
    out = {}

    def latest_val_pct(label):
        lp = _latest(_series(data, label))
        return _to_pct(lp["value"]) if lp and lp.get("value") is not None else None

    def latest_val_float(label):
        lp = _latest(_series(data, label))
        try:
            return float(lp["value"]) if lp and lp.get("value") is not None else None
        except (TypeError, ValueError):
            return None

    out["P1_vwc10_pct"] = latest_val_pct("TEROS 12 Soil VWC @ 10cm (P1)")
    out["P2_vwc20_pct"] = latest_val_pct("TEROS 12 Soil VWC @ 20cm (P2)")
    out["P3_wp_kpa"]    = latest_val_float("TEROS 21 Matric Potential (P3)")
    out["P4_vwc10_pct"] = latest_val_pct("TEROS 12 Soil VWC @ 10cm (P4)")
    out["P5_vwc20_pct"] = latest_val_pct("TEROS 12 Soil VWC @ 20cm (P5)")
    out["P6_wp_kpa"]    = latest_val_float("TEROS 21 Matric Potential (P6)")
    return out

# -----------------------------------------------------------------------------
# Routes (single-call + debug)
# -----------------------------------------------------------------------------

@app.route("/api/combined_all")
def api_combined_all():
    """One call: returns latest table + soil + per-port quick values for all 4 loggers."""
    devices = []
    for sn in ALLOWED_DEVICE_SNS:
        try:
            sensor_data = get_cached_data(sn)
            table_rows = _build_table_rows(sensor_data)
            latest_row = _latest_row(table_rows) or {}
            soil = get_soil_moistvals(sensor_data)
            ports = get_port_quick_values(sensor_data)

            devices.append({
                "device_sn": sn,
                "latest": latest_row,           # includes temp_f, precip_in, solar_w_m2, vpd_kpa, soil10_pct, soil20_pct, time
                "soil": soil,                   # { latest: { soil10_pct, soil20_pct, avg_pct, time } }
                "ports": ports,                 # P1..P6 quick values (VWC % or WP kPa)
                "links": {"zentracloud": f"https://zentracloud.com/devices/{sn}"}
            })
        except Exception as e:
            devices.append({"device_sn": sn, "error": str(e)})

    payload = {"count": len(devices), "devices": devices}
    if WEATHER_STATION_URL:
        payload["weather_station"] = {"external_url": WEATHER_STATION_URL}
    return jsonify(payload)

# ---- Debug/optional endpoints (still handy if you want to test per device) ---

@app.route("/api/live/<device_sn>")
def api_live_device(device_sn):
    if device_sn not in ALLOWED_DEVICE_SNS:
        return jsonify({"error": "Device not supported"}), 404
    return jsonify(get_cached_data(device_sn))

@app.route("/api/table/<device_sn>")
def api_table(device_sn):
    if device_sn not in ALLOWED_DEVICE_SNS:
        return jsonify({"error": "Device not supported"}), 404
    data = get_cached_data(device_sn)
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

@app.route("/api/soil/<device_sn>")
def api_soil(device_sn):
    if device_sn not in ALLOWED_DEVICE_SNS:
        return jsonify({"error": "Device not supported"}), 404
    data = get_cached_data(device_sn)
    moist = get_soil_moistvals(data)
    return jsonify({
        "device_sn": device_sn,
        "latest": moist["latest"],
        "units": {"soil_pct": "%"}
    })

@app.route("/healthz")
def healthz():
    return jsonify({"ok": True, "time": datetime.now(timezone.utc).isoformat()})

# -----------------------------------------------------------------------------

if __name__ == "__main__":
    # Start dev server
    app.run(host="127.0.0.1", port=5000, debug=True)
