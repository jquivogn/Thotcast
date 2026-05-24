#!/usr/bin/env bash
# Thotcast — environment setup script
# Tested on Ubuntu Server 22.04 with NVIDIA T400 + CUDA 13.x

set -euo pipefail

VENV_DIR=".venv"

echo "=== [1/5] Creating Python virtual environment ==="
python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"

echo "=== [2/5] Installing base dependencies ==="
pip install --upgrade pip
pip install -r requirements.txt

echo "=== [3/5] Installing TTS backend (kokoro-onnx + onnxruntime-gpu) ==="
pip install kokoro-onnx onnxruntime-gpu soundfile

echo "=== [4/5] Downloading Kokoro model files ==="
if [ ! -f "kokoro-v0_19.onnx" ]; then
    wget -q --show-progress \
        https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files/kokoro-v0_19.onnx
fi
if [ ! -f "voices.json" ]; then
    wget -q --show-progress \
        https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files/voices.json
fi

echo "=== [5/5] Checking Ollama + Llama 3.1 model ==="
if ! command -v ollama &>/dev/null; then
    echo "  Ollama not found. Install it: https://ollama.com/download"
else
    echo "  Pulling llama3.1:8b (skipped if already present)..."
    ollama pull llama3.1:8b
fi

echo ""
echo "Setup complete. Start the API with:"
echo "  source $VENV_DIR/bin/activate"
echo "  uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
