#!/usr/bin/env python3
import os
import requests
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import json

load_dotenv()
API_TOKEN = os.getenv('ZENTRA_API_TOKEN')
DEVICE_SN = 'z6-32396'  # Left Side Front (force this device)
BASE_URL = 'https://zentracloud.com/api/v3/get_readings/'

headers = {
    'Authorization': API_TOKEN,
    'Accept': 'application/json'
}
now_utc = datetime.now(timezone.utc)
params = {
    'device_sn': DEVICE_SN,
    'start_date': (now_utc - timedelta(hours=2)).strftime('%Y-%m-%d %H:%M'),
    'end_date': now_utc.strftime('%Y-%m-%d %H:%M'),
    'output_format': 'json',
    'per_page': 100
}

print(f"Fetching data for device: {DEVICE_SN}")
resp = requests.get(BASE_URL, headers=headers, params=params, timeout=15)
print(f"Response status code: {resp.status_code}")
raw_data = resp.json()
print("Raw response keys:", list(raw_data.keys()))

data = raw_data.get('data', {})
print(f"Data keys count: {len(data)}")
print("All available series:", list(data.keys()))

if 'Water Content' in data:
    print('\n=== Water Content series found ===')
    series_list = data['Water Content']
    for i, series in enumerate(series_list):
        print(f'Series {i+1}:')
        for key, value in series.items():
            if key != 'readings':  # Skip readings to focus on metadata
                print(f'  {key}: {value}')
        readings_count = len(series.get('readings', []))
        print(f'  readings_count: {readings_count}')
        print()
else:
    print('No Water Content series found')
    
    # Check if we have any data at all
    if data:
        # Show a sample of what we do have
        for series_name in list(data.keys())[:3]:  # Show first 3 series
            print(f"\n=== {series_name} series sample ===")
            if data[series_name]:
                series = data[series_name][0] if isinstance(data[series_name], list) else data[series_name]
                print(f"  Type: {type(series)}")
                if hasattr(series, 'keys'):
                    for key in series.keys():
                        if key != 'readings':
                            print(f"  {key}: {series[key]}")
                    readings_count = len(series.get('readings', []))
                    print(f"  readings_count: {readings_count}")
                    if readings_count > 0:
                        print(f"  sample reading: {series['readings'][0]}")
    else:
        print("No data returned at all")