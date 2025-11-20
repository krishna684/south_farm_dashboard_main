// src/components/HumidityPrecipitationChart.js
import React from 'react';
import { Line } from 'react-chartjs-2';
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend } from 'chart.js';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend);

function HumidityPrecipitationChart({ hourlyData }) {
  const chartData = {
    labels: hourlyData.map(item => item.time),
    datasets: [
      {
        label: 'Relative Humidity (%)',
        data: hourlyData.map(item => item.relativeHumidity),
        borderColor: 'rgb(153, 102, 255)',
        backgroundColor: 'rgba(153, 102, 255, 0.2)',
        yAxisID: 'y-humidity',
        tension: 0.2,
        pointRadius: 1,
      },
      {
        label: 'Precipitation Potential (%)',
        data: hourlyData.map(item => item.precipitationPotential),
        borderColor: 'rgb(0, 123, 255)',
        backgroundColor: 'rgba(0, 123, 255, 0.2)',
        yAxisID: 'y-precipitation',
        tension: 0.2,
        pointRadius: 1,
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
          boxWidth: 15,
          usePointStyle: true,
        },
      },
      title: {
        display: true,
        text: 'Relative Humidity & Precipitation Potential',
      },
      tooltip: {
        mode: 'index',
        intersect: false,
      },
    },
    scales: {
      'y-humidity': {
        type: 'linear',
        display: true,
        position: 'left',
        beginAtZero: true,
        title: {
          display: true,
          text: 'Humidity (%)',
        },
      },
      'y-precipitation': {
        type: 'linear',
        display: true,
        position: 'right',
        beginAtZero: true,
        title: {
          display: true,
          text: 'Precipitation (%)',
        },
        grid: {
          drawOnChartArea: false, // To avoid overlapping grids
        },
      },
    },
  };

  return <Line data={chartData} options={options} />;
}

export default HumidityPrecipitationChart;