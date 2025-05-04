import React, { useState, useEffect, useRef } from "react";
import SearchResultCard from "./SearchResultCard";
import VirtualizedSearchResults from "./VirtualizedSearchResults";

const SearchBar = ({ onSearch }) => {
  const [query, setQuery] = useState("");
  const [advancedMode, setAdvancedMode] = useState(false);
  const [jsonQuery, setJsonQuery] = useState(
    '{\n  "query": "",\n  "filters": {},\n  "options": {\n    "limit": 10,\n    "threshold": 0.7\n  }\n}'
  );
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [suggestions, setSuggestions] = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [queryMode, setQueryMode] = useState("semantic"); // semantic, keyword, hybrid
  const [useVirtualized, setUseVirtualized] = useState(false);
  const searchInputRef = useRef(null);

  // Debounce function for suggestions
  const debounce = (func, delay) => {
    let timeoutId;
    return (...args) => {
      clearTimeout(timeoutId);
      timeoutId = setTimeout(() => func(...args), delay);
    };
  };

  // Generate query suggestions based on input
  const generateSuggestions = debounce(async (input) => {
    if (input.length < 3) {
      setSuggestions([]);
      return;
    }

    try {
      const response = await fetch("/api/search/suggest", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ input }),
      });

      if (!response.ok) throw new Error("Failed to get suggestions");

      const data = await response.json();
      setSuggestions(data.suggestions || []);
      setShowSuggestions(true);
    } catch (err) {
      console.error("Error getting suggestions:", err);
      setSuggestions([]);
    }
  }, 300);

  // Handle natural language query conversion
  const processNaturalLanguage = async (nlQuery) => {
    try {
      const response = await fetch("/api/search/process-nl", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: nlQuery }),
      });

      if (!response.ok) return null;

      const data = await response.json();
      return data.structured_query;
    } catch (err) {
      console.error("NL processing error:", err);
      return null;
    }
  };

  // Update JSON query when standard query changes
  useEffect(() => {
    try {
      const queryObj = JSON.parse(jsonQuery);
      queryObj.query = query;
      setJsonQuery(JSON.stringify(queryObj, null, 2));
    } catch (err) {
      // If JSON is invalid, don't update
      console.error("Invalid JSON in query builder");
    }
  }, [query]);

  // Monitor changes in the search query and generate suggestions
  useEffect(() => {
    if (query.trim()) {
      generateSuggestions(query);
    } else {
      setSuggestions([]);
      setShowSuggestions(false);
    }
  }, [query]);

  // Close suggestions when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (
        searchInputRef.current &&
        !searchInputRef.current.contains(event.target)
      ) {
        setShowSuggestions(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Automatically switch to virtualized mode when results exceed threshold
  useEffect(() => {
    if (results.length > 20 && !useVirtualized) {
      setUseVirtualized(true);
    }
  }, [results.length]);

  const handleSearch = async (e) => {
    e?.preventDefault();
    setLoading(true);
    setError(null);

    try {
      let searchPayload;

      if (advancedMode) {
        // Use the JSON query directly in advanced mode
        try {
          searchPayload = JSON.parse(jsonQuery);
        } catch (err) {
          setError("Invalid JSON query. Please check your syntax.");
          setLoading(false);
          return;
        }
      } else {
        // Basic mode - construct search payload based on query and mode
        searchPayload = {
          q: query,
          mode: queryMode,
          limit: 10,
        };

        // If NLP mode is enabled, try to process natural language query
        if (queryMode === "semantic" || queryMode === "hybrid") {
          const nlResult = await processNaturalLanguage(query);
          if (nlResult) {
            searchPayload.structured_query = nlResult;
          }
        }
      }

      const response = await fetch("/api/search", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${localStorage.getItem("accessToken")}`,
        },
        body: JSON.stringify(searchPayload),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || "Search failed");
      }

      const data = await response.json();

      // Transform results for consistency and to match SearchResultCard requirements
      const transformedResults = data.map((result) => ({
        id: result.document_id || result.id,
        title: result.title || `Document ${result.document_id || result.id}`,
        content: result.content || result.text || result.snippet || "",
        similarity: result.similarity,
        source: result.source || "Unknown",
        timestamp: result.timestamp || result.created_at,
        tags: result.tags || [],
      }));

      setResults(transformedResults);
      if (onSearch) {
        onSearch(transformedResults);
      }
    } catch (error) {
      console.error("Search error:", error);
      setError(error.message || "An error occurred during search");
    } finally {
      setLoading(false);
    }
  };

  const handleSuggestionSelect = (suggestion) => {
    setQuery(suggestion);
    setShowSuggestions(false);
    handleSearch();
  };

  const handleResultSelect = (resultId) => {
    console.log(`Selected result: ${resultId}`);
    // Implementation for viewing details of a selected result
  };

  return (
    <div className="w-full">
      {/* Search controls */}
      <div className="mb-6">
        <form onSubmit={handleSearch} className="mb-4">
          <div className="relative" ref={searchInputRef}>
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search for documents..."
              className="w-full p-3 pl-10 border border-gray-300 rounded-md text-base shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <svg
                className="h-5 w-5 text-gray-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                ></path>
              </svg>
            </div>

            {/* Query suggestions */}
            {showSuggestions && suggestions.length > 0 && (
              <div className="absolute z-10 w-full mt-1 bg-white rounded-md shadow-lg border border-gray-300">
                <ul className="max-h-60 rounded-md py-1 text-base overflow-auto focus:outline-none">
                  {suggestions.map((suggestion, index) => (
                    <li
                      key={index}
                      className="cursor-pointer select-none relative py-2 pl-3 pr-9 hover:bg-gray-100"
                      onClick={() => handleSuggestionSelect(suggestion)}
                    >
                      {suggestion}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {/* Search mode selector */}
          <div className="flex justify-between items-center mt-3 mb-4">
            <div className="flex space-x-4">
              <label className="inline-flex items-center">
                <input
                  type="radio"
                  name="queryMode"
                  value="semantic"
                  checked={queryMode === "semantic"}
                  onChange={() => setQueryMode("semantic")}
                  className="form-radio h-4 w-4 text-blue-600"
                />
                <span className="ml-2 text-sm text-gray-700">Semantic</span>
              </label>
              <label className="inline-flex items-center">
                <input
                  type="radio"
                  name="queryMode"
                  value="keyword"
                  checked={queryMode === "keyword"}
                  onChange={() => setQueryMode("keyword")}
                  className="form-radio h-4 w-4 text-blue-600"
                />
                <span className="ml-2 text-sm text-gray-700">Keyword</span>
              </label>
              <label className="inline-flex items-center">
                <input
                  type="radio"
                  name="queryMode"
                  value="hybrid"
                  checked={queryMode === "hybrid"}
                  onChange={() => setQueryMode("hybrid")}
                  className="form-radio h-4 w-4 text-blue-600"
                />
                <span className="ml-2 text-sm text-gray-700">Hybrid</span>
              </label>
            </div>

            <div className="flex space-x-4">
              <label className="inline-flex items-center">
                <input
                  type="checkbox"
                  checked={useVirtualized}
                  onChange={() => setUseVirtualized(!useVirtualized)}
                  className="form-checkbox h-4 w-4 text-blue-600"
                />
                <span className="ml-2 text-sm text-gray-700">Virtual List</span>
              </label>

              <label className="inline-flex items-center">
                <input
                  type="checkbox"
                  checked={advancedMode}
                  onChange={() => setAdvancedMode(!advancedMode)}
                  className="form-checkbox h-4 w-4 text-blue-600"
                />
                <span className="ml-2 text-sm text-gray-700">
                  Advanced Query
                </span>
              </label>
            </div>
          </div>

          {/* Advanced query builder (JSON editor) */}
          {advancedMode && (
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                JSON Query Builder
              </label>
              <textarea
                value={jsonQuery}
                onChange={(e) => setJsonQuery(e.target.value)}
                rows={10}
                className="w-full p-3 border border-gray-300 rounded-md text-base font-mono text-sm shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
          )}

          <button
            type="submit"
            className="w-full p-3 bg-blue-600 text-white rounded-md cursor-pointer text-base hover:bg-blue-700 transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
            disabled={loading}
          >
            {loading ? "Searching..." : "Search"}
          </button>
        </form>

        {/* Error message */}
        {error && (
          <div className="p-3 bg-red-100 border-l-4 border-red-500 text-red-700 mb-4">
            <p>{error}</p>
          </div>
        )}
      </div>

      {/* Results section */}
      {results.length > 0 ? (
        <div className="mt-6">
          <h3 className="text-xl font-semibold mb-3">
            Results ({results.length})
          </h3>
          {useVirtualized ? (
            <div className="h-full">
              <VirtualizedSearchResults
                results={results}
                onResultSelect={handleResultSelect}
              />
            </div>
          ) : (
            <div className="space-y-4">
              {results.map((result, index) => (
                <SearchResultCard
                  key={result.id || index}
                  result={result}
                  onSelect={handleResultSelect}
                />
              ))}
            </div>
          )}
        </div>
      ) : (
        !loading &&
        query && (
          <div className="text-center py-6 text-gray-500">
            No results found. Try adjusting your search query.
          </div>
        )
      )}
    </div>
  );
};

export default SearchBar;
