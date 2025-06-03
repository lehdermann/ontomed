#!/bin/bash

# Script to start the Blazegraph server for the HMARL+GenAI system

echo "=== Starting Blazegraph server for HMARL+GenAI ==="
echo "Access port: 9999"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "Error: Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Current directory
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

# Start the container
echo "Building and starting the Blazegraph container..."
docker-compose up -d --build

# Check if the container is running
if [ $? -eq 0 ]; then
    echo "Container started successfully!"
    echo "The Blazegraph server will be available at: http://localhost:9999/blazegraph/"
    echo "SPARQL endpoint: http://localhost:9999/blazegraph/sparql"
    echo ""
    echo "To check the container logs, run:"
    echo "docker-compose logs -f"
    echo ""
    echo "To stop the container, run:"
    echo "docker-compose down"
else
    echo "Error starting the container. Check the logs for details."
    exit 1
fi
