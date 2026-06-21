#!/usr/bin/env bash

set -e

echo "Building standalone binary using PyInstaller..."

# 1. Compile with PyInstaller
pyinstaller --onedir --name octoback \
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

# 2. Copy folder to ~/.local/share and create symlink
BIN_DIR="$HOME/.local/bin"
SHARE_DIR="$HOME/.local/share"
mkdir -p "$BIN_DIR" "$SHARE_DIR"
echo "Installing directory to $SHARE_DIR/octoback..."
rm -rf "$SHARE_DIR/octoback"
cp -r dist/octoback "$SHARE_DIR/octoback"
echo "Creating symlink in $BIN_DIR/octoback..."
ln -sf "$SHARE_DIR/octoback/octoback" "$BIN_DIR/octoback"

# 3. Clean up build artifacts to keep repository clean
echo "Cleaning up build artifacts..."
rm -rf build dist octoback.spec

echo "Build and installation complete!"
echo "You can now run 'octoback' directly from your terminal."
