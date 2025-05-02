import React, { useState, useEffect } from "react";
import "./App.css";
import Dashboard from "./components/Dashboard";
import SearchBar from "./components/SearchBar";
import ModelVersionControl from "./components/ModelVersionControl";
import QueueStatus from "./components/QueueStatus";

function App() {
    const [files, setFiles] = useState([]);
    const [taskId, setTaskId] = useState(null);
    const [taskStatus, setTaskStatus] = useState(null);
    const [viewMode, setViewMode] = useState('upload'); // 'upload', 'dashboard', 'search', 'models', 'queue'

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
            const response = await fetch("http://localhost:5000/upload", {
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
                const response = await fetch(`http://localhost:5000/status/${id}`);
                const data = await response.json();
                setTaskStatus(`Status: ${data.status} (Processed: ${data.queue_stats?.processed || 0}, Failed: ${data.queue_stats?.failed || 0})`);

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

    return (
        <div className="App">
            <header>
                <h1>Text Analysis Dashboard</h1>
                <nav>
                    <button onClick={() => setViewMode('upload')}>Upload</button>
                    <button onClick={() => setViewMode('dashboard')}>Dashboard</button>
                    <button onClick={() => setViewMode('search')}>Search</button>
                    <button onClick={() => setViewMode('models')}>Models</button>
                    <button onClick={() => setViewMode('queue')}>Queue Status</button>
                </nav>
            </header>

            {viewMode === 'upload' && (
                <div className="upload-container">
                    <h2>Upload Files</h2>
                    <form onSubmit={handleSubmit}>
                        <input type="file" multiple onChange={handleFileChange} />
                        <button type="submit">Upload and Process</button>
                    </form>
                    {taskId && <p>Task ID: {taskId}</p>}
                    {taskStatus && <p>{taskStatus}</p>}
                </div>
            )}

            {viewMode === 'dashboard' && (
                <div className="dashboard-container">
                    <h2>Analysis Dashboard</h2>
                    <Dashboard />
                </div>
            )}

            {viewMode === 'search' && (
                <div className="search-container">
                    <h2>Search Documents</h2>
                    <SearchBar onSearch={handleSearchResults} />
                </div>
            )}

            {viewMode === 'models' && (
                <div className="models-container">
                    <h2>Model Management</h2>
                    <ModelVersionControl />
                </div>
            )}

            {viewMode === 'queue' && (
                <div className="queue-container">
                    <h2>Processing Queue</h2>
                    <QueueStatus />
                </div>
            )}
        </div>
    );
}

export default App;
