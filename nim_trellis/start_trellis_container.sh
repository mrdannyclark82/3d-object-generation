#!/bin/bash

# Get the NGC API key from the environment variable
#echo "Using NGC API Key: $NGC_API_KEY"
export NGC_API_KEY=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

# Ensure NGC_API_KEY is set before running podman
if [ -z "$NGC_API_KEY" ]; then
  echo "NGC API Key is missing!"
  exit 1
fi

# Require container name via environment
if [ -z "$CONTAINER_NAME" ]; then
  echo "Container name (CONTAINER_NAME) is missing!"
  exit 1
fi

# Login to nvcr.io
echo "$NGC_API_KEY" | podman login nvcr.io -u '$oauthtoken' --password-stdin

# Export env vars
export LOCAL_NIM_CACHE=/tmp/container_cache_nim

# Setup cache dir
mkdir -p "$LOCAL_NIM_CACHE"
chmod -R a+w "$LOCAL_NIM_CACHE"

# Run container
podman run --name "$CONTAINER_NAME" -it --rm \
    --user=root \
    --ipc=host \
    --net=host \
    --device nvidia.com/gpu=all \
    -e NGC_API_KEY=$NGC_API_KEY \
    -v "$LOCAL_NIM_CACHE:/opt/nim/.cache" \
    -e NIM_MANIFEST_PROFILE=a7ae7732f732b5a3e3a86a7aba5dd389b8f8707189052a284c0dbf2f92d0fa12 \
    -e NIM_TRITON_REQUEST_TIMEOUT=270000000 \
    -e NIM_OFFLOADING_POLICY=system_ram \
    nvcr.io/nvstaging/nim/trellis:1.0.0-rc.0-33155747
