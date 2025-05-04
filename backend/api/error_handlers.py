from flask import jsonify
from werkzeug.exceptions import HTTPException
import traceback
import logging


logger = logging.getLogger(__name__)


def register_error_handlers(app):
    """Register error handlers with the Flask application

    Args:
        app: Flask application instance
    """
    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({"error": "Bad request", "message": str(error)}), 400

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": "Not found", "message": str(error)}), 404

    @app.errorhandler(405)
    def method_not_allowed(error):
        return jsonify({"error": "Method not allowed", "message": str(error)}), 405

    @app.errorhandler(500)
    def server_error(error):
        logger.error(f"500 error: {error}\n{traceback.format_exc()}")
        return jsonify({"error": "Internal server error", "message": "An internal error occurred"}), 500

    @app.errorhandler(Exception)
    def handle_exception(error):
        # Pass through HTTP exceptions
        if isinstance(error, HTTPException):
            return error

        # Log the error
        logger.error(f"Unhandled exception: {error}\n{traceback.format_exc()}")

        # Return a generic server error
        return jsonify({
            "error": "Internal server error",
            "message": "An unexpected error occurred"
        }), 500
