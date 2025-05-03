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
    return (
      <div className="text-center p-5 italic text-gray-500">
        Loading queue status...
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-3 mb-3 bg-red-50 text-red-800 rounded-md border-l-4 border-red-600">
        {error}
      </div>
    );
  }

  // Calculate completion percentage
  const totalItems = queueData.stats.total;
  const completedItems = queueData.stats.processed + queueData.stats.failed;
  const completionPercentage =
    totalItems > 0 ? Math.round((completedItems / totalItems) * 100) : 0;

  return (
    <div className="mt-5">
      <h3 className="text-xl font-semibold mb-4">Processing Queue Status</h3>

      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div className="p-4 bg-gray-50 rounded-md text-center">
          <span className="block mb-2 text-gray-600 font-medium">Pending:</span>
          <span className="text-2xl font-bold text-gray-800">
            {queueData.queue_length}
          </span>
        </div>

        <div className="p-4 bg-gray-50 rounded-md text-center">
          <span className="block mb-2 text-gray-600 font-medium">
            Total Submitted:
          </span>
          <span className="text-2xl font-bold text-gray-800">
            {queueData.stats.total}
          </span>
        </div>

        <div className="p-4 bg-gray-50 rounded-md text-center">
          <span className="block mb-2 text-gray-600 font-medium">
            Processed:
          </span>
          <span className="text-2xl font-bold text-gray-800">
            {queueData.stats.processed}
          </span>
        </div>

        <div className="p-4 bg-gray-50 rounded-md text-center">
          <span className="block mb-2 text-gray-600 font-medium">Failed:</span>
          <span className="text-2xl font-bold text-gray-800">
            {queueData.stats.failed}
          </span>
        </div>
      </div>

      <div className="mt-6">
        <div className="font-bold mb-2">
          Overall Progress: {completionPercentage}%
        </div>
        <div className="h-5 bg-gray-200 rounded-full overflow-hidden">
          <div
            className="h-full bg-green-600 transition-all duration-500"
            style={{ width: `${completionPercentage}%` }}
          />
        </div>
      </div>
    </div>
  );
};

export default QueueStatus;
