#!/usr/bin/env python3
"""
Simple test script to verify Climate Engine API connectivity.
"""
import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_climate_engine_api():
    """Test Climate Engine API with simple parameters"""
    
    # Get token from .env file
    token = os.getenv("CLIMATE_ENGINE_API_TOKEN")
    if not token:
        print("ERROR: No CLIMATE_ENGINE_API_TOKEN found in .env file")
        return False
    
    print(f"Using token: {token[:20]}...")
    
    # Set up headers
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json"
    }
    
    # Try multiple parameter formats to find the right one
    test_cases = [
        {
            "name": "Basic GRIDMET test",
            "params": {
                "dataset": "GRIDMET",
                "variable": "eto",
                "start_date": "2024-10-01",
                "end_date": "2024-10-01",
                "lat": 38.9069,
                "lon": -92.2808
            }
        },
        {
            "name": "GridMET with different case",
            "params": {
                "dataset": "GridMET",
                "variable": "eto", 
                "start_date": "2024-10-01",
                "end_date": "2024-10-01",
                "lat": 38.9069,
                "lon": -92.2808
            }
        },
        {
            "name": "Different variable name",
            "params": {
                "dataset": "GRIDMET", 
                "variable": "pet",  # Different variable
                "start_date": "2024-10-01",
                "end_date": "2024-10-01",
                "lat": 38.9069,
                "lon": -92.2808
            }
        }
    ]
    
    url = "https://api.climateengine.org/timeseries/native/coordinates"
    print(f"Testing URL: {url}")
    
    # Test each case
    for test_case in test_cases:
        print(f"\n--- Testing: {test_case['name']} ---")
        params = test_case['params']
        print(f"Parameters: {params}")
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            
            print(f"Response Status: {response.status_code}")
            print(f"Response Content: {response.text}")
            
            if response.status_code == 200:
                print("✅ SUCCESS: This parameter set works!")
                try:
                    json_data = response.json()
                    print(f"JSON Keys: {list(json_data.keys())}")
                    return True
                except Exception as e:
                    print(f"❌ JSON parsing error: {e}")
            else:
                print(f"❌ FAILED: HTTP {response.status_code}")
                
        except Exception as e:
            print(f"❌ REQUEST ERROR: {e}")
    
    return False

if __name__ == "__main__":
    print("Testing Climate Engine API...")
    success = test_climate_engine_api()
    if success:
        print("\n🎉 Climate Engine API test PASSED!")
    else:
        print("\n💥 Climate Engine API test FAILED!")