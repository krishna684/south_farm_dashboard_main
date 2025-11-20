#!/usr/bin/env python3
"""
Debug script to check what data is available for device z6-27574
"""

import os
import requests
import json
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv()

API_TOKEN = os.getenv("ZENTRA_API_TOKEN")
BASE_URL = "https://zentracloud.com/api/v3/get_readings/"

def debug_device(device_sn):
    headers = {"Authorization": API_TOKEN, "Accept": "application/json"}
    now_utc = datetime.now(timezone.utc)
    params = {
        "device_sn": device_sn,
        "start_date": (now_utc - timedelta(hours=24)).strftime("%Y-%m-%d %H:%M"),
        "end_date": now_utc.strftime("%Y-%m-%d %H:%M"),
        "output_format": "json",
        "per_page": 1000,
    }
    
    print(f"Debugging device: {device_sn}")
    print(f"Date range: {params['start_date']} to {params['end_date']}")
    
    try:
        resp = requests.get(BASE_URL, headers=headers, params=params, timeout=20)
        print(f"Response status: {resp.status_code}")
        
        if resp.status_code != 200:
            print(f"Error response: {resp.text}")
            return
        
        raw = resp.json()
        data = raw.get("data", {})
        
        print(f"Available data series: {len(data)}")
        
        if not data:
            print("No data series found!")
            return
        
        for label, series_list in data.items():
            print(f"\nSeries: {label}")
            print(f"   Count: {len(series_list)} series")
            
            for i, series in enumerate(series_list):
                readings = series.get("readings", [])
                metadata = series.get("metadata", {})
                
                print(f"   Series {i+1}:")
                print(f"     Readings: {len(readings)}")
                print(f"     Metadata: {metadata}")
                
                # Try to detect port
                port = None
                for key in ("port", "port_num", "source_port", "channel", "port_number"):
                    if key in series and series[key] is not None:
                        port = series[key]
                        break
                
                if not port:
                    # Check labels for port info
                    for field in ("series_label", "label", "name", "sensor_name", "series_name"):
                        val = series.get(field)
                        if isinstance(val, str) and ("port" in val.lower() or "p" in val.lower()):
                            print(f"     Label hint: {val}")
                
                print(f"     Detected port: {port}")
                
                if readings:
                    latest = readings[-1]
                    print(f"     Latest reading: {latest.get('datetime')} = {latest.get('value')}")
                    
                    # Show first few readings
                    print(f"     Sample readings:")
                    for j, reading in enumerate(readings[:3]):
                        print(f"       {j+1}: {reading.get('datetime')} = {reading.get('value')}")
    
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    # Debug all devices
    devices = ["z6-32396", "z6-20881", "z6-27574", "z6-27573"]
    
    for device in devices:
        debug_device(device)
        print("\n" + "="*60 + "\n")