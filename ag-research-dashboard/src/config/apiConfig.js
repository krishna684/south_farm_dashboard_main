// src/config/apiConfig.js

// Climate Engine API Configuration
export const CLIMATE_ENGINE_CONFIG = {
  API_TOKEN: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJmcmVzaCI6ZmFsc2UsImlhdCI6MTc1NjEzODExNSwianRpIjoiYTkyNDFmYWEtNGQyMS00ZDU5LThlOGItZWMzY2I4YTE2N2IxIiwibmJmIjoxNzU2MTM4MTE1LCJ0eXBlIjoiYWNjZXNzIiwic3ViIjoiV0J0Qkc3VnBzMGRDdjZIaUtzQjRlbDBLMk9vMSIsImV4cCI6MTc2MTMyMjExNSwicm9sZXMiOiJ1c2VyIiwidXNlcl9pZCI6IldCdEJHN1ZwczBkQ3Y2SGlLc0I0ZWwwSzJPbzEifQ.tldxNXP22FA95SfUKE0BB2aJ5yH6rddRKxhgJwSARRw",
  BASE_URL: "https://api.climateengine.org"
};

// Flask API Configuration
export const FLASK_API_CONFIG = {
  BASE_URL: "http://127.0.0.1:5000"
};

// Field Location (Columbia, MO - adjust to your field coordinates)
export const FIELD_LOCATION = {
  lat: 38.9517,
  lon: -92.3341
};

// Data refresh intervals (milliseconds)
export const REFRESH_INTERVALS = {
  TABLE_DATA: 5 * 60 * 1000,   // 5 minutes
  CHART_DATA: 15 * 60 * 1000   // 15 minutes
};