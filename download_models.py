import torch
import gc

from diffusers import SanaSprintPipeline
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def download_models():
    try:
        logger.info("Starting model downloads...")
        
        # Download Sana Sprint model
        logger.info("Downloading Sana Sprint model...")
        sana_model = SanaSprintPipeline.from_pretrained(
            "Efficient-Large-Model/Sana_Sprint_0.6B_1024px_diffusers",
            torch_dtype=torch.bfloat16
        )
        del sana_model
        gc.collect()
        torch.cuda.empty_cache()
        logger.info("Sana Sprint model downloaded successfully!")
        
        logger.info("All models downloaded successfully!")
        return True
    except Exception as e:
        logger.error(f"Error downloading models: {e}")
        return False

if __name__ == "__main__":
    download_models() 