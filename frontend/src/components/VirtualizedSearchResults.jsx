import React, { useState, useMemo } from "react";
import PropTypes from "prop-types";
import { FixedSizeList as List } from "react-window";
import AutoSizer from "react-virtualized-auto-sizer";
import SearchResultCard from "./SearchResultCard";

const VirtualizedSearchResults = ({ results, onResultSelect }) => {
  const [sortBy, setSortBy] = useState("similarity"); // similarity, date, title
  const [sortDirection, setSortDirection] = useState("desc"); // asc, desc
  const [filterText, setFilterText] = useState("");
  const [filterTags, setFilterTags] = useState([]);

  // Extract all unique tags from results for filter options
  const allTags = useMemo(() => {
    const tags = new Set();
    results.forEach((result) => {
      if (result.tags) {
        result.tags.forEach((tag) => tags.add(tag));
      }
    });
    return Array.from(tags);
  }, [results]);

  // Apply sorting and filtering to results
  const processedResults = useMemo(() => {
    // Filter results based on filterText and filterTags
    let filtered = results;

    if (filterText) {
      const lowerFilter = filterText.toLowerCase();
      filtered = filtered.filter(
        (result) =>
          result.title.toLowerCase().includes(lowerFilter) ||
          result.content.toLowerCase().includes(lowerFilter)
      );
    }

    if (filterTags.length > 0) {
      filtered = filtered.filter(
        (result) =>
          result.tags && filterTags.some((tag) => result.tags.includes(tag))
      );
    }

    // Sort the filtered results
    return filtered.sort((a, b) => {
      let comparison = 0;
      switch (sortBy) {
        case "similarity":
          comparison = b.similarity - a.similarity;
          break;
        case "date":
          comparison = new Date(b.timestamp || 0) - new Date(a.timestamp || 0);
          break;
        case "title":
          comparison = a.title.localeCompare(b.title);
          break;
        default:
          comparison = b.similarity - a.similarity;
      }
      return sortDirection === "asc" ? -comparison : comparison;
    });
  }, [results, sortBy, sortDirection, filterText, filterTags]);

  // Toggle sort direction or change sort field
  const handleSortChange = (field) => {
    if (sortBy === field) {
      setSortDirection(sortDirection === "asc" ? "desc" : "asc");
    } else {
      setSortBy(field);
      setSortDirection("desc");
    }
  };

  // Toggle tag filter
  const toggleTagFilter = (tag) => {
    setFilterTags((prev) =>
      prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag]
    );
  };

  // Render each item in the virtualized list
  const Row = ({ index, style }) => {
    const result = processedResults[index];
    return (
      <div style={style}>
        <SearchResultCard result={result} onSelect={onResultSelect} />
      </div>
    );
  };

  return (
    <div className="flex flex-col h-full">
      <div className="mb-4 p-4 bg-gray-50 rounded-lg border border-gray-200">
        <div className="flex flex-wrap gap-4 justify-between items-center">
          {/* Filter controls */}
          <div className="flex-1">
            <input
              type="text"
              value={filterText}
              onChange={(e) => setFilterText(e.target.value)}
              placeholder="Filter results..."
              className="w-full p-2 border border-gray-300 rounded-md"
            />
          </div>

          {/* Sort controls */}
          <div className="flex space-x-2 items-center">
            <span className="text-sm text-gray-600">Sort by:</span>
            <button
              onClick={() => handleSortChange("similarity")}
              className={`px-3 py-1 text-sm rounded-md ${
                sortBy === "similarity"
                  ? "bg-blue-600 text-white"
                  : "bg-gray-200 text-gray-800"
              }`}
            >
              Relevance{" "}
              {sortBy === "similarity" &&
                (sortDirection === "desc" ? "↓" : "↑")}
            </button>
            <button
              onClick={() => handleSortChange("date")}
              className={`px-3 py-1 text-sm rounded-md ${
                sortBy === "date"
                  ? "bg-blue-600 text-white"
                  : "bg-gray-200 text-gray-800"
              }`}
            >
              Date {sortBy === "date" && (sortDirection === "desc" ? "↓" : "↑")}
            </button>
            <button
              onClick={() => handleSortChange("title")}
              className={`px-3 py-1 text-sm rounded-md ${
                sortBy === "title"
                  ? "bg-blue-600 text-white"
                  : "bg-gray-200 text-gray-800"
              }`}
            >
              Title{" "}
              {sortBy === "title" && (sortDirection === "desc" ? "↓" : "↑")}
            </button>
          </div>
        </div>

        {/* Tag filters */}
        {allTags.length > 0 && (
          <div className="mt-3">
            <div className="text-sm text-gray-600 mb-1">Filter by tag:</div>
            <div className="flex flex-wrap gap-2">
              {allTags.map((tag) => (
                <button
                  key={tag}
                  onClick={() => toggleTagFilter(tag)}
                  className={`px-2 py-1 text-xs rounded-full ${
                    filterTags.includes(tag)
                      ? "bg-blue-600 text-white"
                      : "bg-gray-200 text-gray-800"
                  }`}
                >
                  {tag}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Results count */}
      <div className="mb-2 text-sm text-gray-600">
        Showing {processedResults.length} of {results.length} results
      </div>

      {/* Virtualized list of results */}
      <div
        className="flex-1"
        style={{ height: "calc(100vh - 300px)", minHeight: "400px" }}
      >
        {processedResults.length > 0 ? (
          <AutoSizer>
            {({ height, width }) => (
              <List
                height={height}
                width={width}
                itemCount={processedResults.length}
                itemSize={180} // Approximate height of each card
              >
                {Row}
              </List>
            )}
          </AutoSizer>
        ) : (
          <div className="h-full flex items-center justify-center bg-gray-50 rounded-lg border border-gray-200">
            <p className="text-gray-500">No results match your filters</p>
          </div>
        )}
      </div>
    </div>
  );
};

VirtualizedSearchResults.propTypes = {
  results: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.string.isRequired,
      title: PropTypes.string.isRequired,
      content: PropTypes.string.isRequired,
      similarity: PropTypes.number.isRequired,
      source: PropTypes.string,
      timestamp: PropTypes.string,
      tags: PropTypes.arrayOf(PropTypes.string),
    })
  ).isRequired,
  onResultSelect: PropTypes.func.isRequired,
};

export default VirtualizedSearchResults;
