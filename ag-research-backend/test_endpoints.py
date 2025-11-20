#!/usr/bin/env python3
"""
Test different Climate Engine API endpoints to find the correct one for ETO forecasts
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

#!/usr/bin/env python3
"""
Test different Climate Engine API endpoints to find working ones
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

def test_basic_endpoints():
    token = os.getenv('CLIMATE_ENGINE_API_TOKEN')
    headers = {'Authorization': f'Bearer {token}'}
    
    # Test different endpoint structures
    endpoints_to_test = [
        # Original endpoint from the code
        {
            'name': 'Native Forecasts Coordinates',
            'url': 'https://api.climateengine.org/timeseries/native/forecasts/coordinates',
            'params': {
                'coordinates': '[[-92.2808,38.9069]]',
                'area_reducer': 'mean',
                'dataset': 'CFS_GRIDMET',
                'variable': 'eto',
                'model': 'ens01',
                'export_format': 'json'
            }
        },
        # Alternative with different model
        {
            'name': 'Native Forecasts with ens_mean',
            'url': 'https://api.climateengine.org/timeseries/native/forecasts/coordinates',
            'params': {
                'coordinates': '[[-92.2808,38.9069]]',
                'area_reducer': 'mean',
                'dataset': 'CFS_GRIDMET',
                'variable': 'eto',
                'model': 'ens_mean',
                'export_format': 'json'
            }
        },
        # Try simpler endpoint structure
        {
            'name': 'Timeseries Forecasts',
            'url': 'https://api.climateengine.org/timeseries/forecasts',
            'params': {
                'lat': '38.9069',
                'lon': '-92.2808',
                'dataset': 'CFS_GRIDMET',
                'variable': 'eto',
                'export_format': 'json'
            }
        },
        # Try precipitation to see if that works
        {
            'name': 'Precipitation Forecast',
            'url': 'https://api.climateengine.org/timeseries/native/forecasts/coordinates',
            'params': {
                'coordinates': '[[-92.2808,38.9069]]',
                'area_reducer': 'mean',
                'dataset': 'CFS_GRIDMET',
                'variable': 'pr',
                'model': 'ens01',
                'export_format': 'json'
            }
        }
    ]
    
    for endpoint in endpoints_to_test:
        print(f"\n--- Testing: {endpoint['name']} ---")
        try:
            response = requests.get(
                endpoint['url'], 
                headers=headers, 
                params=endpoint['params'], 
                timeout=30
            )
            
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✓ Success! Response keys: {list(data.keys())}")
                if 'Data' in data:
                    print(f"  Data blocks: {len(data['Data'])}")
                    if len(data['Data']) > 0 and 'Data' in data['Data'][0]:
                        print(f"  First block entries: {len(data['Data'][0]['Data'])}")
                        # Show first few entries
                        sample_data = data['Data'][0]['Data'][:3]
                        print(f"  Sample data: {sample_data}")
            else:
                error_text = response.text[:200]
                print(f"❌ Failed: {error_text}")
                
        except Exception as e:
            print(f"❌ Exception: {e}")

if __name__ == "__main__":
    test_basic_endpoints()