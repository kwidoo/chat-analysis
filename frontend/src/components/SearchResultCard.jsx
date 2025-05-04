import React from "react";
import PropTypes from "prop-types";

const SearchResultCard = ({ result, onSelect }) => {
  const { id, title, content, similarity, source, timestamp } = result;

  // Format the similarity score as a percentage
  const similarityPercentage = (similarity * 100).toFixed(1);

  // Determine color based on similarity score
  const getSimilarityColor = (score) => {
    if (score >= 0.8) return "bg-green-500";
    if (score >= 0.6) return "bg-blue-500";
    if (score >= 0.4) return "bg-yellow-500";
    return "bg-red-500";
  };

  // Create a formatted date string if timestamp is available
  const formattedDate = timestamp
    ? new Date(timestamp).toLocaleString()
    : "No date";

  // Truncate content if it's too long
  const truncateContent = (text, maxLength = 150) => {
    if (text.length <= maxLength) return text;
    return text.slice(0, maxLength) + "...";
  };

  return (
    <div
      className="border rounded-lg p-4 mb-4 bg-white shadow-sm hover:shadow-md transition-shadow cursor-pointer"
      onClick={() => onSelect(id)}
      data-testid="search-result-card"
    >
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-lg font-medium text-gray-900 truncate">{title}</h3>
        <div className="flex items-center">
          <div
            className={`${getSimilarityColor(
              similarity
            )} w-6 h-6 rounded-full flex items-center justify-center mr-2`}
          >
            <span className="text-xs text-white font-bold">
              {similarityPercentage}%
            </span>
          </div>
          <div className="text-sm text-gray-500">{formattedDate}</div>
        </div>
      </div>

      <p className="text-gray-600 text-sm mb-3">{truncateContent(content)}</p>

      <div className="flex justify-between items-center">
        <div className="text-xs text-gray-500">
          Source: {source || "Unknown"}
        </div>
        <div className="flex space-x-2">
          {/* Visual similarity meter */}
          <div className="w-32 h-2 bg-gray-200 rounded-full overflow-hidden">
            <div
              className={`h-full ${getSimilarityColor(similarity)}`}
              style={{ width: `${similarityPercentage}%` }}
            ></div>
          </div>
        </div>
      </div>

      {/* Tags if available */}
      {result.tags && result.tags.length > 0 && (
        <div className="flex flex-wrap gap-2 mt-2">
          {result.tags.map((tag, index) => (
            <span
              key={index}
              className="px-2 py-1 text-xs bg-gray-100 text-gray-800 rounded-full"
            >
              {tag}
            </span>
          ))}
        </div>
      )}
    </div>
  );
};

SearchResultCard.propTypes = {
  result: PropTypes.shape({
    id: PropTypes.string.isRequired,
    title: PropTypes.string.isRequired,
    content: PropTypes.string.isRequired,
    similarity: PropTypes.number.isRequired,
    source: PropTypes.string,
    timestamp: PropTypes.string,
    tags: PropTypes.arrayOf(PropTypes.string),
  }).isRequired,
  onSelect: PropTypes.func.isRequired,
};

export default SearchResultCard;
