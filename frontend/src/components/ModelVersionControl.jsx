import React, { useState, useEffect } from "react";

const ModelVersionControl = () => {
  const [activeModel, setActiveModel] = useState("v1");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Fetch the current active model on component mount
  useEffect(() => {
    fetch("/api/health")
      .then((response) => response.json())
      .then((data) => {
        setActiveModel(data.model);
      })
      .catch((err) => {
        setError("Failed to fetch model status");
        console.error("Error fetching model status:", err);
      });
  }, []);

  const switchModel = async (version) => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`/api/models/switch/${version}`);

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      setActiveModel(data.active_model);
    } catch (err) {
      setError(`Failed to switch model: ${err.message}`);
      console.error("Error switching model:", err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="model-version-control">
      <h3>Model Version Control</h3>

      {error && <div className="error-message">{error}</div>}

      <div className="model-status">
        <strong>Current Model:</strong> {activeModel}
        {loading && <span className="loading-indicator"> (Switching...)</span>}
      </div>

      <div className="model-switcher">
        <button
          onClick={() => switchModel("v1")}
          disabled={loading || activeModel === "v1"}
          className={activeModel === "v1" ? "active" : ""}
        >
          Model v1: all-MiniLM-L6-v2
        </button>

        <button
          onClick={() => switchModel("v2")}
          disabled={loading || activeModel === "v2"}
          className={activeModel === "v2" ? "active" : ""}
        >
          Model v2: all-mpnet-base-v2
        </button>
      </div>

      <div className="model-info">
        <p>
          <strong>Model v1:</strong> Efficient smaller model, faster processing
        </p>
        <p>
          <strong>Model v2:</strong> Larger model with improved accuracy
        </p>
      </div>
    </div>
  );
};

export default ModelVersionControl;
