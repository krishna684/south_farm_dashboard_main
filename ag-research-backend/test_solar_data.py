#!/usr/bin/env python3
"""
Test script to verify Solar Radiation data is available from Flask API
"""
import requests
import json

def test_solar_data():
    """Test if solar radiation data is available from the Flask API"""
    
    try:
        # Test the live data endpoint
        url = "http://127.0.0.1:5000/api/live/z6-23000"
        print(f"Testing URL: {url}")
        
        response = requests.get(url, timeout=10)
        print(f"Response Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            # Check what sensor data is available
            print(f"\nAvailable sensor data keys:")
            for key in sorted(data.keys()):
                readings_count = len(data[key]) if isinstance(data[key], list) else 0
                print(f"  - {key}: {readings_count} readings")
            
            # Specifically check for Solar Radiation
            if 'Solar Radiation' in data:
                solar_readings = data['Solar Radiation']
                print(f"\n✅ Solar Radiation data found!")
                print(f"Number of readings: {len(solar_readings)}")
                
                if len(solar_readings) > 0:
                    latest = solar_readings[0]
                    print(f"Latest reading: {latest}")
                    
                    # Show first 5 readings
                    print(f"\nFirst 5 readings:")
                    for i, reading in enumerate(solar_readings[:5]):
                        value = reading.get('value', 'N/A')
                        timestamp = reading.get('timestamp', 'N/A')
                        print(f"  {i+1}. Value: {value} W/m², Time: {timestamp}")
                        
                    return True
                else:
                    print("❌ Solar Radiation data exists but has no readings")
                    return False
            else:
                print("❌ No Solar Radiation data found")
                print("Available sensors:")
                for key in data.keys():
                    if 'solar' in key.lower() or 'radiation' in key.lower():
                        print(f"  - Possible match: {key}")
                return False
                
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection failed - Flask server not running?")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("=== Solar Radiation Data Test ===")
    success = test_solar_data()
    
    if success:
        print("\n🎉 Solar Radiation data is available and ready for charts!")
    else:
        print("\n💥 Solar Radiation data test failed. Check Flask backend and Zentra API.")
        print("\nNext steps:")
        print("1. Make sure Flask backend is running (python app.py)")
        print("2. Check Zentra API token is valid")
        print("3. Verify device z6-23000 has solar radiation sensor")