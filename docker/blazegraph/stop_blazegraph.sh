#!/bin/bash

# Script to stop the Blazegraph server for the HMARL+GenAI system

echo "=== Stopping Blazegraph server for HMARL+GenAI ==="

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "Error: Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Current directory
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

# Stop the container
echo "Stopping the Blazegraph container..."
docker-compose down

# Check if the container was stopped
if [ $? -eq 0 ]; then
    echo "Container stopped successfully!"
else
    echo "Error stopping the container. Check the logs for details."
    exit 1
fi
