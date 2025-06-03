#!/bin/bash

# Script to start MedKnowBridge services using Docker Compose

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Starting MedKnowBridge services...${NC}"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
  echo -e "${RED}Error: Docker is not running. Please start Docker and try again.${NC}"
  exit 1
fi

# Navigate to the docker directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Build and start the services
echo -e "${YELLOW}Building and starting containers...${NC}"
docker-compose up -d --build

# Wait for services to be healthy
echo -e "${YELLOW}Waiting for services to be ready...${NC}"
MAX_RETRIES=30
RETRY_INTERVAL=5
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
  BLAZEGRAPH_HEALTHY=$(docker inspect --format='{{.State.Health.Status}}' medknowbridge_blazegraph 2>/dev/null)
  API_HEALTHY=$(docker inspect --format='{{.State.Health.Status}}' medknowbridge_api 2>/dev/null)
  
  if [ "$BLAZEGRAPH_HEALTHY" = "healthy" ] && [ "$API_HEALTHY" = "healthy" ]; then
    echo -e "${GREEN}All services are healthy!${NC}"
    break
  fi
  
  echo -e "${YELLOW}Waiting for services to be healthy... (${RETRY_COUNT}/${MAX_RETRIES})${NC}"
  echo -e "  Blazegraph: ${BLAZEGRAPH_HEALTHY:-starting}"
  echo -e "  API: ${API_HEALTHY:-starting}"
  
  RETRY_COUNT=$((RETRY_COUNT + 1))
  sleep $RETRY_INTERVAL
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
  echo -e "${RED}Timeout waiting for services to be healthy.${NC}"
  echo -e "${YELLOW}You can check the logs with: docker-compose logs${NC}"
  exit 1
fi

# Initialize Blazegraph namespaces
echo -e "${YELLOW}Initializing Blazegraph namespaces...${NC}"
docker-compose exec medknowbridge python docker/init_namespaces.py

# Load sample medical knowledge data
echo -e "${YELLOW}Loading sample medical knowledge data...${NC}"
docker-compose exec medknowbridge python docker/load_sample_data.py

echo -e "${GREEN}MedKnowBridge services are running!${NC}"
echo -e "${GREEN}API is available at: http://localhost:8000${NC}"
echo -e "${GREEN}API Documentation: http://localhost:8000/docs${NC}"
echo -e "${GREEN}Blazegraph is available at: http://localhost:9998/blazegraph${NC}"
echo -e "${YELLOW}To stop the services, run: ./stop_services.sh${NC}"
