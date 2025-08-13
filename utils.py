"""Utility functions for Chat-to-3D application."""

import json
import logging
from pathlib import Path
from datetime import datetime
import torch
import config


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


def check_gpu_vram_capacity(vram_threshold):
    """Check if the GPU has vram_threshold or less VRAM capacity."""
    try:
        if not torch.cuda.is_available():
            logging.warning("No CUDA-capable GPU found")
            return False
            
        # Get total VRAM capacity in bytes
        total_vram = torch.cuda.get_device_properties(0).total_memory
        # Convert to GB
        total_vram_gb = total_vram / (1024**3)
        
        logging.info(f"Total GPU VRAM: {total_vram_gb:.2f} GB")
        logging.info(f"VRAM threshold: {vram_threshold} GB")
        logging.info(f"VRAM check result: {total_vram_gb <= vram_threshold}")
        
        # Return True if VRAM is vram_threshold or less
        return total_vram_gb <= vram_threshold
    except Exception as e:
        logging.error(f"Error checking GPU VRAM capacity: {e}")
        return False 
    


def is_llm_should_be_stopped(vram_threshold = config.VRAM_THRESHOLD_LLM):
    """Check if the LLM should be stopped."""
    return not check_gpu_vram_capacity(vram_threshold)


def should_disable_buttons_during_3d_generation(vram_threshold = config.VRAM_THRESHOLD_SANA):
    """Check if buttons should be disabled during 3D generation based on VRAM threshold."""
    return check_gpu_vram_capacity(vram_threshold)


def disable_all_buttons_for_3d_generation(gallery_data):
    """Disable all edit and refresh buttons on all cards when 3D generation is in progress."""
    if not should_disable_buttons_during_3d_generation():
        return gallery_data
    
    updated_data = gallery_data.copy()
    
    # Mark all items as having 3D generation in progress to disable buttons
    for idx, obj in enumerate(updated_data):
        updated_data[idx]["3d_generation_global"] = True
    
    print(f"🔒 Disabled all edit/refresh buttons for {len(gallery_data)} items during 3D generation (VRAM threshold met)")
    return updated_data


def enable_all_buttons_after_3d_generation(gallery_data):
    """Re-enable all edit and refresh buttons on all cards after 3D generation completes."""
    updated_data = gallery_data.copy()
    
    # Clear the global 3D generation flag for all items
    for idx, obj in enumerate(updated_data):
        if "3d_generation_global" in updated_data[idx]:
            del updated_data[idx]["3d_generation_global"]
    
    print(f"🔓 Re-enabled all edit/refresh buttons for {len(gallery_data)} items after 3D generation")
    return updated_data