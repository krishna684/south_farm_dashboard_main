#!/usr/bin/env python3
"""
Test Climate Engine API with different authentication and endpoint approaches
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

def test_alternative_approaches():
    token = os.getenv('CLIMATE_ENGINE_API_TOKEN')
    
    print("=== Testing Different Auth Methods ===")
    
    # Test 1: Bearer token (current method)
    headers1 = {'Authorization': f'Bearer {token}'}
    
    # Test 2: Direct token (no Bearer prefix)
    headers2 = {'Authorization': token}
    
    # Test 3: API Key header
    headers3 = {'X-API-Key': token}
    
    # Test 4: Different header name
    headers4 = {'API-Token': token}
    
    auth_methods = [
        ('Bearer Token', headers1),
        ('Direct Token', headers2),
        ('X-API-Key', headers3),
        ('API-Token', headers4)
    ]
    
    base_url = 'https://api.climateengine.org'
    
    for method_name, headers in auth_methods:
        print(f"\n--- {method_name} ---")
        
        # Test base endpoint
        try:
            response = requests.get(base_url, headers=headers, timeout=10)
            print(f"Base API: {response.status_code}")
        except Exception as e:
            print(f"Base API failed: {e}")
            continue
            
        if response.status_code == 200:
            # Try a simple data endpoint
            try:
                simple_url = f"{base_url}/timeseries"
                response = requests.get(simple_url, headers=headers, timeout=10)
                print(f"Timeseries endpoint: {response.status_code}")
                
                if response.status_code != 200:
                    print(f"  Response: {response.text[:100]}")
            except Exception as e:
                print(f"Timeseries failed: {e}")

def test_available_endpoints():
    token = os.getenv('CLIMATE_ENGINE_API_TOKEN')
    headers = {'Authorization': f'Bearer {token}'}
    
    print("\n=== Testing Available Endpoints ===")
    
    endpoints = [
        '/datasets',
        '/variables', 
        '/models',
        '/timeseries',
        '/forecast',
        '/forecasts',
        '/data',
        '/api/v1/timeseries',
        '/v1/timeseries',
    ]
    
    base_url = 'https://api.climateengine.org'
    
    for endpoint in endpoints:
        try:
            url = f"{base_url}{endpoint}"
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                print(f"✓ {endpoint} - 200 OK")
                data = response.json()
                if isinstance(data, dict):
                    print(f"  Keys: {list(data.keys())[:5]}")
                elif isinstance(data, list):
                    print(f"  List length: {len(data)}")
            elif response.status_code == 401:
                print(f"❌ {endpoint} - 401 Unauthorized")
            elif response.status_code == 404:
                print(f"- {endpoint} - 404 Not Found")
            else:
                print(f"? {endpoint} - {response.status_code}")
                
        except Exception as e:
            print(f"❌ {endpoint} - Exception: {e}")

if __name__ == "__main__":
    test_alternative_approaches()
    test_available_endpoints()