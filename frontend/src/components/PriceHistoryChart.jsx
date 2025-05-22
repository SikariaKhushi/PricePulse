import React from "react";
import { Line } from "react-chartjs-2";
import { Chart, LineElement, CategoryScale, LinearScale, PointElement, Tooltip, Legend } from "chart.js";

Chart.register(LineElement, CategoryScale, LinearScale, PointElement, Tooltip, Legend);

export default function PriceHistoryChart({ history }) {
  if (!history || history.length === 0) return <p>No price history available.</p>;

  const data = {
    labels: history.map(item => new Date(item.timestamp).toLocaleString()),
    datasets: [
      {
        label: "Price (₹)",
        data: history.map(item => item.price),
        borderColor: "#2563eb",
        backgroundColor: "rgba(37,99,235,0.1)",
        fill: true,
        tension: 0.3,
      },
    ],
  };

  return (
    <div className="bg-white rounded shadow p-4 mt-4">
      <h3 className="font-semibold mb-2">Price History</h3>
      <Line data={data} />
    </div>
  );
}
