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
      <input
        type="text"
        value={searchQuery}
        onChange={handleSearch}
        placeholder="Search messages..."
      />

      <ResponsiveContainer width="100%" height={400}>
        <ComposedChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="name" />
          <YAxis />
          <Tooltip />
          <Legend />
          <Bar dataKey="messages" fill="#8884d8" />
          <Line type="monotone" dataKey="sentiment" stroke="#82ca9d" />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
};

export default Dashboard;
