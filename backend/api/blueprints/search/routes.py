import numpy as np
from flask import request, jsonify, current_app
from . import search_bp


@search_bp.route('', methods=['POST'])
def search():
    """Endpoint to search for similar items using FAISS

    Required JSON body parameters:
    - q: Query text to search for
    - k: Number of results to return (default: 5)
    """
    data = request.json
    if not data:
        return jsonify({"error": "Missing JSON body"}), 400

    query = data.get('q')
    if not query:
        return jsonify({"error": "Missing query parameter 'q'"}), 400

    # Get k with type conversion and default value
    try:
        k = int(data.get('k', 5))
    except (ValueError, TypeError):
        return jsonify({"error": "Parameter 'k' must be an integer"}), 400

    # Get services from app context
    embedding_service = current_app.embedding_service
    index_service = current_app.index_service

    # Generate query embedding
    query_embedding = embedding_service.encode([query])[0]

    # FAISS Search
    distances, indices = index_service.search(query_embedding, k)

    results = []
    for i, idx in enumerate(indices[0]):
        if idx < 0 or idx >= index_service.get_total():
            continue

        # In a production system, we'd store document mappings
        # For now, returning index and similarity score
        results.append({
            "document_id": int(idx),
            "similarity": float(1 - distances[0][i]),
            "cluster": 0  # Would be populated from clustering data
        })

    return jsonify(results)


@search_bp.route('/suggest', methods=['POST'])
def suggest():
    """Endpoint to provide search query suggestions based on user input.

    Required JSON body parameters:
    - input: Partial search query text for generating suggestions
    """
    data = request.json
    if not data:
        return jsonify({"error": "Missing JSON body"}), 400

    input_text = data.get('input')
    if not input_text or not isinstance(input_text, str):
        return jsonify({"error": "Missing or invalid 'input' parameter"}), 400

    # Get index service from app context
    index_service = current_app.index_service

    # Logic to generate suggestions
    # This is a simplified implementation - in production, you might use:
    # 1. Previously successful queries from a query log
    # 2. Frequent terms from your index
    # 3. Document titles or key phrases
    # 4. An external suggestion service API

    # Get some data from the index to base suggestions on
    total_docs = index_service.get_total()
    suggestions = []

    if total_docs > 0:
        # Generate suggestions based on the input
        if input_text.lower().startswith('how'):
            suggestions = [
                f"{input_text} to implement search",
                f"{input_text} to optimize indexing",
                f"{input_text} to improve query performance"
            ]
        elif input_text.lower().startswith('what'):
            suggestions = [
                f"{input_text} is FAISS",
                f"{input_text} are vector embeddings",
                f"{input_text} is the best indexing strategy"
            ]
        else:
            # Generic suggestions based on common search patterns
            suggestions = [
                f"{input_text} tutorial",
                f"{input_text} implementation",
                f"{input_text} best practices",
                f"{input_text} examples"
            ]

    return jsonify({"suggestions": suggestions})


@search_bp.route('/process-nl', methods=['POST'])
def process_natural_language():
    """Endpoint to transform natural language queries into structured queries.

    Required JSON body parameters:
    - query: Natural language text to transform into a structured query
    """
    data = request.json
    if not data:
        return jsonify({"error": "Missing JSON body"}), 400

    query = data.get('query')
    if not query or not isinstance(query, str):
        return jsonify({"error": "Missing or invalid 'query' parameter"}), 400

    # Process the natural language query
    # This is a simplified implementation - in production, you might use:
    # 1. NLP libraries to extract entities, intent, etc.
    # 2. A language model to transform the query
    # 3. Rule-based transformations for common patterns

    structured_query = {
        "type": "semantic",
        "text": query,
        "filters": [],
        "boost": []
    }

    # Detect filtering intention
    lower_query = query.lower()

    # Check for time filters
    if any(term in lower_query for term in ["today", "recent", "latest"]):
        structured_query["filters"].append({
            "field": "timestamp",
            "operator": "gte",
            "value": "now-1d" # Last 24 hours
        })
    elif "yesterday" in lower_query:
        structured_query["filters"].append({
            "field": "timestamp",
            "operator": "range",
            "value": {"gte": "now-2d", "lt": "now-1d"}
        })
    elif "this week" in lower_query:
        structured_query["filters"].append({
            "field": "timestamp",
            "operator": "gte",
            "value": "now-7d"
        })

    # Check for type filters
    if "document" in lower_query or "doc" in lower_query:
        structured_query["filters"].append({
            "field": "type",
            "operator": "eq",
            "value": "document"
        })
    elif "image" in lower_query or "photo" in lower_query:
        structured_query["filters"].append({
            "field": "type",
            "operator": "eq",
            "value": "image"
        })

    return jsonify({
        "original_query": query,
        "structured_query": structured_query
    })


@search_bp.route('/visualization', methods=['GET'])
def get_visualization_data():
    """Endpoint to get data for visualization"""
    # Get index service from app context
    index_service = current_app.index_service

    # Generate cluster statistics
    # In a production system, we'd do proper clustering and dimensionality reduction
    cluster_stats = [
        {"name": "Cluster 1", "messages": 100, "sentiment": 0.8},
        {"name": "Cluster 2", "messages": 75, "sentiment": 0.2},
        {"name": "Cluster 3", "messages": 50, "sentiment": 0.5}
    ]

    projection_data = []
    # Add some sample projection data
    if index_service.get_total() > 0:
        # Get a sample of the embeddings (max 1000)
        sample_size = min(index_service.get_total(), 1000)
        indices = np.random.choice(index_service.get_total(), size=sample_size, replace=False)
        for i in indices:
            projection_data.append({
                "x": float(np.random.random()),  # In reality, this would be t-SNE output
                "y": float(np.random.random()),
                "cluster": int(np.random.randint(0, 3)),
                "id": int(i)
            })

    return jsonify({
        "clusters": cluster_stats,
        "projection": projection_data
    })
