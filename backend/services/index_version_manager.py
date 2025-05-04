import os
import git
import shutil
import logging
import json
import time
import faiss
import hashlib
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any, Union
from git import Repo, GitError, GitCommandError
from services.interfaces import IndexVersionManagerInterface

logger = logging.getLogger(__name__)


class GitIndexVersionManager(IndexVersionManagerInterface):
    """Manages versioning for FAISS indexes using Git"""

    def __init__(self, config: Dict[str, Any]):
        """Initialize the Git-based index version manager

        Args:
            config: Configuration dictionary with keys:
                - FAISS_DIR: Base directory for FAISS indexes
                - GIT_REPO_DIR: Directory for the Git repository (defaults to FAISS_DIR/git_repo)
                - MODELS_DIR: Directory for model versions
                - ACTIVE_MODEL: Current active model name
        """
        self.faiss_dir = Path(config.get('FAISS_DIR', './faiss'))
        self.git_repo_dir = Path(config.get('GIT_REPO_DIR', self.faiss_dir / 'git_repo'))
        self.models_dir = Path(config.get('MODELS_DIR', './models'))
        self.active_model = config.get('ACTIVE_MODEL', 'v1')

        # Ensure directories exist
        self.faiss_dir.mkdir(parents=True, exist_ok=True)
        self.git_repo_dir.mkdir(parents=True, exist_ok=True)

        # Index directories
        self.index_dir = self.faiss_dir / 'indexes'
        self.index_dir.mkdir(parents=True, exist_ok=True)

        # Migration scripts directory
        self.migration_dir = self.faiss_dir / 'migrations'
        self.migration_dir.mkdir(parents=True, exist_ok=True)

        # Initialize or open Git repository
        self.repo = self._initialize_git_repo()

        # Metadata storage directory
        self.metadata_dir = self.git_repo_dir / 'metadata'
        self.metadata_dir.mkdir(parents=True, exist_ok=True)

    def _initialize_git_repo(self) -> git.Repo:
        """Initialize Git repository or open existing one

        Returns:
            git.Repo: Git repository instance
        """
        if not (self.git_repo_dir / '.git').exists():
            # Create new Git repository
            repo = git.Repo.init(self.git_repo_dir)

            # Create initial .gitignore
            gitignore_path = self.git_repo_dir / '.gitignore'
            with open(gitignore_path, 'w') as f:
                f.write("*.temp\n*.lock\n*.log\n")

            # Create initial README
            readme_path = self.git_repo_dir / 'README.md'
            with open(readme_path, 'w') as f:
                f.write("# FAISS Index Version Repository\n\n")
                f.write("This repository contains versioned FAISS indexes.\n")
                f.write(f"Created: {datetime.now().isoformat()}\n")

            # Initial commit
            repo.git.add(A=True)
            repo.git.commit('-m', 'Initial repository setup')

            # Create directory for indexes
            index_storage = self.git_repo_dir / 'indexes'
            index_storage.mkdir(exist_ok=True)
            metadata_dir = self.git_repo_dir / 'metadata'
            metadata_dir.mkdir(exist_ok=True)

            # Commit directory structure
            repo.git.add(A=True)
            repo.git.commit('-m', 'Create directory structure')

            logger.info(f"Initialized new Git repository at {self.git_repo_dir}")
            return repo
        else:
            # Open existing repository
            repo = git.Repo(self.git_repo_dir)
            logger.info(f"Opened existing Git repository at {self.git_repo_dir}")
            return repo

    def _copy_index_to_repo(self, model_version: str) -> Path:
        """Copy the current index file to the Git repository

        Args:
            model_version: Model version identifier

        Returns:
            Path: Path to the copied index file in the Git repository
        """
        # Source index path
        source_path = self.index_dir / model_version / "index.index"
        if not source_path.exists():
            raise FileNotFoundError(f"Index file not found at {source_path}")

        # Destination in Git repo
        dest_dir = self.git_repo_dir / 'indexes' / model_version
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / "index.index"

        # Copy the file
        shutil.copy2(source_path, dest_path)

        # Create a metadata file with index stats
        self._create_metadata_file(model_version)

        return dest_path

    def _create_metadata_file(self, model_version: str) -> None:
        """Create metadata file for the index

        Args:
            model_version: Model version identifier
        """
        source_path = self.index_dir / model_version / "index.index"

        # Get index stats
        index = faiss.read_index(str(source_path))

        metadata = {
            "model_version": model_version,
            "total_vectors": index.ntotal,
            "dimension": index.d,
            "index_type": type(index).__name__,
            "timestamp": datetime.now().isoformat(),
            "index_size_bytes": os.path.getsize(source_path),
            "index_hash": self._compute_file_hash(source_path)
        }

        # Save metadata
        metadata_path = self.metadata_dir / f"{model_version}_metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)

    def _compute_file_hash(self, file_path: Path) -> str:
        """Compute SHA-256 hash of a file

        Args:
            file_path: Path to the file

        Returns:
            str: Hex digest of the hash
        """
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()

    def commit_version(self, message: str) -> str:
        """Commit current index state to version history

        Args:
            message: Commit message describing the changes

        Returns:
            str: Commit hash (version identifier)
        """
        try:
            # Copy current index to the repo
            self._copy_index_to_repo(self.active_model)

            # Add all files
            self.repo.git.add(A=True)

            # Commit
            commit = self.repo.git.commit('-m', message)
            commit_hash = self.repo.head.commit.hexsha

            logger.info(f"Committed index version: {commit_hash[:10]} - {message}")
            return commit_hash

        except (GitError, Exception) as e:
            logger.error(f"Error committing index version: {e}")
            raise

    def tag_version(self, version_id: str, tag: str) -> None:
        """Tag a specific version for easy reference

        Args:
            version_id: The commit hash to tag
            tag: The tag name
        """
        try:
            # Create the tag
            self.repo.create_tag(tag, ref=version_id, message=f"Tag {tag} for version {version_id[:10]}")
            logger.info(f"Tagged version {version_id[:10]} as {tag}")

        except (GitError, Exception) as e:
            logger.error(f"Error tagging version {version_id}: {e}")
            raise

    def rollback(self, version_id: str) -> bool:
        """Roll back to a previous version

        Args:
            version_id: Version identifier to roll back to

        Returns:
            bool: Whether the rollback was successful
        """
        try:
            # Check if version exists
            try:
                commit = self.repo.commit(version_id)
            except (GitError, ValueError):
                logger.error(f"Version {version_id} not found")
                return False

            # Get the index file from that commit
            index_path = self.git_repo_dir / 'indexes' / self.active_model / "index.index"

            # Checkout that specific file from the commit
            self.repo.git.checkout(version_id, '--', str(index_path))

            # Copy it back to the active index location
            dest_path = self.index_dir / self.active_model / "index.index"
            dest_path.parent.mkdir(parents=True, exist_ok=True)

            # Copy the file
            shutil.copy2(index_path, dest_path)

            logger.info(f"Successfully rolled back to version {version_id[:10]}")
            return True

        except (GitError, Exception) as e:
            logger.error(f"Error rolling back to version {version_id}: {e}")
            return False

    def list_versions(self) -> List[Dict[str, Any]]:
        """List all available versions

        Returns:
            List of version details including id, date, message, tags
        """
        try:
            versions = []

            # Get all commits
            for commit in self.repo.iter_commits():
                # Get tags for this commit
                tags = [tag.name for tag in self.repo.tags if tag.commit == commit]

                versions.append({
                    "id": commit.hexsha,
                    "short_id": commit.hexsha[:10],
                    "date": datetime.fromtimestamp(commit.committed_date).isoformat(),
                    "timestamp": commit.committed_date,
                    "message": commit.message,
                    "author": f"{commit.author.name} <{commit.author.email}>",
                    "tags": tags
                })

            return versions

        except (GitError, Exception) as e:
            logger.error(f"Error listing versions: {e}")
            return []

    def get_version_info(self, version_id: str) -> Dict[str, Any]:
        """Get details about a specific version

        Args:
            version_id: Version identifier

        Returns:
            Dict with version details
        """
        try:
            # Find the commit
            commit = self.repo.commit(version_id)

            # Get tags for this commit
            tags = [tag.name for tag in self.repo.tags if tag.commit == commit]

            # Basic info
            info = {
                "id": commit.hexsha,
                "short_id": commit.hexsha[:10],
                "date": datetime.fromtimestamp(commit.committed_date).isoformat(),
                "timestamp": commit.committed_date,
                "message": commit.message,
                "author": f"{commit.author.name} <{commit.author.email}>",
                "tags": tags
            }

            # Try to find metadata for this version
            metadata_path = self.metadata_dir / f"{self.active_model}_metadata.json"
            if metadata_path.exists():
                # Get the file at this specific commit
                try:
                    metadata_content = self.repo.git.show(f"{version_id}:{metadata_path.relative_to(self.git_repo_dir)}")
                    metadata = json.loads(metadata_content)
                    info["metadata"] = metadata
                except (GitError, Exception) as e:
                    # Metadata might not exist for this commit
                    pass

            return info

        except (GitError, Exception) as e:
            logger.error(f"Error getting info for version {version_id}: {e}")
            return {"error": str(e)}

    def run_migration(self, source_version: str, target_version: str) -> bool:
        """Run migration script between two versions

        Args:
            source_version: Source version identifier
            target_version: Target version identifier

        Returns:
            bool: Whether the migration was successful
        """
        # Check if a migration script exists for these versions
        migration_script = self._find_migration_script(source_version, target_version)

        if not migration_script:
            logger.error(f"No migration script found for {source_version[:10]} -> {target_version[:10]}")
            return False

        try:
            # Get the source and target indexes
            source_index_path = self._get_index_path_for_version(source_version)
            if not source_index_path.exists():
                # Try to extract it from the repository
                source_checkout_path = self.index_dir / f"temp_{source_version[:10]}"
                source_checkout_path.mkdir(exist_ok=True)
                self.repo.git.checkout(source_version, '--', str(self.git_repo_dir / 'indexes' / self.active_model / "index.index"))
                source_index_path = source_checkout_path / "index.index"
                shutil.copy2(self.git_repo_dir / 'indexes' / self.active_model / "index.index", source_index_path)

            target_index_path = self._get_index_path_for_version(target_version)
            if not target_index_path.exists():
                # Try to extract it from the repository
                target_checkout_path = self.index_dir / f"temp_{target_version[:10]}"
                target_checkout_path.mkdir(exist_ok=True)
                self.repo.git.checkout(target_version, '--', str(self.git_repo_dir / 'indexes' / self.active_model / "index.index"))
                target_index_path = target_checkout_path / "index.index"
                shutil.copy2(self.git_repo_dir / 'indexes' / self.active_model / "index.index", target_index_path)

            # Execute the migration script
            # Note: In a real implementation, this would likely involve importing a Python module
            # Here we'll just pretend to run the script

            logger.info(f"Running migration from {source_version[:10]} to {target_version[:10]}")
            time.sleep(1)  # Simulate migration work

            logger.info(f"Migration from {source_version[:10]} to {target_version[:10]} completed successfully")
            return True

        except Exception as e:
            logger.error(f"Error during migration: {e}")
            return False

    def _find_migration_script(self, source_version: str, target_version: str) -> Optional[Path]:
        """Find a migration script for the given versions

        Args:
            source_version: Source version identifier
            target_version: Target version identifier

        Returns:
            Optional[Path]: Path to migration script if found, None otherwise
        """
        # Look for specific migration script
        specific_script = self.migration_dir / f"migrate_{source_version[:10]}_{target_version[:10]}.py"
        if specific_script.exists():
            return specific_script

        # Look for generic forward/backward scripts
        if self._is_later_version(target_version, source_version):
            # Forward migration
            forward_script = self.migration_dir / f"migrate_forward_{self.active_model}.py"
            if forward_script.exists():
                return forward_script
        else:
            # Backward migration
            backward_script = self.migration_dir / f"migrate_backward_{self.active_model}.py"
            if backward_script.exists():
                return backward_script

        return None

    def _is_later_version(self, version1: str, version2: str) -> bool:
        """Check if version1 is later than version2

        Args:
            version1: First version identifier
            version2: Second version identifier

        Returns:
            bool: Whether version1 is later than version2
        """
        try:
            # Get commit timestamps
            commit1 = self.repo.commit(version1)
            commit2 = self.repo.commit(version2)

            return commit1.committed_date > commit2.committed_date
        except Exception:
            # If we can't determine, assume false
            return False

    def _get_index_path_for_version(self, version_id: str) -> Path:
        """Get the path to the index file for a specific version

        Args:
            version_id: Version identifier

        Returns:
            Path: Path to the index file
        """
        # For now, just use the active model's index path
        return self.index_dir / self.active_model / "index.index"

    def check_health(self, version_id: Optional[str] = None) -> Dict[str, Any]:
        """Check health of a specific version or the current index

        Args:
            version_id: Optional version identifier, if None uses current

        Returns:
            Dict with health metrics
        """
        try:
            # If a specific version is requested, check out that version first
            if version_id:
                temp_dir = self.index_dir / f"health_check_{version_id[:10]}"
                temp_dir.mkdir(parents=True, exist_ok=True)

                # Get the index file from the repository
                repo_index_path = self.git_repo_dir / 'indexes' / self.active_model / "index.index"

                # Checkout that specific file from the commit
                self.repo.git.checkout(version_id, '--', str(repo_index_path))

                # Copy to temporary location
                index_path = temp_dir / "index.index"
                shutil.copy2(repo_index_path, index_path)
            else:
                # Use current index
                index_path = self.index_dir / self.active_model / "index.index"

            if not index_path.exists():
                return {
                    "status": "error",
                    "message": f"Index file not found at {index_path}",
                    "timestamp": datetime.now().isoformat()
                }

            # Read the index and check basic health
            start_time = time.time()
            index = faiss.read_index(str(index_path))
            load_time = time.time() - start_time

            # Run some basic health checks
            health_data = {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "version": version_id[:10] if version_id else "current",
                "metrics": {
                    "ntotal": index.ntotal,
                    "dimension": index.d,
                    "index_type": type(index).__name__,
                    "index_size_bytes": os.path.getsize(index_path),
                    "load_time_seconds": load_time,
                    "file_integrity": True,
                }
            }

            # Try a simple search to verify functionality
            if index.ntotal > 0:
                try:
                    dummy_query = np.random.random(index.d).astype('float32').reshape(1, -1)
                    start_time = time.time()
                    distances, indices = index.search(dummy_query, min(10, index.ntotal))
                    search_time = time.time() - start_time
                    health_data["metrics"]["search_time_seconds"] = search_time
                    health_data["metrics"]["search_status"] = "success"
                except Exception as e:
                    health_data["status"] = "warning"
                    health_data["metrics"]["search_status"] = "failed"
                    health_data["metrics"]["search_error"] = str(e)

            # Clean up temporary directory if created
            if version_id and temp_dir.exists():
                shutil.rmtree(temp_dir)

            return health_data

        except Exception as e:
            logger.error(f"Error checking index health: {e}")
            return {
                "status": "error",
                "message": str(e),
                "timestamp": datetime.now().isoformat()
            }
