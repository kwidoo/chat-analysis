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
    <div className="mt-5">
      <h3 className="text-xl font-semibold mb-3">Model Version Control</h3>

      {error && (
        <div className="my-2 p-3 bg-red-50 text-red-800 rounded-md border-l-4 border-red-600">
          {error}
        </div>
      )}

      <div className="my-4 p-3 bg-gray-50 rounded-md border-l-4 border-gray-500">
        <span className="font-semibold">Current Model:</span> {activeModel}
        {loading && (
          <span className="italic text-blue-600 ml-2">(Switching...)</span>
        )}
      </div>

      <div className="flex gap-2 my-5">
        <button
          onClick={() => switchModel("v1")}
          disabled={loading || activeModel === "v1"}
          className={`flex-1 py-2 px-4 rounded-md border transition-all ${
            activeModel === "v1"
              ? "bg-green-600 text-white border-green-600"
              : "bg-gray-100 hover:bg-gray-200 text-gray-800 border-gray-300 disabled:opacity-60 disabled:cursor-not-allowed"
          }`}
        >
          Model v1: all-MiniLM-L6-v2
        </button>

        <button
          onClick={() => switchModel("v2")}
          disabled={loading || activeModel === "v2"}
          className={`flex-1 py-2 px-4 rounded-md border transition-all ${
            activeModel === "v2"
              ? "bg-green-600 text-white border-green-600"
              : "bg-gray-100 hover:bg-gray-200 text-gray-800 border-gray-300 disabled:opacity-60 disabled:cursor-not-allowed"
          }`}
        >
          Model v2: all-mpnet-base-v2
        </button>
      </div>

      <div className="mt-5 p-4 bg-gray-50 rounded-md">
        <p className="mb-2">
          <span className="font-semibold">Model v1:</span> Efficient smaller
          model, faster processing
        </p>
        <p>
          <span className="font-semibold">Model v2:</span> Larger model with
          improved accuracy
        </p>
      </div>
    </div>
  );
};

export default ModelVersionControl;
