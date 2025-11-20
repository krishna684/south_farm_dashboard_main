#!/usr/bin/env python3
"""
Test different authentication methods for Climate Engine API
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

def test_auth_methods():
    """Test different authentication approaches"""
    
    token = os.getenv("CLIMATE_ENGINE_API_TOKEN")
    if not token:
        print("ERROR: No CLIMATE_ENGINE_API_TOKEN found")
        return False
    
    print(f"Testing with token: {token[:30]}...")
    
    # Test different auth header formats
    auth_tests = [
        {"Authorization": f"Bearer {token}"},
        {"Authorization": f"Token {token}"},  
        {"X-API-Key": token},
        {"apikey": token},
        {"token": token}
    ]
    
    url = "https://api.climateengine.org/timeseries/native/coordinates"
    params = {
        "dataset": "GRIDMET",
        "variable": "eto",
        "start_date": "2024-10-01",
        "end_date": "2024-10-01", 
        "lat": 38.9069,
        "lon": -92.2808
    }
    
    for i, auth_header in enumerate(auth_tests):
        print(f"\n--- Test {i+1}: {list(auth_header.keys())[0]} ---")
        headers = {**auth_header, "Accept": "application/json"}
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=15)
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text[:200]}...")
            
            if response.status_code == 200:
                print("✅ SUCCESS: This auth method works!")
                return True
            elif response.status_code == 401:
                print("❌ 401: Authentication failed")
            else:
                print(f"❌ {response.status_code}: Other error")
                
        except Exception as e:
            print(f"❌ Request failed: {e}")
    
    return False

def check_token_format():
    """Check if the token looks valid"""
    token = os.getenv("CLIMATE_ENGINE_API_TOKEN")
    if not token:
        return False
        
    print(f"\nToken Analysis:")
    print(f"Length: {len(token)}")
    print(f"Starts with: {token[:20]}...")
    print(f"Ends with: ...{token[-20:]}")
    
    # JWT tokens have 3 parts separated by dots
    if token.count('.') == 2:
        print("✅ Format: Looks like JWT token (3 parts)")
        parts = token.split('.')
        print(f"Header length: {len(parts[0])}")
        print(f"Payload length: {len(parts[1])}") 
        print(f"Signature length: {len(parts[2])}")
        
        # Try to decode header (it's base64)
        try:
            import base64
            import json
            # Add padding if needed
            header_padded = parts[0] + '=' * (4 - len(parts[0]) % 4)
            header_decoded = base64.b64decode(header_padded)
            header_json = json.loads(header_decoded)
            print(f"Header: {header_json}")
            
            # Decode payload
            payload_padded = parts[1] + '=' * (4 - len(parts[1]) % 4)  
            payload_decoded = base64.b64decode(payload_padded)
            payload_json = json.loads(payload_decoded)
            print(f"Payload keys: {list(payload_json.keys())}")
            if 'exp' in payload_json:
                import datetime
                exp_time = datetime.datetime.fromtimestamp(payload_json['exp'])
                print(f"Expires: {exp_time}")
                if exp_time < datetime.datetime.now():
                    print("❌ TOKEN IS EXPIRED!")
                else:
                    print("✅ Token not expired")
                    
        except Exception as e:
            print(f"❌ Token decode error: {e}")
    else:
        print("❌ Format: Not a JWT token")
    
    return True

if __name__ == "__main__":
    print("=== Climate Engine Authentication Test ===")
    check_token_format()
    test_auth_methods()