"""Utility functions for Chat-to-3D application."""

import json
import logging
from pathlib import Path
from datetime import datetime


def setup_logging(level="INFO"):
    """Set up logging configuration."""
    logging.basicConfig(
        level=getattr(logging, level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )


def save_json(data, filepath):
    """Save data to JSON file."""
    try:
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        logging.error(f"Failed to save JSON to {filepath}: {e}")
        return False


def load_json(filepath):
    """Load data from JSON file."""
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Failed to load JSON from {filepath}: {e}")
        return None


def ensure_dir(path):
    """Ensure directory exists."""
    Path(path).mkdir(parents=True, exist_ok=True)


def get_timestamp():
    """Get current timestamp as string."""
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def clear_image_generation_failure_flags(obj):
    """
    Clear image generation failure flags from an object.
    
    Args:
        obj (dict): The object dictionary containing image generation flags
        
    Returns:
        dict: The object with failure flags cleared
    """
    # Clear any previous failure flags since image generation succeeded
    if "image_generation_failed" in obj:
        del obj["image_generation_failed"]
    if "image_generation_error" in obj:
        del obj["image_generation_error"]
    if "prompt_content_filtered" in obj:
        del obj["prompt_content_filtered"]
    if "prompt_content_filtered_timestamp" in obj:
        del obj["prompt_content_filtered_timestamp"]
    
    return obj 