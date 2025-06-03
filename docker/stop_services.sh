#!/bin/bash

# Script to stop MedKnowBridge services

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Stopping MedKnowBridge services...${NC}"

# Navigate to the docker directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Stop the services
docker-compose down

echo -e "${GREEN}MedKnowBridge services stopped.${NC}"
