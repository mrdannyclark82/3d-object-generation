#!/usr/bin/env python3
"""
Service health checker for LLM and Trellis services.
This script checks if the services are running and ready.
"""

import requests
import time
import sys
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def check_service_health(url, service_name, timeout=5):
    """Check if a service is healthy."""
    try:
        response = requests.get(url, timeout=timeout)
        if response.status_code == 200:
            logger.info(f"{service_name} is ready")
            return True
        else:
            logger.debug(f"{service_name} returned status {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        logger.debug(f"{service_name} not ready: {e}")
        return False

def main():
    """Main function to check both services."""
    llm_url = "http://localhost:19002/v1/health/ready"
    trellis_url = "http://localhost:8000/v1/health/ready"
    
    llm_ready = check_service_health(llm_url, "LLM Service")
    trellis_ready = check_service_health(trellis_url, "Trellis Service")
    
    # Return exit code based on service status
    if llm_ready and trellis_ready:
        print("ALL_READY")
        sys.exit(0)
    elif llm_ready:
        print("LLM_READY")
        sys.exit(1)
    elif trellis_ready:
        print("TRELLIS_READY")
        sys.exit(2)
    else:
        print("NONE_READY")
        sys.exit(3)

if __name__ == "__main__":
    main() 