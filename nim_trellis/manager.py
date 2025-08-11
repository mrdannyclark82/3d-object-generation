import subprocess
import sys
import os
from pathlib import Path

from .constants import CONTAINER_NAME


def stop_container() -> bool:
    """Stop the TRELLIS NIM podman container if it is running.

    Returns True if the kill command executed (even if the container wasn't running),
    False if the command failed to execute.
    """
    try:
        # Prefer running inside WSL if available, mirroring run_llama.py behavior
        if os.name == "nt":
            # Use WSL to call podman
            cmd = [
                "wsl", "-d", "NVIDIA-Workbench", "/bin/bash", "-lc",
                f"podman kill {CONTAINER_NAME} || true"
            ]
        else:
            cmd = ["bash", "-lc", f"podman kill {CONTAINER_NAME} || true"]

        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=15)
        print(result.stdout.strip())
        return result.returncode == 0
    except Exception as e:
        print(f"Failed to stop container {CONTAINER_NAME}: {e}")
        return False 