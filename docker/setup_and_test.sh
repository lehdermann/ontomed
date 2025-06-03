#!/bin/bash

# Script to set up and test Blazegraph for the HMARL+GenAI system

echo "=== Blazegraph Setup for the HMARL+GenAI System ==="
echo "This script will:"
echo "1. Start the Blazegraph server on port 9999"
echo "2. Initialize the required namespaces"
echo "3. Test the integration with the Circadian Explanation Agent"
echo ""

# Current directory
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

# Check dependencies
echo "Checking dependencies..."
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "Error: Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed. Please install Python 3 first."
    exit 1
fi

# Check if the requests module is installed
if ! python3 -c "import requests" &> /dev/null; then
    echo "Installing Python 'requests' module..."
    pip3 install requests
fi

# Step 1: Start the Blazegraph server
echo ""
echo "Step 1: Starting the Blazegraph server..."
./start_blazegraph.sh

# Wait a bit for the container to start
echo "Waiting for the server to start..."
sleep 10

# Step 2: Initialize the namespaces
echo ""
echo "Step 2: Initializing namespaces..."
python3 init_namespaces.py

# Step 3: Test the integration
echo ""
echo "Step 3: Testing integration with the HMARL+GenAI system..."

# Project directory
PROJECT_DIR="$(cd "$DIR/../.." && pwd)"

# Run the graph database integration demo script
echo "Running the graph database integration demo script..."
cd "$PROJECT_DIR"
python examples/graph_db_integration_example.py

# Check the result
if [ $? -eq 0 ]; then
    echo ""
    echo "=== Setup completed successfully! ==="
    echo "The Blazegraph server is running on port 9999"
    echo "Namespaces have been initialized"
    echo "Integration with the HMARL+GenAI system has been tested"
    echo ""
    echo "You can access the Blazegraph web interface at: http://localhost:9999/blazegraph/"
    echo "SPARQL endpoint: http://localhost:9999/blazegraph/sparql"
    echo ""
    echo "To stop the server, run: ./stop_blazegraph.sh"
else
    echo ""
    echo "=== Error during setup ==="
    echo "An error occurred while testing the integration with the HMARL+GenAI system."
    echo "Check the logs for more details."
    echo ""
    echo "The Blazegraph server will continue running for debugging."
    echo "To stop the server, run: ./stop_blazegraph.sh"
    exit 1
fi
