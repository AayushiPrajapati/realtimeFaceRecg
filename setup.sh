#!/bin/bash
# This script sets up the directory structure for the face recognition system

# Create required directories
mkdir -p data
mkdir -p models
mkdir -p mlruns
mkdir -p db
mkdir -p templates
mkdir -p static

# Create empty .gitkeep files in empty directories to ensure they're tracked in git
touch data/.gitkeep
touch models/.gitkeep
touch mlruns/.gitkeep
touch db/.gitkeep
touch static/.gitkeep

echo "Directory structure created successfully!"
