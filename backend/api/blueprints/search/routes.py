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
