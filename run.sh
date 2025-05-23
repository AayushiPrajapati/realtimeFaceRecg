#!/bin/bash

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Docker is not installed. Please install Docker before running this script."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "Docker Compose is not installed. Please install Docker Compose before running this script."
    exit 1
fi

# Function to allow X11 connections from Docker
setup_x11() {
    echo "Setting up X11 permissions for Docker..."
    xhost +local:docker
}

# Create required directories if they don't exist
mkdir -p data models mlruns db templates static

# Check if the webcam is available
if [ ! -c /dev/video0 ]; then
    echo "Warning: No webcam found at /dev/video0. The recognition service may not work properly."
fi

# Check if the data directory has any files
if [ -z "$(ls -A data 2>/dev/null)" ]; then
    echo "Warning: The data directory is empty. You should add face images to the data directory before training."
    echo "Create subdirectories for each person (e.g., data/1/, data/2/) and add face images to these directories."
fi

# Setup X11 for GUI applications
setup_x11

# Start the containers
echo "Starting the Face Recognition system..."
docker-compose up -d

echo "The system is now running!"
echo "Web interface available at: http://localhost:5002"
echo "MLFlow tracking available at: http://localhost:5050"
echo ""
echo "To stop the system, run: docker-compose down"
