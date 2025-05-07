import os

from flask import Blueprint, current_app, jsonify
from services.default_embedding_service import ModelRegistry

models_bp = Blueprint("models", __name__)


@models_bp.route("/list")
def list_models():
    """Endpoint to list all available models"""
    available_models = ModelRegistry.get_available_models()
    return jsonify(
        {
            "models": [
                {"version": version, "name": name} for version, name in available_models.items()
            ],
            "active_model": current_app.config["ACTIVE_MODEL"],
        }
    )


@models_bp.route("/switch/<version>")
def switch_model(version):
    """Endpoint to switch the active model

    Args:
        version: The version of the model to switch to
    """
    # Check if the requested model version exists
    available_models = ModelRegistry.get_available_models()
    if version not in available_models:
        return jsonify({"error": "Invalid model version"}), 400

    # Update the active model
    current_app.config["ACTIVE_MODEL"] = version

    # Save to active_model.txt
    active_model_path = os.path.join(current_app.config["MODELS_DIR"], "active_model.txt")
    with open(active_model_path, "w") as f:
        f.write(version)

    # Update services with the new model
    current_app.setup_services()

    return jsonify(
        {
            "status": "success",
            "active_model": version,
            "model_name": available_models[version],
        }
    )
