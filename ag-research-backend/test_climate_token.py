#!/usr/bin/env python3
"""
Test Climate Engine API token and check expiration
"""
import os
import json
import requests
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def decode_jwt_payload(token):
    """Decode JWT token payload without verification"""
    try:
        import base64
        import json
        
        # JWT tokens have 3 parts separated by dots
        parts = token.split('.')
        if len(parts) != 3:
            return None
            
        # Decode the payload (second part)
        payload_part = parts[1]
        # Add padding if necessary
        payload_part += '=' * (4 - len(payload_part) % 4)
        decoded_bytes = base64.urlsafe_b64decode(payload_part)
        payload = json.loads(decoded_bytes)
        return payload
    except Exception as e:
        print(f"Error decoding token: {e}")
        return None

def test_climate_engine_token():
    """Test Climate Engine API token"""
    token = os.getenv('CLIMATE_ENGINE_API_TOKEN')
    
    if not token:
        print("❌ No CLIMATE_ENGINE_API_TOKEN found in environment")
        return False
    
    print(f"✓ Token found (length: {len(token)})")
    
    # Decode and check expiration
    payload = decode_jwt_payload(token)
    if payload:
        print("Token payload:")
        for key, value in payload.items():
            if key == 'exp':
                exp_date = datetime.fromtimestamp(value)
                now = datetime.now()
                expired = now > exp_date
                print(f"  {key}: {value} ({exp_date}) {'❌ EXPIRED' if expired else '✓ Valid'}")
            else:
                print(f"  {key}: {value}")
        
        exp_timestamp = payload.get('exp', 0)
        if exp_timestamp:
            exp_date = datetime.fromtimestamp(exp_timestamp)
            now = datetime.now()
            if now > exp_date:
                print("❌ Token has EXPIRED!")
                return False
    
    # Test API call
    print("\nTesting API call...")
    headers = {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/json'
    }
    
    # Test simple endpoint first
    try:
        response = requests.get('https://api.climateengine.org/', headers=headers, timeout=10)
        print(f"Base API Status: {response.status_code}")
        
        if response.status_code == 401:
            print("❌ 401 Unauthorized - Token is invalid or expired")
            return False
        elif response.status_code == 200:
            print("✓ Base API call successful")
        
    except Exception as e:
        print(f"❌ API call failed: {e}")
        return False
    
    # Test ETO forecast endpoint
    try:
        params = {
            'coordinates': '[[-92.2808,38.9069]]',
            'area_reducer': 'mean',
            'dataset': 'CFS_GRIDMET',
            'variable': 'eto',
            'model': 'ens01',
            'export_format': 'json'
        }
        
        url = 'https://api.climateengine.org/timeseries/native/forecasts/coordinates'
        response = requests.get(url, headers=headers, params=params, timeout=30)
        
        print(f"ETO Forecast Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✓ ETO forecast data received")
            print(f"Response keys: {list(data.keys())}")
            if 'Data' in data and len(data['Data']) > 0:
                print(f"Data blocks: {len(data['Data'])}")
                if 'Data' in data['Data'][0]:
                    print(f"First block data points: {len(data['Data'][0]['Data'])}")
            return True
        else:
            print(f"❌ ETO forecast failed: {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"❌ ETO forecast failed: {e}")
        return False

if __name__ == "__main__":
    success = test_climate_engine_token()
    print(f"\n{'✓ SUCCESS' if success else '❌ FAILED'}")