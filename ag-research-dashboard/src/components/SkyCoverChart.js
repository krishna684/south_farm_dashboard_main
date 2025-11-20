// src/components/SkyCoverChart.js
import React from 'react';
import { Line } from 'react-chartjs-2';
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend } from 'chart.js';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend);

function SkyCoverChart({ hourlyData }) {
  const chartData = {
    labels: hourlyData.map(item => item.time),
    datasets: [
      {
        label: 'Sky Cover (%)',
        data: hourlyData.map(item => item.skyCover),
        borderColor: 'rgb(108, 117, 125)',
        backgroundColor: 'rgba(108, 117, 125, 0.2)',
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
      },
      title: {
        display: true,
        text: 'Sky Cover',
      },
      tooltip: {
        mode: 'index',
        intersect: false,
      },
    },
    scales: {
      y: {
        beginAtZero: true,
        max: 100,
      },
    },
  };

  return <Line data={chartData} options={options} />;
}

export default SkyCoverChart;