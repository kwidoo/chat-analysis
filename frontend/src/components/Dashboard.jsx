import React, { useEffect, useState } from "react";
import {
  ResponsiveContainer,
  ComposedChart,
  Line,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from "recharts";

const Dashboard = () => {
  const [data, setData] = useState([]);
  const [searchQuery, setSearchQuery] = useState("");

  useEffect(() => {
    fetch("/api/visualization")
      .then((res) => res.json())
      .then(setData);
  }, []);

  const handleSearch = (e) => {
    setSearchQuery(e.target.value);
    fetch(`/api/search?q=${encodeURIComponent(e.target.value)}`)
      .then((res) => res.json())
      .then((results) => console.log(results));
  };

  return (
    <div>
      <div className="mb-6">
        <input
          type="text"
          value={searchQuery}
          onChange={handleSearch}
          placeholder="Search messages..."
          className="w-full p-3 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500 transition-colors"
        />
      </div>

      <div className="bg-white p-4 rounded-lg shadow-sm">
        <h3 className="text-lg font-semibold mb-4 text-gray-700">
          Data Visualization
        </h3>
        <ResponsiveContainer width="100%" height={400}>
          <ComposedChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" />
            <YAxis />
            <Tooltip
              contentStyle={{
                backgroundColor: "rgba(255, 255, 255, 0.95)",
                borderRadius: "6px",
                padding: "10px",
              }}
            />
            <Legend />
            <Bar dataKey="messages" fill="#8884d8" radius={[4, 4, 0, 0]} />
            <Line
              type="monotone"
              dataKey="sentiment"
              stroke="#82ca9d"
              strokeWidth={2}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

export default Dashboard;
