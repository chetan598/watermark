#!/usr/bin/env bash
# Render build script

set -o errexit

echo "Installing system dependencies..."
apt-get update
apt-get install -y ffmpeg libsm6 libxext6 libxrender-dev libgomp1 libgl1-mesa-glx

echo "Installing Python packages..."
pip install --upgrade pip
pip install -r requirements.txt

echo "Build complete!"

