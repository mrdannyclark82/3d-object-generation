import socket
import time
import logging
import os
import signal
import psutil
import subprocess

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Container names
LLM_CONTAINER_NAME = "CHAT_TO_3D"
TRELLIS_CONTAINER_NAME = "TRELLIS_NIM"

class TrellisTerminator:
    def __init__(self, host='localhost', port=12345):
        self.host = host
        self.port = port

    def is_server_running(self):
        """Check if the server is running by attempting to connect."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
                client.settimeout(0.5)
                client.connect((self.host, self.port))
            return True
        except (ConnectionRefusedError, socket.timeout):
            return False

    def is_container_running(self, container_name):
        """Check if the container is currently running.
        
        Returns True if the container exists and is running, False otherwise.
        """
        try:
            # Prefer running inside WSL if available
            if os.name == "nt":
                cmd = [
                    "wsl", "-d", "NVIDIA-Workbench", "/bin/bash", "-lc",
                    f"podman ps -a --format '{{{{.Names}}}} {{{{.Status}}}}' | grep '^{container_name}' || true"
                ]
            else:
                cmd = ["bash", "-lc", f"podman ps -a --format '{{{{.Names}}}} {{{{.Status}}}}' | grep '^{container_name}' || true"]

            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=10)
            
            if result.returncode == 0 and result.stdout.strip():
                # Container exists, check if it's running
                status_line = result.stdout.strip()
                if status_line:
                    logger.info(f"Container {container_name} status: {status_line}")
                    # Check if status indicates running (not "Exited", "Stopped", etc.)
                    if any(status in status_line.lower() for status in ["up", "running", "starting", "stopping"]):
                        return True
            return False
        except Exception as e:
            logger.error(f"Failed to check container status {container_name}: {e}")
            return False

    def stop_container(self, container_name):
        """Stop a podman container if it is running.

        Returns True if the container was successfully stopped or was not running,
        False if the stop operation failed.
        """
        try:
            # First check if container is running
            if not self.is_container_running(container_name):
                logger.info(f"Container {container_name} is not running")
                return True
            
            logger.info(f"Stopping container {container_name}...")
            
            # Prefer running inside WSL if available
            if os.name == "nt":
                # Use WSL to call podman
                cmd = [
                    "wsl", "-d", "NVIDIA-Workbench", "/bin/bash", "-lc",
                    f"podman kill {container_name} || true"
                ]
            else:
                cmd = ["bash", "-lc", f"podman stop {container_name} || true"]

            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=30)
            logger.info(result.stdout.strip())
            
            if result.returncode != 0:
                logger.warning(f"Warning: podman stop command failed with return code {result.returncode}")
            
            # Wait for container to actually stop
            logger.info("Waiting for container to stop...")
            start_time = time.time()
            timeout = 15  # 15 seconds timeout
            
            while time.time() - start_time < timeout:
                if not self.is_container_running(container_name):
                    logger.info(f"✅ Container {container_name} stopped successfully")
                    return True
                logger.info("Container still stopping, waiting...")
                time.sleep(1)
            
            # If container didn't stop gracefully, try force removal
            logger.warning(f"Container {container_name} did not stop within {timeout} seconds, attempting force removal...")
            
            if os.name == "nt":
                force_cmd = [
                    "wsl", "-d", "NVIDIA-Workbench", "/bin/bash", "-lc",
                    f"podman rm -f {container_name} || true"
                ]
            else:
                force_cmd = ["bash", "-lc", f"podman rm -f {container_name} || true"]
            
            force_result = subprocess.run(force_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=30)
            logger.info(force_result.stdout.strip())
            
            if force_result.returncode != 0:
                logger.warning(f"Warning: podman rm -f command failed with return code {force_result.returncode}")
            
            # Wait for container to be removed
            logger.info("Waiting for container to be removed...")
            start_time = time.time()
            while time.time() - start_time < timeout:
                if not self.is_container_running(container_name):
                    logger.info(f"✅ Container {container_name} force-removed successfully")
                    return True
                logger.info("Container still being removed, waiting...")
                time.sleep(1)
            
            logger.error(f"❌ Timeout: Container {container_name} could not be stopped or removed within {timeout} seconds")
            return False
            
        except Exception as e:
            logger.error(f"Failed to stop container {container_name}: {e}")
            return False

    def terminate_process(self, pid):
        """Terminate process with SIGTERM, fallback to SIGKILL if needed."""
        try:
            # Try graceful termination first
            os.kill(pid, signal.SIGTERM)
            logger.info(f"Sent SIGTERM to process {pid}")
            
            # Wait for process to terminate
            for _ in range(5):
                if not psutil.pid_exists(pid):
                    logger.info(f"Process {pid} terminated successfully")
                    return True
                time.sleep(1)
            
            # If still running, force kill
            if psutil.pid_exists(pid):
                logger.warning(f"Process {pid} did not terminate gracefully, sending SIGKILL")
                os.kill(pid, signal.SIGKILL)
                time.sleep(1)
                return not psutil.pid_exists(pid)
            
            return True
        except Exception as e:
            logger.error(f"Error terminating process {pid}: {e}")
            return False

    def stop_nim_containers(self):
        """Stop both LLM_NIM and TRELLIS NIM containers."""
        logger.info("Stopping NIM containers...")
        
        # Stop LLM NIM container
        logger.info("Stopping LLM NIM container...")
        llm_success = self.stop_container(LLM_CONTAINER_NAME)
        if llm_success:
            logger.info("✅ LLM NIM container stopped successfully")
        else:
            logger.warning("❌ Failed to stop LLM NIM container")
        
        # Stop TRELLIS NIM container
        logger.info("Stopping TRELLIS NIM container...")
        trellis_success = self.stop_container(TRELLIS_CONTAINER_NAME)
        if trellis_success:
            logger.info("✅ TRELLIS NIM container stopped successfully")
        else:
            logger.warning("❌ Failed to stop TRELLIS NIM container")
        
        
        return llm_success and trellis_success

    def terminate_and_wait(self):
        """Terminate TRELLIS process and NIM containers, then wait for them to end."""
        success = True
        
        # First stop NIM containers
        logger.info("Starting NIM container termination...")
        nim_success = self.stop_nim_containers()
        if not nim_success:
            success = False
            logger.warning("Some NIM containers failed to stop")
        
        # Then handle TRELLIS server if running
        if not self.is_server_running():
            logger.info("TRELLIS server not running")
        else:
            logger.info("TRELLIS server is running, attempting to terminate...")
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
                    client.settimeout(5)  # Increased timeout
                    client.connect((self.host, self.port))
                    logger.info("Connected to termination server, sending terminate command...")
                    client.send(b'terminate')
                    response = client.recv(1024)

                    if not response:
                        logger.error("No response received from server")
                        success = False
                    elif not response.startswith(b'terminating:'):
                        logger.error(f"Unexpected response: {response}")
                        success = False
                    else:
                        try:
                            pid = int(response.decode().split(':')[1])
                            logger.info(f"Received PID {pid} from server")
                            if not self.terminate_process(pid):
                                logger.warning(f"Failed to terminate process {pid}")
                                success = False
                            else:
                                logger.info(f"Successfully terminated process {pid}")
                        except (ValueError, IndexError) as e:
                            logger.error(f"Failed to parse PID from response '{response}': {e}")
                            success = False

            except Exception as e:
                logger.error(f"Error during TRELLIS server termination: {e}")
                success = False

        return success

def free_vram_for_blender():
    """Terminate TRELLIS process and NIM containers to free VRAM for Blender."""
    logger.info("Starting VRAM cleanup for Blender...")
    terminator = TrellisTerminator()
    
    # Check if server is running first
    if terminator.is_server_running():
        logger.info("✅ Termination server is running")
    else:
        logger.info("❌ Termination server is not running")
    
    if terminator.terminate_and_wait():
        print("✅ All services terminated successfully, proceeding with Blender operations")
    else:
        print("⚠️ Some services failed to terminate, please check processes manually")

if __name__ == "__main__":
    free_vram_for_blender()