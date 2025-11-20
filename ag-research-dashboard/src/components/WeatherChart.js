// src/components/WeatherChart.js

import React from "react";
import { Line } from "react-chartjs-2";
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend } from 'chart.js';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend);

function WeatherChart({ data }) {
  const chartData = {
    labels: data.map(d => new Date(d.timestamp).toLocaleTimeString()),
    datasets: [
      {
        label: "Temperature (°C)",
        data: data.map(d => d.temp),
        borderColor: "#FDB719", /* Mizzou Gold */
        backgroundColor: "rgba(253, 183, 25, 0.5)", /* Mizzou Gold with transparency */
        tension: 0.1
      },
    ],
  };


  const options = {
    responsive: true,
    plugins: {
      legend: { position: 'top' },
      title: { display: true, text: 'Temperature Trend' },
    },
  };

  return <Line options={options} data={chartData} />;
}

export default WeatherChart;