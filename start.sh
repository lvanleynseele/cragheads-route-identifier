#!/bin/bash

# Exit on error
set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Starting Image Processing Service...${NC}"

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Python 3 is not installed. Please install Python 3 and try again.${NC}"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv venv
fi

# Activate virtual environment
echo -e "${YELLOW}Activating virtual environment...${NC}"
source venv/bin/activate

# Install/upgrade pip
echo -e "${YELLOW}Upgrading pip...${NC}"
python -m pip install --upgrade pip

# Install requirements
echo -e "${YELLOW}Installing dependencies...${NC}"
pip install -r requirements.txt

# Verify critical dependencies
echo -e "${YELLOW}Verifying dependencies...${NC}"
python -c "import fastapi; import uvicorn; import psutil; import cv2; import numpy; import PIL" || {
    echo -e "${RED}Failed to verify dependencies. Please check the installation.${NC}"
    exit 1
}

# Create necessary directories
echo -e "${YELLOW}Setting up directories...${NC}"
mkdir -p logs

# Start the service
echo -e "${GREEN}Starting service on port 3020...${NC}"
uvicorn main:app --host 0.0.0.0 --port 3020 --reload --log-level info 