#!/usr/bin/env python
# Copyright 2024 NVIDIA CORPORATION & AFFILIATES
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0

import logging
import torch
from torch.nn.functional import softmax
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
import config

logger = logging.getLogger(__name__)

class GuardrailService:
    """Service for content filtering using ShieldGemma model."""
    
    def __init__(self, shield_model_path="google/shieldgemma-2b"):
        """Initialize the guardrail service with ShieldGemma model."""
        self.shield_model_path = shield_model_path
        self.tokenizer = None
        self.model = None
        self.device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
        self.is_loaded = False
        
    def load_model(self):
        """Load the ShieldGemma model for content filtering."""
        try:
            if self.is_loaded:
                return True
                
            if not torch.cuda.is_available():
                logger.warning("No CUDA-capable GPU found for guardrail service")
                return False
            
            logger.info(f"Loading ShieldGemma model from {self.shield_model_path}")
            
            # Load tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(self.shield_model_path)
            
            # Load model with 4-bit quantization for efficiency
            qconfig = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.bfloat16,
                bnb_4bit_use_double_quant=True
            )
            
            self.model = AutoModelForCausalLM.from_pretrained(
                self.shield_model_path, 
                device_map="auto", 
                quantization_config=qconfig, 
                trust_remote_code=True
            )
            
            self.model.to(self.device)
            self.is_loaded = True
            
            logger.info("✅ ShieldGemma model loaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to load ShieldGemma model: {e}")
            return False
    
    def is_dangerous(self, prompt, threshold=0.2):
        """Check if a prompt violates safety policies."""
        try:
            if not self.load_model():
                logger.warning("Guardrail model not loaded, skipping content check")
                return False
            
            safety_policy = """
                The prompt must not seek to generate harmful, abusive, hateful, sexually explicit, or otherwise inappropriate content targeting individuals or protected groups.
            """
            
            evaluation_prompt = f"""You are a policy expert trying to help determine whether a user
            prompt is in violation of the defined safety policies.

            <start_of_turn>
            Human Question: {prompt.strip()}
            <end_of_turn>

            Our safety principle is defined in the below:

            {safety_policy.strip()}

            Does the human question violate the above principle? Your answer must start
            with 'Yes' or 'No'. And then walk through step by step to be sure we answer
            correctly.
            """

            inputs = self.tokenizer(evaluation_prompt, return_tensors="pt").to(self.device)
            
            with torch.no_grad():
                logits = self.model(**inputs).logits

            # Extract the logits for the Yes and No tokens
            vocab = self.tokenizer.get_vocab()
            selected_logits = logits[0, -1, [vocab["Yes"], vocab["No"]]]

            # Convert these logits to a probability with softmax
            probabilities = softmax(selected_logits, dim=0)

            # Return probability of 'Yes' (violation)
            score = probabilities[0].item()
            
            logger.info(f"Content safety score for prompt: {score:.4f} (threshold: {threshold})")
            
            return score > threshold
            
        except Exception as e:
            logger.error(f"Error in content safety check: {e}")
            # In case of error, err on the side of caution and flag the content
            return True
    
    def check_prompt_safety(self, prompt, threshold=0.2):
        """Check if a prompt is safe for image generation."""
        try:
            is_violation = self.is_dangerous(prompt, threshold)
            
            if is_violation:
                logger.warning(f"2D prompt flagged as inappropriate: {prompt[:100]}...")
                return False, "PROMPT_CONTENT_FILTERED"
            else:
                logger.info(f"2D prompt passed safety check: {prompt[:100]}...")
                return True, "Content is safe for image generation"
                
        except Exception as e:
            logger.error(f"Error checking prompt safety: {e}")
            # In case of error, err on the side of caution
            return False, "Error in content safety check, please try again" 