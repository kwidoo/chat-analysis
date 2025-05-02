import os

# Configuration settings
class Config:
    DATA_DIR = os.path.join(os.path.dirname(__file__), 'faiss')
    UPLOAD_DIR = os.path.join(os.path.dirname(__file__), 'uploads')
    DASK_SCHEDULER_ADDRESS = 'tcp://dask-scheduler:8786'
    FAISS_LOCK_FILE = os.path.join(DATA_DIR, 'index.lock')
    FAISS_DIR = os.path.join(os.path.dirname(__file__), 'faiss')
    MODELS_DIR = os.path.join(os.path.dirname(__file__), 'models')
    QUEUES_DIR = os.path.join(os.path.dirname(__file__), 'queues')
    ACTIVE_MODEL = os.environ.get('ACTIVE_MODEL', 'v1')

    # Memory management
    MEMORY_LIMIT = "4GB"
    GC_INTERVAL = 300  # seconds

    # Queue monitoring
    QUEUE_STATUS = {
        "total": 0,
        "processed": 0,
        "failed": 0
    }

    @staticmethod
    def init_app(app):
        os.makedirs(Config.DATA_DIR, exist_ok=True)
        os.makedirs(Config.UPLOAD_DIR, exist_ok=True)
        os.makedirs(Config.MODELS_DIR, exist_ok=True)
        os.makedirs(Config.QUEUES_DIR, exist_ok=True)

        # Create active_model.txt if it doesn't exist
        active_model_path = os.path.join(Config.MODELS_DIR, 'active_model.txt')
        if not os.path.exists(active_model_path):
            with open(active_model_path, 'w') as f:
                f.write(Config.ACTIVE_MODEL)
