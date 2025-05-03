import React, { useState } from "react";

const SearchBar = ({ onSearch }) => {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);

  const handleSearch = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const response = await fetch("http://backend:5000/api/search", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          query: query,
          k: 5,
        }),
      });

      const data = await response.json();
      setResults(data);
      if (onSearch) {
        onSearch(data);
      }
    } catch (error) {
      console.error("Search error:", error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <form onSubmit={handleSearch}>
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Enter your search query..."
          className="w-full p-3 mb-4 border border-gray-300 rounded-md text-base"
        />
        <button
          type="submit"
          className="w-full p-3 bg-green-600 text-white rounded-md cursor-pointer text-base hover:bg-green-700 transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
          disabled={loading}
        >
          {loading ? "Searching..." : "Search"}
        </button>
      </form>

      {results.length > 0 && (
        <div className="mt-5">
          <h3 className="text-xl font-semibold mb-3">Results</h3>
          <ul className="space-y-2">
            {results.map((result, index) => (
              <li
                key={index}
                className="flex justify-between items-center p-4 mb-3 bg-gray-50 rounded-md shadow-sm"
              >
                <div>Document ID: {result.document_id}</div>
                <div className="font-bold text-green-600">
                  Similarity: {(result.similarity * 100).toFixed(2)}%
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};

export default SearchBar;
