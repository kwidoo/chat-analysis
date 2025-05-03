import React, { useState } from "react";
import { Routes, Route, Link, useNavigate } from "react-router-dom";
import Dashboard from "./components/Dashboard";
import SearchBar from "./components/SearchBar";
import ModelVersionControl from "./components/ModelVersionControl";
import QueueStatus from "./components/QueueStatus";

function App() {
  const [files, setFiles] = useState([]);
  const [taskId, setTaskId] = useState(null);
  const [taskStatus, setTaskStatus] = useState(null);
  const navigate = useNavigate();

  const handleFileChange = (event) => {
    setFiles(event.target.files);
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    const formData = new FormData();
    for (let i = 0; i < files.length; i++) {
      formData.append("files", files[i]);
    }

    try {
      const response = await fetch("/api/upload", {
        method: "POST",
        body: formData,
      });

      const result = await response.json();
      setTaskId(result.task_id);
      setTaskStatus("Processing started...");

      // Poll for status
      if (result.task_id) {
        pollTaskStatus(result.task_id);
      }
    } catch (error) {
      console.error("Upload error:", error);
      setTaskStatus("Upload failed");
    }
  };

  const pollTaskStatus = (id) => {
    const interval = setInterval(async () => {
      try {
        const response = await fetch(`/api/status/${id}`);
        const data = await response.json();
        setTaskStatus(
          `Status: ${data.status} (Processed: ${
            data.queue_stats?.processed || 0
          }, Failed: ${data.queue_stats?.failed || 0})`
        );

        // If processing is complete, stop polling
        if (data.status === "completed") {
          clearInterval(interval);
        }
      } catch (error) {
        console.error("Status check error:", error);
        clearInterval(interval);
      }
    }, 2000);
  };

  const handleSearchResults = (results) => {
    console.log("Search results:", results);
    // You could update some state here to display the results in the UI
  };

  // Upload component
  const UploadForm = () => (
    <div className="bg-white p-6 rounded-lg shadow-md">
      <h2 className="text-2xl font-semibold mb-4">Upload Files</h2>
      <form onSubmit={handleSubmit} className="flex flex-col mb-4">
        <input
          type="file"
          multiple
          onChange={handleFileChange}
          className="mb-4"
        />
        <button
          type="submit"
          className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 transition-colors cursor-pointer"
        >
          Upload and Process
        </button>
      </form>
      {taskId && (
        <p className="p-3 bg-blue-50 border-l-4 border-blue-500 mb-4">
          Task ID: {taskId}
        </p>
      )}
      {taskStatus && (
        <p className="p-3 bg-blue-50 border-l-4 border-blue-500 mb-4">
          {taskStatus}
        </p>
      )}
    </div>
  );

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 font-sans">
      <header className="mb-8">
        <h1 className="text-3xl font-bold text-center text-gray-800 mb-6">
          Text Analysis Dashboard
        </h1>
        <nav className="flex justify-center gap-3 my-5">
          <Link
            to="/"
            className={`px-4 py-2 rounded-md transition-colors bg-gray-200 text-gray-800 hover:bg-gray-300`}
          >
            Upload
          </Link>
          <Link
            to="/dashboard"
            className={`px-4 py-2 rounded-md transition-colors bg-gray-200 text-gray-800 hover:bg-gray-300`}
          >
            Dashboard
          </Link>
          <Link
            to="/search"
            className={`px-4 py-2 rounded-md transition-colors bg-gray-200 text-gray-800 hover:bg-gray-300`}
          >
            Search
          </Link>
          <Link
            to="/models"
            className={`px-4 py-2 rounded-md transition-colors bg-gray-200 text-gray-800 hover:bg-gray-300`}
          >
            Models
          </Link>
          <Link
            to="/queue"
            className={`px-4 py-2 rounded-md transition-colors bg-gray-200 text-gray-800 hover:bg-gray-300`}
          >
            Queue Status
          </Link>
        </nav>
      </header>

      <Routes>
        <Route path="/" element={<UploadForm />} />
        <Route
          path="/dashboard"
          element={
            <div className="bg-white p-6 rounded-lg shadow-md">
              <h2 className="text-2xl font-semibold mb-4">
                Analysis Dashboard
              </h2>
              <Dashboard />
            </div>
          }
        />
        <Route
          path="/search"
          element={
            <div className="bg-white p-6 rounded-lg shadow-md">
              <h2 className="text-2xl font-semibold mb-4">Search Documents</h2>
              <SearchBar onSearch={handleSearchResults} />
            </div>
          }
        />
        <Route
          path="/models"
          element={
            <div className="bg-white p-6 rounded-lg shadow-md">
              <h2 className="text-2xl font-semibold mb-4">Model Management</h2>
              <ModelVersionControl />
            </div>
          }
        />
        <Route
          path="/queue"
          element={
            <div className="bg-white p-6 rounded-lg shadow-md">
              <h2 className="text-2xl font-semibold mb-4">Processing Queue</h2>
              <QueueStatus />
            </div>
          }
        />
      </Routes>
    </div>
  );
}

export default App;
