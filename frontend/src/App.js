import React, { useState } from "react";
import "./App.css";

function App() {
    const [files, setFiles] = useState([]);
    const [labels, setLabels] = useState([]);

    const handleFileChange = (event) => {
        setFiles(event.target.files);
    };

    const handleSubmit = async (event) => {
        event.preventDefault();
        const formData = new FormData();
        for (let i = 0; i < files.length; i++) {
            formData.append("files", files[i]);
        }

        const response = await fetch("http://localhost:5000/upload", {
            method: "POST",
            body: formData,
        });

        const result = await response.json();
        setLabels(result.labels);
    };

    return (
        <div className="App">
            <h1>Chat Analysis</h1>
            <form onSubmit={handleSubmit}>
                <input type="file" multiple onChange={handleFileChange} />
                <button type="submit">Upload and Analyze</button>
            </form>
            {labels.length > 0 && (
                <div>
                    <h2>Cluster Labels</h2>
                    <ul>
                        {labels.map((label, index) => (
                            <li key={index}>
                                Message {index}: Cluster {label}
                            </li>
                        ))}
                    </ul>
                </div>
            )}
        </div>
    );
}

export default App;
