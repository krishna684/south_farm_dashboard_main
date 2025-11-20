// src/components/TemperatureMinMaxAvgChart.js
import React, { useState, useEffect } from 'react';
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend } from 'chart.js';
import { Line } from 'react-chartjs-2';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend);

function TemperatureMinMaxAvgChart() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchTemperatureData();
    const interval = setInterval(fetchTemperatureData, 300000); // 5 minutes
    return () => clearInterval(interval);
  }, []);

  const fetchTemperatureData = async () => {
    try {
      const response = await fetch('http://127.0.0.1:5000/api/live/z6-23000');
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const apiData = await response.json();
      console.log('Temperature Chart - API Data received:', Object.keys(apiData));
      
      const tempReadings = apiData['Air Temperature'] || [];
      
      // Debug: Log current time and timezone info
      const now = new Date();
      console.log('Current local time:', now.toLocaleString());
      console.log('Current Columbia, MO time:', now.toLocaleString('en-US', {
        timeZone: 'America/Chicago'
      }));
      console.log('Total temperature readings available:', tempReadings.length);
      
      if (tempReadings.length === 0) {
        console.log('No temperature data found in API response');
        setData([]);
        return;
      }
      
      // Get the last 24 hours of data
      const currentTime = new Date();
      const twentyFourHoursAgo = new Date(currentTime.getTime() - (24 * 60 * 60 * 1000));
      
      // Filter to get only readings from last 24 hours and sort by timestamp
      const recentReadings = tempReadings
        .filter(reading => {
          const readingTime = new Date(reading.time);
          return readingTime >= twentyFourHoursAgo;
        })
        .sort((a, b) => new Date(a.time) - new Date(b.time));
      
      console.log(`=== TEMPERATURE 24-HOUR DATA ===`);
      console.log(`Total API readings: ${tempReadings.length}`);
      console.log(`Filtered to ${recentReadings.length} temperature readings from last 24 hours`);
      if (recentReadings.length > 0) {
        console.log(`Time range: ${recentReadings[0].time} to ${recentReadings[recentReadings.length - 1].time}`);
      }
      
      // Group readings by hour to calculate min/max/avg
      const hourlyData = {};
      
      recentReadings.forEach(reading => {
        const timestamp = new Date(reading.time);
        const hourKey = timestamp.toISOString().slice(0, 13); // YYYY-MM-DDTHH
        const tempC = parseFloat(reading.value);
        const tempF = (tempC * 9/5) + 32;
        
        if (!hourlyData[hourKey]) {
          hourlyData[hourKey] = {
            timestamp,
            temps: [],
            hourKey
          };
        }
        hourlyData[hourKey].temps.push(tempF);
      });
      
      // Convert to array and calculate min/max/avg for each hour
      const processedData = Object.values(hourlyData)
        .slice(-24) // Get last 24 hours
        .map(hourData => {
          const temps = hourData.temps;
          const tempMin = Math.min(...temps);
          const tempMax = Math.max(...temps);
          const tempAvg = temps.reduce((sum, temp) => sum + temp, 0) / temps.length;
          
          const now = new Date();
          const isRecent = Math.abs(now - hourData.timestamp) < 60 * 60 * 1000; // within 1 hour
          
          const timeLabel = isRecent ? 'Now' : hourData.timestamp.toLocaleString('en-US', {
            timeZone: 'America/Chicago', // Columbia, MO timezone
            hour: 'numeric',
            minute: '2-digit',
            hour12: true
          });
          
          return {
            time: timeLabel,
            tempMin: Math.round(tempMin * 10) / 10, // Round to 1 decimal
            tempMax: Math.round(tempMax * 10) / 10,
            tempAvg: Math.round(tempAvg * 10) / 10,
            timestamp: hourData.timestamp,
            actualTime: hourData.timestamp
          };
        });
      
      console.log(`Final processed temperature data points: ${processedData.length}`);
      console.log('Temperature data time range:', processedData.length > 0 ? 
        `${processedData[0].time} to ${processedData[processedData.length - 1].time}` : 'No data');
      
      setData(processedData);
    } catch (error) {
      console.error('Error fetching temperature data:', error);
      // Set empty data on error to prevent crashes
      setData([]);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div style={{display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%'}}>
      <p>Loading temperature data...</p>
    </div>;
  }

  if (data.length === 0) {
    return <div style={{
      display: 'flex', 
      flexDirection: 'column',
      alignItems: 'center', 
      justifyContent: 'center', 
      height: '100%',
      color: '#666',
      backgroundColor: '#f8f9fa',
      borderRadius: '8px',
      border: '2px dashed #ddd'
    }}>
      <div style={{fontSize: '48px', marginBottom: '10px'}}>🌡️</div>
      <p style={{margin: 0, fontSize: '14px', fontWeight: 'bold'}}>No temperature data available</p>
      <p style={{margin: '5px 0 0 0', fontSize: '12px', color: '#999'}}>Check weather station connection</p>
    </div>;
  }

  const chartData = {
    labels: data.map(item => item.time),
    datasets: [
      {
        label: 'Min Temperature (°F)',
        data: data.map(item => item.tempMin),
        borderColor: 'rgb(54, 162, 235)',
        backgroundColor: 'rgba(54, 162, 235, 0.1)',
        pointRadius: 3,
        tension: 0.2,
        borderWidth: 2,
      },
      {
        label: 'Max Temperature (°F)',
        data: data.map(item => item.tempMax),
        borderColor: 'rgb(255, 99, 132)',
        backgroundColor: 'rgba(255, 99, 132, 0.1)',
        pointRadius: 3,
        tension: 0.2,
        borderWidth: 2,
      },
      {
        label: 'Avg Temperature (°F)',
        data: data.map(item => item.tempAvg),
        borderColor: 'rgb(255, 206, 86)',
        backgroundColor: 'rgba(255, 206, 86, 0.1)',
        pointRadius: 3,
        tension: 0.2,
        borderWidth: 2,
      }
    ]
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top',
        labels: {
          boxWidth: 12,
          usePointStyle: true,
          padding: 15,
        },
      },
      title: {
        display: true,
        text: '24 Hours Temperature',
        font: {
          size: 14,
          weight: 'bold',
        },
      },
      tooltip: {
        mode: 'index',
        intersect: false,
        backgroundColor: 'rgba(75, 192, 192, 0.9)',
        titleColor: 'white',
        bodyColor: 'white',
        borderColor: 'rgb(75, 192, 192)',
        borderWidth: 2,
        callbacks: {
          title: function(context) {
            const dataPoint = data[context[0].dataIndex];
            if (dataPoint && dataPoint.actualTime) {
              return dataPoint.actualTime.toLocaleString('en-US', {
                timeZone: 'America/Chicago',
                weekday: 'short',
                month: 'short',
                day: 'numeric',
                hour: 'numeric',
                minute: '2-digit',
                hour12: true
              }) + ' (Columbia, MO)';
            }
            return context[0].label;
          },
          label: function(context) {
            const temp = context.parsed.y.toFixed(1);
            let emoji = '🌡️';
            if (context.parsed.y > 80) emoji = '🔥';
            else if (context.parsed.y > 70) emoji = '☀️';
            else if (context.parsed.y < 40) emoji = '🧊';
            else if (context.parsed.y < 50) emoji = '❄️';
            return `${emoji} ${context.dataset.label}: ${temp}°F`;
          },
          afterBody: function(context) {
            const dataPoint = data[context[0].dataIndex];
            if (dataPoint) {
              const range = dataPoint.tempMax - dataPoint.tempMin;
              return `Temperature range: ${range.toFixed(1)}°F`;
            }
            return '';
          }
        }
      },
    },
    scales: {
      y: {
        title: {
          display: true,
          text: 'Temperature (°F)',
          color: '#333',
          font: {
            weight: 'bold',
          },
        },
        grid: {
          color: 'rgba(0,0,0,0.1)',
        },
      },
      x: {
        title: {
          display: true,
          text: 'Time (Columbia, MO - Central Time)',
          font: {
            size: 12,
            weight: 'bold'
          }
        },
        grid: {
          color: 'rgba(0,0,0,0.05)',
        },
      },
    },
  };

  return <Line data={chartData} options={options} />;
}

export default TemperatureMinMaxAvgChart;