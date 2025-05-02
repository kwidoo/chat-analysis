import React, { useState, useEffect } from "react";

const QueueStatus = () => {
  const [queueData, setQueueData] = useState({
    queue_length: 0,
    stats: {
      total: 0,
      processed: 0,
      failed: 0,
    },
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchQueueStatus = async () => {
      try {
        const response = await fetch("/api/queue/status");
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        setQueueData(data);
        setError(null);
      } catch (err) {
        setError("Failed to fetch queue status");
        console.error("Error fetching queue status:", err);
      } finally {
        setLoading(false);
      }
    };

    // Initial fetch
    fetchQueueStatus();

    // Set up polling interval - check every 5 seconds
    const intervalId = setInterval(fetchQueueStatus, 5000);

    // Clean up interval on component unmount
    return () => clearInterval(intervalId);
  }, []);

  if (loading) {
    return <div className="loading">Loading queue status...</div>;
  }

  if (error) {
    return <div className="error-message">{error}</div>;
  }

  // Calculate completion percentage
  const totalItems = queueData.stats.total;
  const completedItems = queueData.stats.processed + queueData.stats.failed;
  const completionPercentage =
    totalItems > 0 ? Math.round((completedItems / totalItems) * 100) : 0;

  return (
    <div className="queue-status">
      <h3>Processing Queue Status</h3>

      <div className="queue-metrics">
        <div className="metric">
          <span className="label">Pending:</span>
          <span className="value">{queueData.queue_length}</span>
        </div>

        <div className="metric">
          <span className="label">Total Submitted:</span>
          <span className="value">{queueData.stats.total}</span>
        </div>

        <div className="metric">
          <span className="label">Processed:</span>
          <span className="value">{queueData.stats.processed}</span>
        </div>

        <div className="metric">
          <span className="label">Failed:</span>
          <span className="value">{queueData.stats.failed}</span>
        </div>
      </div>

      <div className="progress-container">
        <div className="progress-label">
          Overall Progress: {completionPercentage}%
        </div>
        <div className="progress-bar">
          <div
            className="progress-fill"
            style={{ width: `${completionPercentage}%` }}
          />
        </div>
      </div>
    </div>
  );
};

export default QueueStatus;
