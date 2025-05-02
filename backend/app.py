import os
import json
import numpy as np
from flask import Flask, request, jsonify
from sentence_transformers import SentenceTransformer
from dask.distributed import Client, Future
import faiss
from sklearn.cluster import KMeans
import dask.bag as db
import dask.dataframe as dd
from dask.distributed import get_worker
import queue
import threading
from datetime import datetime
import pickle

app = Flask(__name__)
app.config.from_pyfile('config.py')

# Initialize Dask
client = Client()

# Model Versioning
MODEL_REGISTRY = {
    'v1': 'all-MiniLM-L6-v2',
    'v2': 'sentence-transformers/all-mpnet-base-v2'
}
CURRENT_MODEL = app.config['ACTIVE_MODEL']

# Load the correct model based on CURRENT_MODEL
model = SentenceTransformer(MODEL_REGISTRY[CURRENT_MODEL])

# FAISS Index Management
def get_active_index_path():
    return os.path.join(app.config['FAISS_DIR'], f"indexes/{CURRENT_MODEL}/index.index")

def get_active_index():
    index_path = get_active_index_path()
    if os.path.exists(index_path):
        return faiss.read_index(index_path)
    return faiss.IndexFlatL2(768)  # Embedding dimension

faiss_index = get_active_index()
index_lock = threading.Lock()

# Batch Processing Queue
processing_queue = queue.Queue()
queue_file_path = os.path.join(app.config['QUEUES_DIR'], 'processing_queue.pkl')
processing_lock = threading.Lock()

# Try to load existing queue if it exists
if os.path.exists(queue_file_path):
    try:
        with open(queue_file_path, 'rb') as f:
            pending_items = pickle.load(f)
            for item in pending_items:
                processing_queue.put(item)
    except Exception as e:
        print(f"Error loading queue: {e}")

@app.route('/upload', methods=['POST'])
def upload_files():
    files = request.files.getlist("files")
    task_id = str(datetime.now().timestamp())

    # Add to processing queue
    with processing_lock:
        app.config['QUEUE_STATUS']['total'] += len(files)
        for file in files:
            processing_queue.put((file, task_id))

        # Persist queue to disk
        try:
            pending_items = list(processing_queue.queue)
            with open(queue_file_path, 'wb') as f:
                pickle.dump(pending_items, f)
        except Exception as e:
            print(f"Error saving queue: {e}")

    return jsonify({"task_id": task_id, "status": "queued", "files": len(files)})

@app.route('/status/<task_id>')
def task_status(task_id):
    # In a production system, we'd track each task separately
    # For now, simply returning the queue status
    return jsonify({
        "task_id": task_id,
        "status": "processing",
        "queue_stats": app.config['QUEUE_STATUS']
    })

@app.route('/search', methods=['POST'])
def search():
    query = request.json.get('query')
    k = request.json.get('k', 5)

    # Generate query embedding
    query_embedding = model.encode([query])[0]

    # FAISS Search
    with index_lock:
        distances, indices = faiss_index.search(
            np.array([query_embedding], dtype='float32'),
            k
        )

    results = []
    for i, idx in enumerate(indices[0]):
        if idx < 0 or idx >= faiss_index.ntotal:
            continue

        # In a production system, we'd store document mappings
        # For now, returning index and similarity score
        results.append({
            "document_id": int(idx),
            "similarity": float(1 - distances[0][i]),
            "cluster": 0  # Would be populated from clustering data
        })

    return jsonify(results)

@app.route('/visualization', methods=['GET'])
def get_visualization_data():
    # Generate cluster statistics
    # In a production system, we'd do proper clustering and dimensionality reduction

    cluster_stats = [
        {"name": "Cluster 1", "messages": 100, "sentiment": 0.8},
        {"name": "Cluster 2", "messages": 75, "sentiment": 0.2},
        {"name": "Cluster 3", "messages": 50, "sentiment": 0.5}
    ]

    projection_data = []

    # Add some sample projection data
    if faiss_index.ntotal > 0:
        # Get a sample of the embeddings (max 1000)
        sample_size = min(faiss_index.ntotal, 1000)
        indices = np.random.choice(faiss_index.ntotal, size=sample_size, replace=False)

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

@app.route('/models/switch/<version>')
def switch_model(version):
    if version in MODEL_REGISTRY:
        global CURRENT_MODEL, model, faiss_index
        CURRENT_MODEL = version
        app.config['ACTIVE_MODEL'] = version

        # Save to active_model.txt
        active_model_path = os.path.join(app.config['MODELS_DIR'], 'active_model.txt')
        with open(active_model_path, 'w') as f:
            f.write(CURRENT_MODEL)

        # Load the new model
        model = SentenceTransformer(MODEL_REGISTRY[CURRENT_MODEL])

        # Load the corresponding index
        faiss_index = get_active_index()

        return jsonify({"status": "success", "active_model": version})
    return jsonify({"error": "Invalid model version"}), 400

@app.route('/queue/status')
def queue_status():
    return jsonify({
        "queue_length": processing_queue.qsize(),
        "stats": app.config['QUEUE_STATUS']
    })

@app.route('/health')
def health_check():
    return jsonify({
        "status": "healthy",
        "model": CURRENT_MODEL,
        "model_name": MODEL_REGISTRY[CURRENT_MODEL],
        "index_size": faiss_index.ntotal,
        "queue_length": processing_queue.qsize()
    })

def process_queue():
    while True:
        try:
            # Get item from queue with 5-second timeout
            file, task_id = processing_queue.get(timeout=5)

            try:
                # Read file contents
                content = file.read()

                if isinstance(content, bytes):
                    content = content.decode('utf-8')

                # Parse JSON if it's a JSON file
                data = json.loads(content) if file.filename.endswith('.json') else {"text": content}

                # Extract messages
                messages = []
                if "messages" in data:
                    messages = [msg.get('content', '') for msg in data["messages"] if 'content' in msg]
                elif "text" in data:
                    messages = [data["text"]]

                if messages:
                    # Generate embeddings with Dask
                    future = client.submit(model.encode, messages)
                    embeddings = future.result()

                    # Add to FAISS index
                    with index_lock:
                        faiss_index.add(np.array(embeddings, dtype='float32'))
                        index_path = get_active_index_path()
                        os.makedirs(os.path.dirname(index_path), exist_ok=True)
                        faiss.write_index(faiss_index, index_path)

                # Update stats
                with processing_lock:
                    app.config['QUEUE_STATUS']['processed'] += 1

            except Exception as e:
                print(f"Error processing file {file.filename}: {e}")
                with processing_lock:
                    app.config['QUEUE_STATUS']['failed'] += 1

            # Mark task as complete
            processing_queue.task_done()

            # Update persisted queue
            with processing_lock:
                pending_items = list(processing_queue.queue)
                with open(queue_file_path, 'wb') as f:
                    pickle.dump(pending_items, f)

        except queue.Empty:
            # Queue is empty, wait a bit
            pass
        except Exception as e:
            print(f"Queue processing error: {e}")

@app.before_request
def manage_memory():
    try:
        worker = get_worker()
        if hasattr(worker, 'memory') and worker.memory.used > app.config['MEMORY_LIMIT']:
            worker.restart()
    except:
        # Not in a worker context or other error
        pass

# Start queue processor
queue_thread = threading.Thread(target=process_queue)
queue_thread.daemon = True
queue_thread.start()

if __name__ == '__main__':
    app.config['QUEUE_STATUS'] = {
        "total": 0,
        "processed": 0,
        "failed": 0
    }
    app.run(host='0.0.0.0', port=5000, threaded=True)
