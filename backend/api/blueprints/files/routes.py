from datetime import datetime

from flask import current_app, jsonify, request

from . import files_bp


@files_bp.route("/upload", methods=["POST"])
def upload_files():
    """Endpoint for uploading files to be processed

    The files will be added to the processing queue for asynchronous processing
    """
    files = request.files.getlist("files")
    if not files:
        return jsonify({"error": "No files provided"}), 400

    # Use the RabbitMQ-based processor if available, otherwise fall back to legacy queue
    if hasattr(current_app, "file_processor_producer"):
        task_ids = []

        for file in files:
            # Read file content
            content = file.read()

            # Submit to file processor
            task_id = current_app.file_processor_producer.submit_file(
                file_path=file.filename,
                file_content=content,
                metadata={
                    "original_filename": file.filename,
                    "content_type": file.content_type,
                    "submitted_at": datetime.now().isoformat(),
                },
            )
            task_ids.append(task_id)

        return jsonify({"task_ids": task_ids, "status": "queued", "files": len(files)})
    else:
        # Legacy queue processing
        queue_service = current_app.queue_service
        task_id = str(datetime.now().timestamp())

        # Add files to the queue
        for file in files:
            queue_service.add_task(file, task_id)

        return jsonify({"task_id": task_id, "status": "queued", "files": len(files)})


@files_bp.route("/status/<task_id>")
def task_status(task_id):
    """Endpoint to check the status of a file processing task"""
    # Use the RabbitMQ-based processor if available, otherwise fall back to legacy queue
    if hasattr(current_app, "file_processor_producer"):
        status = current_app.file_processor_producer.get_task_status(task_id)

        if status:
            return jsonify(status)
        else:
            return jsonify({"task_id": task_id, "status": "not_found"}), 404
    else:
        # Legacy queue processing
        queue_service = current_app.queue_service

        return jsonify(
            {
                "task_id": task_id,
                "status": "processing",
                "queue_stats": queue_service.get_queue_status(),
            }
        )


@files_bp.route("/tasks")
def list_tasks():
    """Endpoint to list all tasks with pagination and filtering

    Query parameters:
    - status: Filter by status (optional)
    - limit: Maximum number of tasks to return (default: 100)
    - offset: Number of tasks to skip (default: 0)
    """
    if not hasattr(current_app, "file_processor_producer"):
        return jsonify({"error": "Task listing not available"}), 501

    # Get query parameters
    status = request.args.get("status")
    try:
        limit = int(request.args.get("limit", 100))
        offset = int(request.args.get("offset", 0))
    except ValueError:
        return jsonify({"error": "Invalid limit or offset parameter"}), 400

    # Get tasks from producer
    tasks = current_app.file_processor_producer.list_tasks(
        status=status, limit=limit, offset=offset
    )

    return jsonify(
        {
            "tasks": tasks,
            "count": len(tasks),
            "limit": limit,
            "offset": offset,
            "status_filter": status,
        }
    )
