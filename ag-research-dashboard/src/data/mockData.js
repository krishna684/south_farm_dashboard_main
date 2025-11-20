// src/data/mockData.js

// This is the single, correct declaration for the stations array.
// src/data/mockData.js
export const stations = [
  // 4 dataloggers
  {
    id: "DL-SECTION-4",
    name: "Section 4",
    position: [38.9069613, -92.2807347],
    status: "online",
    type: "datalogger",
    deviceSn: "z6-32396",
    externalUrl: "https://zentracloud.com/devices/z6-32396"
  },
  {
    id: "DL-SECTION-6",
    name: "Section 6",
    position: [38.9068077, -92.2807445],
    status: "online",
    type: "datalogger",
    deviceSn: "z6-20881",
    externalUrl: "https://zentracloud.com/devices/z6-20881"
  },
  {
    id: "DL-SECTION-5",
    name: "Section 5",
    position: [38.9068991, -92.2815533],
    status: "online",
    type: "datalogger",
    deviceSn: "z6-27574",
    externalUrl: "https://zentracloud.com/devices/z6-27574"
  },
  {
    id: "DL-SECTION-3",
    name: "Section 3",
    position: [38.9070547, -92.2815383],
    status: "online",
    type: "datalogger",
    deviceSn: "z6-27573",
    externalUrl: "https://zentracloud.com/devices/z6-27573"
  },

  // 1 weather station (edit link to the site you want to open)
  {
    id: "WS-100",
    name: "ATMOS41 Weather Station",
    position: [38.9088688, -92.2796074],
    status: "online",
    type: "weather station",
    externalUrl: "https://meter-weather-station.onrender.com/"
  }
];

export const sensorData = {
  "WS-001": Array.from({ length: 24 }, (_, i) => ({
    timestamp: `2025-07-29T${i.toString().padStart(2, '0')}:00:00Z`,
    temp: 75 + Math.sin(i * 0.2) * 15 + Math.random() * 2,
    humidity: 70 + Math.cos(i * 0.3) * 10 + Math.random() * 5,
  })),
  "WS-003": Array.from({ length: 24 }, (_, i) => ({
    timestamp: `2025-07-29T${i.toString().padStart(2, '0')}:00:00Z`,
    temp: 80 + Math.random() * 1,
    humidity: 85 + Math.random() * 2,
  })),
};

const now = new Date('2025-07-29T16:00:00Z'); // Set a "current" time for slicing

export const hourlyWeatherDataColumbia = Array.from({ length: 24 }, (_, i) => {
  const currentHour = new Date(now);
  currentHour.setHours(now.getHours() + (i - 18)); // Center the "peak" of the day
  const hour = currentHour.getHours();

  const baseTemp = 75 + Math.sin(i * 0.2) * 15;
  const tempVariation = 8; // Temperature range variation

  return {
    time: `${hour % 12 === 0 ? 12 : hour % 12}${hour < 12 || hour === 24 ? 'am' : 'pm'}`,
    temp: baseTemp,
    // Temperature min/max/avg for combined chart
    tempMin: baseTemp - tempVariation + Math.random() * 2,
    tempMax: baseTemp + tempVariation + Math.random() * 2,
    tempAvg: baseTemp + (Math.random() - 0.5) * 2,
    // Precipitation in inches
    precipitation: Math.max(0, Math.sin(i * 0.5) * 0.05 + (Math.random() - 0.5) * 0.02),
    // ETO (Evapotranspiration) in inches - typically higher during day, lower at night
    eto: Math.max(0.001, 0.01 + Math.sin((i - 6) * 0.3) * 0.008 + Math.random() * 0.002),
    solarRadiation: Math.max(0, 800 - Math.pow(i - 12, 2) * 15),
    vpd: Math.max(0.2, 1.5 + Math.sin(i * 0.2) * 1.2), // Vapour Pressure Deficit
    soilMoisture10cm: 35 - i * 0.5 + Math.random() * 2,
    soilMoisture20cm: 42 - i * 0.4 + Math.random() * 2,
    // Other data fields
    dewpoint: 70 + Math.sin((i + 2) * 0.2) * 12,
    gusts: Math.max(0, 5 + Math.sin(i * 0.5) * 5),
    relativeHumidity: 80 + Math.cos(i * 0.3) * 8,
    precipitationPotential: Math.max(0, 5 + Math.sin((i + 5) * 0.4) * 8),
    skyCover: Math.min(100, Math.max(0, 10 + Math.cos((i + 3) * 0.2) * 40)),
  };
});
