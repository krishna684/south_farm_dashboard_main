// src/components/SolarRadiationChart.js
import React, { useState, useEffect } from 'react';
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, BarElement, Title, Tooltip, Legend } from 'chart.js';
import { Line } from 'react-chartjs-2';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, BarElement, Title, Tooltip, Legend);

function SolarRadiationChart() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchSolarRadiationData();
    const interval = setInterval(fetchSolarRadiationData, 300000); // 5 minutes
    return () => clearInterval(interval);
  }, []);

  const fetchSolarRadiationData = async () => {
    try {
      const response = await fetch('http://127.0.0.1:5000/api/live/z6-23000');
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const apiData = await response.json();
      console.log('Solar Radiation Chart - API Data received:', Object.keys(apiData));
      
      // Get solar radiation readings from Zentra weather station
      const solarReadings = apiData['Solar Radiation'] || [];
      
      // Debug: Log current time and timezone info
      const now = new Date();
      console.log('Current local time:', now.toLocaleString());
      console.log('Current Columbia, MO time:', now.toLocaleString('en-US', {
        timeZone: 'America/Chicago'
      }));
      
      if (solarReadings.length === 0) {
        console.log('No Solar Radiation data found in API response');
        console.log('Available data keys:', Object.keys(apiData));
        setData([]);
        return;
      }
      
      // Get the last 24 hours of data
      const currentTime = new Date();
      const twentyFourHoursAgo = new Date(currentTime.getTime() - (24 * 60 * 60 * 1000));
      
      // Filter to get only readings from last 24 hours and sort by timestamp
      const recentReadings = solarReadings
        .filter(reading => {
          const readingTime = new Date(reading.time);
          return readingTime >= twentyFourHoursAgo;
        })
        .sort((a, b) => new Date(a.time) - new Date(b.time));
      
      console.log(`=== SOLAR RADIATION 24-HOUR DATA ===`);
      console.log(`Total API readings: ${solarReadings.length}`);
      console.log(`Filtered to ${recentReadings.length} readings from last 24 hours`);
      if (recentReadings.length > 0) {
        console.log(`Time range: ${recentReadings[0].time} to ${recentReadings[recentReadings.length - 1].time}`);
      }
      
      // Group readings by hour to get hourly averages for cleaner 24-hour view
      const hourlyData = {};
      
      recentReadings.forEach(reading => {
        const timestamp = new Date(reading.time);
        const hourKey = timestamp.toISOString().slice(0, 13); // YYYY-MM-DDTHH
        const solarValue = parseFloat(reading.value) || 0;
        
        if (!hourlyData[hourKey]) {
          hourlyData[hourKey] = {
            timestamp,
            values: [],
            hourKey
          };
        }
        hourlyData[hourKey].values.push(solarValue);
      });
      
      // Convert to array and calculate averages for each hour
      const processedData = Object.values(hourlyData)
        .map(hourData => {
          const avgSolar = hourData.values.reduce((sum, val) => sum + val, 0) / hourData.values.length;
          const timestamp = hourData.timestamp;
          const currentTime = new Date();
          const isRecent = Math.abs(currentTime - timestamp) < 60 * 60 * 1000; // within 1 hour
          
          const timeLabel = isRecent ? 'Now' : timestamp.toLocaleString('en-US', {
            timeZone: 'America/Chicago', // Columbia, MO timezone
            hour: 'numeric',
            minute: '2-digit',
            hour12: true
          });
          
          return {
            time: timeLabel,
            solarRadiation: Math.round(avgSolar * 10) / 10, // Round to 1 decimal
            timestamp: timestamp.toISOString(),
            actualTime: timestamp
          };
        })
        .sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp)) // Ensure chronological order
        .slice(-24); // Get exactly the last 24 hours
      
      console.log(`Final processed solar data points: ${processedData.length}`);
      console.log('Solar data time range:', processedData.length > 0 ? 
        `${processedData[0].time} to ${processedData[processedData.length - 1].time}` : 'No data');
      
      setData(processedData);
    } catch (error) {
      console.error('Error fetching solar radiation data:', error);
      // Set empty data on error to prevent crashes
      setData([]);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div style={{display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%'}}>
      <p>Loading solar radiation data...</p>
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
      <div style={{fontSize: '48px', marginBottom: '10px'}}>☀️</div>
      <p style={{margin: 0, fontSize: '14px', fontWeight: 'bold'}}>No solar radiation data available</p>
      <p style={{margin: '5px 0 0 0', fontSize: '12px', color: '#999'}}>Check weather station connection</p>
    </div>;
  }

  // Calculate better visual scaling
  const maxValue = Math.max(...data.map(item => item.solarRadiation));
  const minValue = Math.min(...data.map(item => item.solarRadiation));
  
  const chartData = {
    labels: data.map(item => item.time),
    datasets: [
      {
        label: 'Solar Radiation (W/m²)',
        data: data.map(item => item.solarRadiation),
        borderColor: 'rgb(255, 152, 0)', // Vibrant orange
        backgroundColor: 'rgba(255, 193, 7, 0.2)', // More visible fill
        pointBackgroundColor: 'rgb(255, 152, 0)',
        pointBorderColor: 'rgb(255, 255, 255)',
        pointBorderWidth: 2,
        pointRadius: 3,
        pointHoverRadius: 8,
        pointHoverBackgroundColor: 'rgb(255, 87, 34)',
        tension: 0.4,
        borderWidth: 3,
        fill: true,
        // Add gradient effect
        segment: {
          backgroundColor: (ctx) => {
            if (ctx.p0.parsed.y > ctx.p1.parsed.y) {
              return 'rgba(255, 193, 7, 0.3)'; // Brighter when increasing
            }
            return 'rgba(255, 193, 7, 0.1)'; // Dimmer when decreasing
          }
        }
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
          font: {
            size: 11,
            weight: 'bold'
          }
        },
      },
      title: {
        display: true,
        text: `☀️ 24-Hour Solar Radiation (${minValue.toFixed(0)} - ${maxValue.toFixed(0)} W/m²)`,
        font: {
          size: 14,
          weight: 'bold'
        },
        color: 'rgb(255, 152, 0)'
      },
      tooltip: {
        mode: 'index',
        intersect: false,
        backgroundColor: 'rgba(255, 152, 0, 0.9)',
        titleColor: 'white',
        bodyColor: 'white',
        borderColor: 'rgb(255, 152, 0)',
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
            const value = context.parsed.y.toFixed(1);
            const percentage = maxValue > 0 ? ((context.parsed.y / maxValue) * 100).toFixed(1) : 0;
            return `☀️ ${value} W/m² (${percentage}% of peak)`;
          },
          afterLabel: function(context) {
            const value = context.parsed.y;
            if (value > 800) return '🔆 High solar intensity';
            if (value > 400) return '🌤️ Moderate solar intensity';
            if (value > 100) return '⛅ Low solar intensity';
            return '🌙 Minimal/nighttime';
          }
        }
      },
    },
    interaction: {
      mode: 'nearest',
      axis: 'x',
      intersect: false,
    },
    scales: {
      x: {
        display: true,
        title: {
          display: true,
          text: 'Time (Columbia, MO - Central Time)',
          font: {
            size: 12,
            weight: 'bold'
          }
        },
        grid: {
          color: 'rgba(255, 193, 7, 0.1)',
          lineWidth: 1
        },
        reverse: false,
      },
      y: {
        display: true,
        title: {
          display: true,
          text: 'Solar Radiation (W/m²)',
          font: {
            size: 12,
            weight: 'bold'
          }
        },
        grid: {
          color: 'rgba(255, 193, 7, 0.1)',
          lineWidth: 1
        },
        // Smart scaling that doesn't start from zero if all values are high
        beginAtZero: maxValue < 100, // Only start from zero if max is very low
        min: maxValue < 100 ? 0 : Math.max(0, minValue - (maxValue - minValue) * 0.1),
        max: maxValue > 100 ? maxValue * 1.15 : Math.max(maxValue * 1.2, 1000),
        ticks: {
          callback: function(value) {
            return Math.round(value) + ' W/m²';
          },
          font: {
            size: 10
          }
        }
      },
    },
    animation: {
      duration: 1000,
      easing: 'easeInOutQuart',
    },
    elements: {
      point: {
        hoverRadius: 8,
        hoverBorderWidth: 3
      },
      line: {
        borderCapStyle: 'round',
        borderJoinStyle: 'round'
      }
    }
  };

  return <Line data={chartData} options={options} />;
}

export default SolarRadiationChart;