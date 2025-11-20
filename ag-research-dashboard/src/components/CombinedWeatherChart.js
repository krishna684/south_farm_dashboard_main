// src/components/CombinedWeatherChart.js
import React from 'react';
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, BarElement, Title, Tooltip, Legend } from 'chart.js';
import { Chart } from 'react-chartjs-2';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, BarElement, Title, Tooltip, Legend);

function CombinedWeatherChart({ hourlyData }) {
  const chartData = {
    labels: hourlyData.map(item => item.time),
    datasets: [
      // Temperature Lines
      {
        label: 'Min Temperature (°F)',
        data: hourlyData.map(item => item.tempMin),
        borderColor: 'rgb(54, 162, 235)',
        backgroundColor: 'rgba(54, 162, 235, 0.1)',
        type: 'line',
        yAxisID: 'y-temp',
        pointRadius: 3,
        tension: 0.2,
        borderWidth: 2,
        spanGaps: false, // Don't connect across null values
      },
      {
        label: 'Max Temperature (°F)',
        data: hourlyData.map(item => item.tempMax),
        borderColor: 'rgb(255, 99, 132)',
        backgroundColor: 'rgba(255, 99, 132, 0.1)',
        type: 'line',
        yAxisID: 'y-temp',
        pointRadius: 3,
        tension: 0.2,
        borderWidth: 2,
        spanGaps: false,
      },
      {
        label: 'Avg Temperature (°F)',
        data: hourlyData.map(item => item.tempAvg),
        borderColor: 'rgb(255, 206, 86)',
        backgroundColor: 'rgba(255, 206, 86, 0.1)',
        type: 'line',
        yAxisID: 'y-temp',
        pointRadius: 3,
        tension: 0.2,
        borderWidth: 2,
        spanGaps: false,
      },
      // Precipitation Bars
      {
        label: 'Precipitation (in)',
        data: hourlyData.map(item => item.precipitation),
        backgroundColor: 'rgba(75, 192, 192, 0.6)',
        borderColor: 'rgb(75, 192, 192)',
        type: 'bar',
        yAxisID: 'y-precip',
        borderWidth: 1,
      },
      // ETO Bars
      {
        label: 'ETO Forecast (in)',
        data: hourlyData.map(item => item.eto),
        backgroundColor: 'rgba(153, 102, 255, 0.6)',
        borderColor: 'rgb(153, 102, 255)',
        type: 'bar',
        yAxisID: 'y-precip',
        borderWidth: 1,
      },
    ],
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
        text: 'Historical Weather + ETO Forecast',
        font: {
          size: 16,
          weight: 'bold',
        },
      },
      tooltip: {
        mode: 'index',
        intersect: false,
        callbacks: {
          label: function(context) {
            let label = context.dataset.label || '';
            if (label) {
              label += ': ';
            }
            if (context.parsed.y !== null) {
              if (label.includes('Temperature')) {
                label += context.parsed.y.toFixed(1) + '°F';
              } else {
                label += context.parsed.y.toFixed(2) + ' in';
              }
            }
            return label;
          }
        }
      },
    },
    scales: {
      'y-temp': {
        type: 'linear',
        display: true,
        position: 'left',
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
      'y-precip': {
        type: 'linear',
        display: true,
        position: 'right',
        beginAtZero: true,
        title: {
          display: true,
          text: 'Precipitation & ETO (inches)',
          color: '#333',
          font: {
            weight: 'bold',
          },
        },
        grid: {
          drawOnChartArea: false, // Prevents grid overlap
        },
      },
      x: {
        grid: {
          color: 'rgba(0,0,0,0.05)',
        },
      },
    },
  };

  return <Chart type='bar' data={chartData} options={options} />;
}

export default CombinedWeatherChart;