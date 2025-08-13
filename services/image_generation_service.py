"""Image generation service using SANA model."""

import os
import logging
import datetime
import torch
import gc
from diffusers import SanaSprintPipeline
import time
import config

# Set environment variables for better memory management
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "max_split_size_mb:128"
os.environ["CUDA_LAUNCH_BLOCKING"] = "0"

logger = logging.getLogger(__name__)

class ImageGenerationService:
    def __init__(self):
        self.sana_pipeline = None
        self.is_loaded = False
        self.model_path = "Efficient-Large-Model/Sana_Sprint_0.6B_1024px_diffusers"
        self.device = None
        
    def _clear_gpu_memory(self):
        """Clear GPU memory to prevent fragmentation."""
        try:
            if torch.cuda.is_available():
                # More aggressive memory clearing
                torch.cuda.empty_cache()
                gc.collect()
                
        except Exception as e:
            logger.warning(f"Could not clear GPU memory: {e}")
    
    def move_sana_pipeline_to_device(self, device="cuda:0"):
        """Move SANA pipeline to specified device (GPU or CPU)."""
        try:
            if self.sana_pipeline is None:
                logger.warning("SANA pipeline is not loaded")
                return False
            
            logger.info(f"Moving SANA pipeline to {device}")


            if self.device == device:
                logger.info(f"SANA pipeline is already on {device}")
                return True
            
            # Move pipeline to specified device
            self.sana_pipeline.to(device)
            self.device = device
            
            # Clear GPU memory after moving to CPU
            if device == "cpu":
                self._clear_gpu_memory()
            
            logger.info(f"Successfully moved SANA pipeline to {device}")
            return True
            
        except Exception as e:
            logger.error(f"Error moving SANA pipeline to {device}: {e}")
            return False
    
    def move_sana_pipeline_to_gpu(self):
        """Move SANA pipeline to GPU."""
        return self.move_sana_pipeline_to_device("cuda:0")
    
    def move_sana_pipeline_to_cpu(self):
        """Move SANA pipeline to CPU."""
        return self.move_sana_pipeline_to_device("cpu")
    
    def load_sana_model(self, device="cuda:0", force_reload=False):
        """Load the SANA model for image generation with optimizations."""
        try:
            print(f"🕐 Timestamp before load_sana_model: {time.time()}")
            if self.is_loaded and self.sana_pipeline is not None and not force_reload:
                logger.info("SANA model already loaded")
                self.move_sana_pipeline_to_device(device)
                return True
            
            print(f"🕐 Timestamp after load_sana_model: {time.time()}")
            # Clear GPU memory before loading
            self._clear_gpu_memory() 
            print(f"🕐 Timestamp after clear_gpu_memory: {time.time()}")
            
            logger.info("Loading SANA model...")
            
            initial_time = time.time()
            # Load model with optimizations and directly to GPU
            self.sana_pipeline = SanaSprintPipeline.from_pretrained(
                self.model_path,
                torch_dtype=torch.bfloat16,
            )
            print(f"🕐 Timestamp after load_sana_model: {time.time()}")
            print(f"Time taken to load SANA model: {time.time() - initial_time} seconds")
            
            initial_time = time.time()
            # Move to GPU with memory optimization
            self.move_sana_pipeline_to_device("cuda:0")
            
            print(f"Time taken to move SANA model to GPU: {time.time() - initial_time} seconds")
            print(f"🕐 Timestamp after move_sana_model_to_gpu: {time.time()}")
        
            self.is_loaded = True
            logger.info("Successfully loaded SANA model")   
            
            return True
            
        except Exception as e:
            logger.error(f"Error loading SANA model: {e}")
            self.is_loaded = False
            self.sana_pipeline = None
            return False
        
    def cleanup_sana_pipeline(self):
        """Clean up the current model"""
        if self.sana_pipeline is not None:
            try:
                # Move to CPU first
                if hasattr(self.sana_pipeline, 'cuda'):
                    self.sana_pipeline.cpu()

                # Clear internal tensors if any
                if hasattr(self.sana_pipeline, '__dict__'):
                    for k, v in list(vars(self.sana_pipeline).items()):
                        if torch.is_tensor(v):
                            setattr(self.sana_pipeline, k, None)
                            del v
                # Delete the model reference
                del self.sana_pipeline
                self.sana_pipeline = None
                self.is_loaded = False
                self.device = None

                self._clear_gpu_memory()
                logger.info("Successfully cleaned up SANA pipeline")
            except Exception as e:
                logger.error(f"Error during cleanup: {e}")

    def check_gpu_vram_capacity(self, vram_threshold=config.VRAM_THRESHOLD):
        """Check if the GPU has vram_threshold or less VRAM capacity."""
        try:
            if not torch.cuda.is_available():
                logger.warning("No CUDA-capable GPU found")
                return False
                
            # Get total VRAM capacity in bytes
            total_vram = torch.cuda.get_device_properties(0).total_memory
            # Convert to GB
            total_vram_gb = total_vram / (1024**3)
            
            logger.info(f"Total GPU VRAM: {total_vram_gb:.2f} GB")
            logger.info(f"VRAM threshold: {vram_threshold} GB")
            logger.info(f"VRAM check result: {total_vram_gb <= vram_threshold}")
            
            # Return True if VRAM is vram_threshold or less
            return total_vram_gb <= vram_threshold
        except Exception as e:
            logger.error(f"Error checking GPU VRAM capacity: {e}")
            return False
        

    def if_sana_pipeline_movement_required(self, vram_threshold=config.VRAM_THRESHOLD):
        """Check if the SANA pipeline needs to be moved to GPU or CPU."""
        return self.check_gpu_vram_capacity(vram_threshold)
        
    
    def generate_image_from_prompt(self, object_name, prompt, output_dir, seed=42):
        """Generate a single image from a prompt using SANA model."""
        try:
            if not self.load_sana_model():
                return False, "Failed to load SANA model", None
            
            # Format object name: lowercase and replace spaces with underscores
            formatted_object_name = object_name.lower().replace(" ", "_")
            
            # Generate image - SCM requires num_inference_steps=2
            with torch.no_grad():  # Reduce memory usage during inference
                image = self.sana_pipeline(
                    prompt=prompt,
                    num_inference_steps=2,  # SCM requirement
                    generator=torch.Generator("cuda").manual_seed(seed)
                ).images[0]
            
            # Create output directory if it doesn't exist
            os.makedirs(output_dir, exist_ok=True)
            
            # Generate timestamp
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Create filename using convention: objectname_seed_timestamp
            image_path = os.path.join(output_dir, f"{formatted_object_name}_{seed}_{timestamp}.png")
            
            # Save the image
            image.save(image_path)
            
            logger.info(f"Generated image: {image_path}")
            
            return True, f"Successfully generated image for {object_name}", image_path
            
        except Exception as e:
            logger.error(f"Error generating image: {e}")
            return False, f"Error generating image: {str(e)}", None
    
    def generate_images_for_objects(self, objects_data, output_dir="static/images/generated"):
        """Generate images for all objects in the gallery data."""
        try:
            if not self.load_sana_model():
                return False, "Failed to load SANA model", {}
            
            # Create output directory
            os.makedirs(output_dir, exist_ok=True)
            
            generated_images = {}
            for obj in objects_data:
                object_name = obj["title"]
                prompt = obj["description"]
                
                logger.info(f"Generating image for: {object_name}")
                success, message, image_path = self.generate_image_from_prompt(
                    object_name, prompt, output_dir
                )
                
                if success and image_path:
                    generated_images[object_name] = image_path
                    logger.info(f"Generated image for {object_name}: {image_path}")
                else:
                    logger.error(f"Failed to generate image for {object_name}: {message}")
            
            return True, f"Generated {len(generated_images)} images", generated_images
            
        except Exception as e:
            logger.error(f"Error generating images for objects: {e}")
            return False, f"Error generating images: {str(e)}", {} 