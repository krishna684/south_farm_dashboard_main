import React, { useState, useEffect } from 'react';
import TemperatureMinMaxAvgChart from './TemperatureMinMaxAvgChart';
import SolarRadiationChart from './SolarRadiationChart';
import PrecipitationETOForecastChart from './PrecipitationETOForecastChart';

function WeatherOverview() {
  const [tableData, setTableData] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchTableData = async () => {
      const deviceSn = 'z6-23000';

      try {
        const response = await fetch(`http://127.0.0.1:5000/api/live/${deviceSn}`);
        if (!response.ok) {
          const errData = await response.json();
          throw new Error(errData.error || `HTTP error! status: ${response.status}`);
        }
        const apiData = await response.json();
        
        // Debug: Log all available sensor data keys
        console.log('Available sensor data keys:', Object.keys(apiData));
        console.log('Full API data:', apiData);

        // ✅ Updated sensor mapping
        const sensorMapping = {
        temp: 'Air Temperature',
        precip: 'Precipitation',
        solar: 'Solar Radiation',
        vpd: 'VPD', // use Zentra's VPD label (kPa)
        soil10: 'TEROS 12 Soil VWC @ 10cm', // Port 1 (10cm)
        soil20: 'TEROS 12 Soil VWC @ 20cm', // Port 2 (20cm)
      };
      
      // Debug: Check if soil moisture sensors exist
      console.log('Soil 10cm data exists:', !!apiData[sensorMapping.soil10]);
      console.log('Soil 20cm data exists:', !!apiData[sensorMapping.soil20]);
      console.log('Water Content data exists:', !!apiData['Water Content']);
      
      if (apiData[sensorMapping.soil10]) {
        console.log('Soil 10cm data:', apiData[sensorMapping.soil10]);
      }
      if (apiData[sensorMapping.soil20]) {
        console.log('Soil 20cm data:', apiData[sensorMapping.soil20]);
      }
      if (apiData['Water Content']) {
        console.log('Water Content data:', apiData['Water Content']);
      }


        const formattedData = [];
        const primarySensorReadings = apiData[sensorMapping.temp];
        if (!primarySensorReadings || primarySensorReadings.length === 0) {
          throw new Error(`Primary sensor '${sensorMapping.temp}' not found or has no data.`);
        }

        for (let i = 0; i < 6 && i < primarySensorReadings.length; i++) {
          const getValue = (sensorKey, index) =>
            apiData[sensorMapping[sensorKey]]?.[index]?.value ?? 'N/A';

          const tempC = parseFloat(getValue('temp', i));
          const tempF = !isNaN(tempC) ? ((tempC * 9) / 5 + 32).toFixed(1) : 'N/A';

          const precipMM = parseFloat(getValue('precip', i));
          const precipIN = !isNaN(precipMM) ? (precipMM / 25.4).toFixed(2) : 'N/A';

          const solarRadRaw = getValue('solar', i);
          const solarRad = !isNaN(parseFloat(solarRadRaw)) ? parseFloat(solarRadRaw).toFixed(0) : 'N/A';

          const vpdRaw = getValue('vpd', i);
          const vpd = !isNaN(parseFloat(vpdRaw)) ? parseFloat(vpdRaw).toFixed(2) : 'N/A';

          // Try port-specific soil moisture first, then fallback to generic Water Content
          let soil10Raw = getValue('soil10', i);
          if (soil10Raw === 'N/A' && apiData['Water Content']?.[i]?.value !== undefined) {
            soil10Raw = apiData['Water Content'][i].value;
          }
          const soil10Val = parseFloat(soil10Raw);
          const soil10 = !isNaN(soil10Val)
            ? ((soil10Val <= 1 ? soil10Val * 100 : soil10Val).toFixed(1))
            : 'N/A';

          let soil20Raw = getValue('soil20', i);
          console.log(`Row ${i} - Soil 20cm raw value:`, soil20Raw);
          
          // If no port-specific 20cm data, check for other possible sensor names
          if (soil20Raw === 'N/A') {
            // Check for alternative sensor names
            const alternativeNames = [
              'TEROS 12 Soil VWC @ 20cm (P2)',
              'Water Content',
              'Volumetric Water Content',
              'Soil VWC'
            ];
            
            for (const altName of alternativeNames) {
              if (apiData[altName]?.[i]?.value !== undefined) {
                soil20Raw = apiData[altName][i].value;
                console.log(`Found soil 20cm data in '${altName}':`, soil20Raw);
                break;
              }
            }
          }
          
          const soil20Val = parseFloat(soil20Raw);
          const soil20 = !isNaN(soil20Val)
            ? ((soil20Val <= 1 ? soil20Val * 100 : soil20Val).toFixed(1))
            : 'N/A';
            
          console.log(`Row ${i} - Final soil 20cm value:`, soil20);



          formattedData.push({
            time:
              i === 0
                ? 'Current'
                : new Date(primarySensorReadings[i].time).toLocaleTimeString('en-US', {
                    hour: 'numeric',
                    minute: '2-digit',
                  }),
            temp: tempF,
            precipitation: precipIN,
            solarRadiation: solarRad,
            vpd: vpd,
            soilMoisture10cm: soil10,
            soilMoisture20cm: soil20,
          });
        }

        setTableData(formattedData);
      } catch (e) {
        console.error("Failed to fetch or process data:", e);
        setError(e.message);
      } finally {
        setIsLoading(false);
      }
    };

    fetchTableData();
    
    const intervalId = setInterval(fetchTableData, 300000); // refresh table every 5 minutes
    
    return () => {
      clearInterval(intervalId);
    };
  }, []);

  if (isLoading) {
    return <div className="overview-panel"><h2>Loading Live Data...</h2></div>;
  }

  if (error) {
    return (
      <div className="overview-panel">
        <h2>Error: {error}</h2>
        <p>Could not fetch data. Is the Python server running and are the sensor names in <code>sensorMapping</code> correct?</p>
      </div>
    );
  }

  return (
    <div className="overview-panel">
      <h2>Local Weather</h2>
      <div className="table-container">
        <table>
          <thead>
            <tr>
              <th>Time</th>
              <th>Temp (°F)</th>
              <th>Precip (in)</th>
              <th>Solar Rad (W/m²)</th>
              <th>VPD (kPa)</th>
              <th>Soil Moist. 10cm (%) <sup>*</sup></th>
              <th>Soil Moist. 20cm (%) <sup>*</sup></th>
            </tr>
          </thead>
          <tbody>
            {tableData.map((hour, index) => (
              <tr key={index} className={index === 0 ? 'current-time-row' : ''}>
                <td>{hour.time}</td>
                <td>{hour.temp}</td>
                <td>{hour.precipitation}</td>
                <td>{hour.solarRadiation}</td>
                <td>{hour.vpd}</td>
                <td>{hour.soilMoisture10cm}</td>
                <td>{hour.soilMoisture20cm}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="table-footnote">
          <sup>*</sup> Measuring average of 8 locations with standard deviation of &plusmn; 0.005
        </p>
      </div>
      
      {/* Charts Section */}
      <div className="charts-section">
        {/* Split 24-Hour Charts Row */}
        <div className="dual-chart-row">
          <div className="half-chart-container">
            <TemperatureMinMaxAvgChart />
          </div>
          <div className="half-chart-container">
            <SolarRadiationChart />
          </div>
        </div>
        
        {/* Full-width Forecast Chart */}
        <div className="single-chart-container">
          <PrecipitationETOForecastChart />
        </div>
      </div>
    </div>
  );
}

export default WeatherOverview;
