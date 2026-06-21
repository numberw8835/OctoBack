#!/usr/bin/env bash

set -e

echo "Building standalone binary using PyInstaller..."

# 1. Compile with PyInstaller
pyinstaller --onefile --name octoback \
    --exclude-module numpy \
    --exclude-module scipy \
    --exclude-module matplotlib \
    --exclude-module pandas \
    --exclude-module sympy \
    --exclude-module pygraphviz \
    --exclude-module IPython \
    --exclude-module jedi \
    --exclude-module PyQt6 \
    --exclude-module torch \
    --exclude-module torchvision \
    --exclude-module torchaudio \
    --exclude-module onnxruntime \
    --exclude-module pyarrow \
    --exclude-module numba \
    --exclude-module llvmlite \
    --exclude-module tkinter \
    --exclude-module zmq \
    --exclude-module lxml \
    --exclude-module qtpy \
    --exclude-module cryptography \
    --exclude-module orjson \
    octoback.py

# 2. Copy binary to ~/.local/bin
BIN_DIR="$HOME/.local/bin"
mkdir -p "$BIN_DIR"
echo "Installing binary to $BIN_DIR/octoback..."
cp dist/octoback "$BIN_DIR/octoback"

# 3. Clean up build artifacts to keep repository clean
echo "Cleaning up build artifacts..."
rm -rf build dist octoback.spec

echo "Build and installation complete!"
echo "You can now run 'octoback' directly from your terminal."
