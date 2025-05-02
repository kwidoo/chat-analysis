from flask import Flask, request, jsonify
import json
import pandas as pd
import numpy as np
from sentence_transformers import SentenceTransformer
from dask.distributed import Client
from sklearn.cluster import KMeans

app = Flask(__name__)

# Initialize Dask client
client = Client()

# Load pre-trained model
model = SentenceTransformer('bert-base-nli-mean-tokens')

@app.route('/upload', methods=['POST'])
def upload_files():
    files = request.files.getlist("files")
    data = []
    for file in files:
        data.append(json.load(file))

    all_messages = [message for chat in data for message in chat['messages']]
    processed_messages = all_messages  # Implement preprocessing if needed

    # Generate embeddings
    embeddings = model.encode(processed_messages)

    # Find common patterns
    labels = find_common_patterns(embeddings)

    return jsonify({"labels": labels.tolist()})

def find_common_patterns(embeddings, num_clusters=5):
    kmeans = KMeans(n_clusters=num_clusters)
    kmeans.fit(embeddings)
    return kmeans.labels_

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
