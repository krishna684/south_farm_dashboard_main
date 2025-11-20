// src/components/TemperatureChart.js
import React from 'react';
import { Line } from 'react-chartjs-2';
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend } from 'chart.js';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend);

function TemperatureChart({ hourlyData }) {
  const chartData = {
    labels: hourlyData.map(item => item.time),
    datasets: [
      {
        label: 'Temperature (°F)',
        data: hourlyData.map(item => item.temp),
        borderColor: 'rgb(255, 99, 132)',
        backgroundColor: 'rgba(255, 99, 132, 0.2)',
        pointRadius: 1,
        tension: 0.2,
      },
      {
        label: 'Dewpoint (°F)',
        data: hourlyData.map(item => item.dewpoint),
        borderColor: 'rgb(54, 162, 235)',
        backgroundColor: 'rgba(54, 162, 235, 0.2)',
        pointRadius: 1,
        tension: 0.2,
      },
      {
        label: 'Heat Index (°F)',
        data: hourlyData.map(item => item.heatIndex),
        borderColor: 'rgb(255, 206, 86)',
        backgroundColor: 'rgba(255, 206, 86, 0.2)',
        pointRadius: 1,
        tension: 0.2,
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
        text: 'Temperature, Dewpoint, & Heat Index',
      },
      tooltip: {
        mode: 'index',
        intersect: false,
      },
    },
    scales: {
      y: {
        beginAtZero: false,
      },
    },
  };

  return <Line data={chartData} options={options} />;
}

export default TemperatureChart;
