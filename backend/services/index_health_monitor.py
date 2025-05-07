import json
import logging
import os
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

import faiss
import numpy as np
import psutil

logger = logging.getLogger(__name__)


class IndexHealthMonitor:
    """Monitor and maintain FAISS index health"""

    def __init__(self, config: Dict[str, Any]):
        """Initialize the index health monitor

        Args:
            config: Configuration dictionary with keys:
                - FAISS_DIR: Base directory for FAISS indexes
                - ACTIVE_MODEL: Current active model name
                - HEALTH_CHECK_INTERVAL: Seconds between health checks (default: 60)
                - VACUUM_THRESHOLD: Percent of fragmentation to trigger vacuum (default: 20)
                - VACUUM_INTERVAL: Minimum hours between vacuums (default: 24)
        """
        self.faiss_dir = Path(config.get("FAISS_DIR", "./faiss"))
        self.active_model = config.get("ACTIVE_MODEL", "v1")

        # Monitoring settings
        self.health_check_interval = config.get("HEALTH_CHECK_INTERVAL", 60)  # seconds
        self.vacuum_threshold = config.get("VACUUM_THRESHOLD", 20)  # percent fragmentation
        self.vacuum_interval = config.get("VACUUM_INTERVAL", 24)  # hours

        # Paths
        self.index_dir = self.faiss_dir / "indexes"
        self.active_index_path = self.index_dir / self.active_model / "index.index"
        self.metrics_dir = self.faiss_dir / "metrics"
        self.metrics_dir.mkdir(parents=True, exist_ok=True)
        self.health_log_path = self.metrics_dir / "health_metrics.json"

        # Internal state
        self._running = False
        self._monitor_thread = None
        self._lock = threading.Lock()
        self._last_vacuum_time = self._get_last_vacuum_time()
        self._last_health_metrics = self._load_last_health_metrics()

    def start_monitoring(self):
        """Start the monitoring thread"""
        if self._running:
            return

        self._running = True
        self._monitor_thread = threading.Thread(
            target=self._monitoring_loop, daemon=True, name="IndexHealthMonitor"
        )
        self._monitor_thread.start()
        logger.info(
            f"Started FAISS index health monitoring with interval: {self.health_check_interval}s"
        )

    def stop_monitoring(self):
        """Stop the monitoring thread"""
        self._running = False
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=5.0)
            logger.info("Stopped FAISS index health monitoring")

    def check_index_health(self) -> Dict[str, Any]:
        """Run a quick health check on the current index

        Returns:
            Dict with health metrics
        """
        start_time = time.time()
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "index_path": str(self.active_index_path),
            "status": "unknown",
        }

        try:
            # Check if index file exists
            if not self.active_index_path.exists():
                metrics.update({"status": "missing", "error": "Index file not found"})
                return metrics

            # Check file stats
            file_size = os.path.getsize(self.active_index_path)
            metrics["file_size_bytes"] = file_size

            # Quick read test - just load the index header
            # This is a basic integrity check that completes in <1s
            index = faiss.read_index(str(self.active_index_path))

            metrics.update(
                {
                    "status": "healthy",
                    "ntotal": index.ntotal,
                    "dimension": index.d,
                    "index_type": type(index).__name__,
                    "check_time_ms": int((time.time() - start_time) * 1000),
                }
            )

            # Run basic search test if the index has vectors
            if index.ntotal > 0:
                try:
                    # Generate a random query vector
                    query = np.random.random(index.d).astype("float32").reshape(1, -1)

                    # Time the search operation
                    search_start = time.time()
                    distances, indices = index.search(query, min(10, index.ntotal))
                    search_time = time.time() - search_start

                    metrics["search_time_ms"] = int(search_time * 1000)

                    # Check if search returned valid results
                    if indices[0][0] < 0 or indices[0][0] >= index.ntotal:
                        metrics["status"] = "warning"
                        metrics["warning"] = "Search returned invalid indices"
                except Exception as e:
                    metrics["status"] = "error"
                    metrics["error"] = f"Search test failed: {str(e)}"

            # Calculate fragmentation (simplified)
            # In a real implementation, you would need a model-specific approach
            # as different index types have different fragmentation characteristics
            if hasattr(index, "ntotal") and hasattr(index, "ntotal_2"):
                # This is hypothetical - FAISS doesn't actually have ntotal_2
                # You'd need to implement your own fragmentation detection logic
                fragmentation = (
                    (1 - (index.ntotal_2 / index.ntotal)) * 100 if index.ntotal > 0 else 0
                )
                metrics["fragmentation_percent"] = fragmentation

                if fragmentation > self.vacuum_threshold:
                    metrics["vacuum_needed"] = True

            # Check system resources
            process = psutil.Process(os.getpid())
            metrics["memory_usage_bytes"] = process.memory_info().rss

            return metrics

        except Exception as e:
            elapsed_ms = int((time.time() - start_time) * 1000)
            logger.error(f"Health check failed in {elapsed_ms}ms: {e}")
            metrics.update({"status": "error", "error": str(e), "check_time_ms": elapsed_ms})
            return metrics

    def vacuum_index(self) -> Dict[str, Any]:
        """Run vacuum operation on the index to optimize storage and performance

        Returns:
            Dict with vacuum operation results
        """
        start_time = time.time()
        result = {
            "timestamp": datetime.now().isoformat(),
            "index_path": str(self.active_index_path),
            "status": "started",
        }

        try:
            if not self.active_index_path.exists():
                result["status"] = "failed"
                result["error"] = "Index file not found"
                return result

            # Create a backup before vacuum
            backup_path = self.active_index_path.with_suffix(".index.bak")
            try:
                import shutil

                shutil.copy2(self.active_index_path, backup_path)
                result["backup_created"] = True
                result["backup_path"] = str(backup_path)
            except Exception as backup_err:
                logger.error(f"Failed to create backup before vacuum: {backup_err}")
                result["backup_created"] = False
                result["backup_error"] = str(backup_err)

            # Load the index
            index = faiss.read_index(str(self.active_index_path))
            original_size = os.path.getsize(self.active_index_path)
            original_count = index.ntotal

            # Perform vacuum operation
            # This depends on the index type - for demonstration purposes:
            # 1. For some index types, we might rebuild the index
            # 2. For others, we might have specialized maintenance operations

            # For this example, we'll just re-save the index which can sometimes
            # optimize storage in real FAISS implementations
            temp_path = self.active_index_path.with_suffix(".index.temp")
            faiss.write_index(index, str(temp_path))

            # Replace the original with the new one
            os.replace(temp_path, self.active_index_path)

            # Get new metrics
            new_size = os.path.getsize(self.active_index_path)
            index = faiss.read_index(str(self.active_index_path))
            new_count = index.ntotal

            # Record vacuum results
            self._last_vacuum_time = datetime.now()
            self._save_last_vacuum_time()

            # Return results
            result.update(
                {
                    "status": "completed",
                    "original_size_bytes": original_size,
                    "new_size_bytes": new_size,
                    "size_reduction_bytes": original_size - new_size,
                    "size_reduction_percent": (
                        round((original_size - new_size) / original_size * 100, 2)
                        if original_size > 0
                        else 0
                    ),
                    "original_count": original_count,
                    "new_count": new_count,
                    "duration_seconds": round(time.time() - start_time, 2),
                }
            )

            return result

        except Exception as e:
            logger.error(f"Vacuum operation failed: {e}")
            result.update(
                {
                    "status": "failed",
                    "error": str(e),
                    "duration_seconds": round(time.time() - start_time, 2),
                }
            )
            return result

    def detect_corruption(self) -> Dict[str, Any]:
        """Quickly detect any index corruption (<1s)

        Returns:
            Dict with corruption check results
        """
        start_time = time.time()
        result = {
            "timestamp": datetime.now().isoformat(),
            "index_path": str(self.active_index_path),
            "status": "unknown",
        }

        try:
            if not self.active_index_path.exists():
                result["status"] = "error"
                result["error"] = "Index file not found"
                return result

            # First test: Try to read index header
            # This is fast but doesn't verify the entire index
            try:
                index = faiss.read_index_header(str(self.active_index_path))
                result["header_check"] = "passed"
            except Exception as header_err:
                result["status"] = "corrupted"
                result["header_check"] = "failed"
                result["header_error"] = str(header_err)
                return result

            # Second test: Quick structure check
            # This is still fast and catches more corruption issues
            # Test will be different depending on index type (e.g., IVF, Flat, etc.)
            try:
                index = faiss.read_index(str(self.active_index_path))

                # Check if basic attributes are available
                assert hasattr(index, "ntotal"), "Missing ntotal attribute"
                assert hasattr(index, "d"), "Missing dimension attribute"

                # For IVF-type indices, check list structure
                if hasattr(index, "nlist"):
                    assert index.nlist > 0, "Invalid nlist value"

                result["structure_check"] = "passed"
                result["status"] = "healthy"
            except Exception as structure_err:
                result["status"] = "corrupted"
                result["structure_check"] = "failed"
                result["structure_error"] = str(structure_err)
                return result

            # Return results with timing information
            duration_ms = int((time.time() - start_time) * 1000)
            result["check_time_ms"] = duration_ms

            # If checks are too slow, warn but don't fail
            if duration_ms > 1000:  # 1 second
                result["status"] = "warning"
                result["warning"] = f"Corruption check exceeded 1s threshold ({duration_ms}ms)"

            return result

        except Exception as e:
            logger.error(f"Corruption detection failed: {e}")
            result.update(
                {
                    "status": "error",
                    "error": str(e),
                    "check_time_ms": int((time.time() - start_time) * 1000),
                }
            )
            return result

    def _monitoring_loop(self):
        """Background monitoring loop"""
        while self._running:
            try:
                # Run health check
                metrics = self.check_index_health()
                self._store_health_metrics(metrics)

                # Check for vacuum need
                should_vacuum = self._should_run_vacuum(metrics)
                if should_vacuum:
                    logger.info("Running scheduled vacuum operation")
                    vacuum_result = self.vacuum_index()
                    logger.info(f"Vacuum completed with status: {vacuum_result['status']}")

                    # Store vacuum metrics with health data
                    self._store_vacuum_metrics(vacuum_result)

            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")

            # Sleep until next check
            time.sleep(self.health_check_interval)

    def _should_run_vacuum(self, metrics: Dict[str, Any]) -> bool:
        """Determine if vacuum should run based on metrics and schedule

        Args:
            metrics: Current health metrics

        Returns:
            bool: True if vacuum should run, False otherwise
        """
        # Check if minimum time since last vacuum has passed
        if self._last_vacuum_time:
            next_vacuum_time = self._last_vacuum_time + timedelta(hours=self.vacuum_interval)
            if datetime.now() < next_vacuum_time:
                return False

        # Check if fragmentation exceeds threshold
        fragmentation = metrics.get("fragmentation_percent", 0)
        vacuum_needed = metrics.get("vacuum_needed", False)

        return vacuum_needed or fragmentation > self.vacuum_threshold

    def _store_health_metrics(self, metrics: Dict[str, Any]):
        """Store health metrics for historical analysis

        Args:
            metrics: Health metrics to store
        """
        self._last_health_metrics = metrics

        # Append to metrics file (keeping last N entries)
        max_entries = 100  # Keep last 100 health checks

        try:
            # Load existing metrics
            existing_metrics = []
            if self.health_log_path.exists():
                with open(self.health_log_path, "r") as f:
                    existing_metrics = json.load(f)

            # Add new metrics
            existing_metrics.append(metrics)

            # Keep only latest entries
            if len(existing_metrics) > max_entries:
                existing_metrics = existing_metrics[-max_entries:]

            # Save updated metrics
            with open(self.health_log_path, "w") as f:
                json.dump(existing_metrics, f, indent=2)

        except Exception as e:
            logger.error(f"Failed to store health metrics: {e}")

    def _store_vacuum_metrics(self, vacuum_result: Dict[str, Any]):
        """Store vacuum operation metrics

        Args:
            vacuum_result: Vacuum operation results
        """
        vacuum_log_path = self.metrics_dir / "vacuum_log.json"

        try:
            # Load existing log
            existing_log = []
            if vacuum_log_path.exists():
                with open(vacuum_log_path, "r") as f:
                    existing_log = json.load(f)

            # Add new entry
            existing_log.append(vacuum_result)

            # Keep only latest 50 entries
            if len(existing_log) > 50:
                existing_log = existing_log[-50:]

            # Save updated log
            with open(vacuum_log_path, "w") as f:
                json.dump(existing_log, f, indent=2)

            # Update last vacuum time
            self._last_vacuum_time = datetime.now()
            self._save_last_vacuum_time()

        except Exception as e:
            logger.error(f"Failed to store vacuum metrics: {e}")

    def _get_last_vacuum_time(self) -> Optional[datetime]:
        """Get the timestamp of the last vacuum operation

        Returns:
            Optional[datetime]: Timestamp of last vacuum or None
        """
        vacuum_time_path = self.metrics_dir / "last_vacuum_time.txt"

        if vacuum_time_path.exists():
            try:
                with open(vacuum_time_path, "r") as f:
                    timestamp_str = f.read().strip()
                    return datetime.fromisoformat(timestamp_str)
            except Exception:
                return None

        return None

    def _save_last_vacuum_time(self):
        """Save the timestamp of the last vacuum operation"""
        if not self._last_vacuum_time:
            return

        vacuum_time_path = self.metrics_dir / "last_vacuum_time.txt"

        try:
            with open(vacuum_time_path, "w") as f:
                f.write(self._last_vacuum_time.isoformat())
        except Exception as e:
            logger.error(f"Failed to save vacuum timestamp: {e}")

    def _load_last_health_metrics(self) -> Dict[str, Any]:
        """Load the most recent health metrics

        Returns:
            Dict with health metrics or empty dict if none found
        """
        if not self.health_log_path.exists():
            return {}

        try:
            with open(self.health_log_path, "r") as f:
                metrics_list = json.load(f)
                if metrics_list and len(metrics_list) > 0:
                    return metrics_list[-1]
        except Exception:
            pass

        return {}
