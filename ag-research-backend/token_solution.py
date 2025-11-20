"""
CLIMATE ENGINE API TOKEN ISSUE - SOLUTION STEPS

PROBLEM:
- Token format is correct (JWT)
- Token is not expired (expires Oct 24, 2025)
- API returns {"detail":"Invalid API token"} with 401 status

SOLUTION NEEDED:
Your token appears to be revoked or invalid on Climate Engine's side.

NEXT STEPS:
1. Go to https://app.climateengine.org/
2. Sign in to your account
3. Generate a NEW API token
4. Replace the token in both files:
   - ag-research-backend/.env (line with CLIMATE_ENGINE_API_TOKEN=)
   - ag-research-dashboard/src/config/apiConfig.js (API_TOKEN field)

CURRENT TOKEN (first 50 chars):
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJmcmVzaCI6ZmFsc2U

REPLACEMENT FORMAT:
The new token should look similar - starting with eyJ... and being about 300-400 characters long.

AFTER GETTING NEW TOKEN:
1. Update both config files
2. Restart Flask backend: python app.py  
3. Restart React frontend: npm start
4. Test the precipitation/ETO chart

The code structure is correct - we just need a valid token.
"""

print(__doc__)

# Also show the exact places to update
import os
from dotenv import load_dotenv

load_dotenv()
current_token = os.getenv("CLIMATE_ENGINE_API_TOKEN", "NOT_FOUND")

print(f"\nCURRENT TOKEN IN .env FILE:")
print(f"{current_token[:50]}...")

print(f"\nFILES TO UPDATE WITH NEW TOKEN:")
print(f"1. ag-research-backend/.env")
print(f"   Line: CLIMATE_ENGINE_API_TOKEN=YOUR_NEW_TOKEN_HERE")
print(f"")
print(f"2. ag-research-dashboard/src/config/apiConfig.js") 
print(f"   Line: API_TOKEN: \"YOUR_NEW_TOKEN_HERE\",")

print(f"\nTO GET NEW TOKEN:")
print(f"1. Visit: https://app.climateengine.org/")
print(f"2. Login to your account")
print(f"3. Look for 'API' or 'Developer' or 'Settings' section")
print(f"4. Generate new API token")
print(f"5. Copy the full token (usually starts with 'eyJ')")
print(f"6. Paste it in both config files above")