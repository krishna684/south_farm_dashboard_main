#!/usr/bin/env python3
"""
Test script to verify the new sensor data structure is working correctly.
This script tests the /api/combined_all endpoint to ensure all sensor data is being fetched properly.
"""

import requests
import json
from datetime import datetime

def test_combined_all_endpoint():
    """Test the /api/combined_all endpoint"""
    try:
        print("Testing /api/combined_all endpoint...")
        response = requests.get("http://127.0.0.1:5000/api/combined_all", timeout=30)
        
        if response.status_code != 200:
            print(f"Error: HTTP {response.status_code}")
            print(f"Response: {response.text}")
            return False
        
        data = response.json()
        print(f"Successfully fetched data for {data.get('count', 0)} devices")
        
        # Check each device
        for device in data.get('devices', []):
            device_sn = device.get('device_sn')
            print(f"\nDevice: {device_sn}")
            
            if 'error' in device:
                print(f"  Error: {device['error']}")
                continue
            
            # Check latest data
            latest = device.get('latest', {})
            if latest:
                print(f"  Last update: {latest.get('time', 'Unknown')}")
                if latest.get('temp_f'):
                    print(f"  Temperature: {latest['temp_f']:.1f}F")
                if latest.get('soil10_pct'):
                    print(f"  Soil 10cm: {latest['soil10_pct']:.1f}%")
                if latest.get('soil20_pct'):
                    print(f"  Soil 20cm: {latest['soil20_pct']:.1f}%")
            
            # Check port data
            ports = device.get('ports', {})
            if ports:
                print("  Port Data:")
                for port_key, value in ports.items():
                    if value is not None:
                        if 'temp' in port_key:
                            print(f"    {port_key}: {value:.1f}C")
                        elif 'vwc' in port_key:
                            print(f"    {port_key}: {value:.1f}%")
                        elif 'ec' in port_key:
                            print(f"    {port_key}: {value:.1f}uS/cm")
                        elif 'wp' in port_key:
                            print(f"    {port_key}: {value:.1f}kPa")
                        else:
                            print(f"    {port_key}: {value}")
            
            # Check soil summary
            soil = device.get('soil', {})
            if soil and soil.get('latest'):
                soil_latest = soil['latest']
                print("  Soil Summary:")
                if soil_latest.get('soil10_pct'):
                    print(f"    10cm: {soil_latest['soil10_pct']:.1f}%")
                if soil_latest.get('soil20_pct'):
                    print(f"    20cm: {soil_latest['soil20_pct']:.1f}%")
                if soil_latest.get('avg_pct'):
                    print(f"    Average: {soil_latest['avg_pct']:.1f}%")
        
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"Network error: {e}")
        return False
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False

def test_individual_device(device_sn):
    """Test individual device endpoint"""
    try:
        print(f"\nTesting individual device: {device_sn}")
        response = requests.get(f"http://127.0.0.1:5000/api/soil/{device_sn}", timeout=30)
        
        if response.status_code != 200:
            print(f"Error: HTTP {response.status_code}")
            return False
        
        data = response.json()
        print(f"Device {device_sn} soil data:")
        latest = data.get('latest', {})
        if latest:
            for key, value in latest.items():
                if value is not None:
                    if key == 'time':
                        print(f"  {key}: {value}")
                    else:
                        print(f"  {key}: {value}")
        
        return True
        
    except Exception as e:
        print(f"Error testing device {device_sn}: {e}")
        return False

if __name__ == "__main__":
    print("Testing New Sensor Data Structure")
    print("=" * 50)
    
    # Test main endpoint
    success = test_combined_all_endpoint()
    
    if success:
        # Test individual devices
        devices = ["z6-32396", "z6-20881", "z6-27574", "z6-27573"]
        for device in devices:
            test_individual_device(device)
    
    print("\n" + "=" * 50)
    print("Test completed!" if success else "Test failed!")