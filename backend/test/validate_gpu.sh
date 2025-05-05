#!/bin/bash
# Validate GPU/CUDA setup in Docker environment

echo "===== GPU/CUDA Validation Script ====="
echo "Checking if NVIDIA drivers are accessible..."

# Check if nvidia-smi is available
if command -v nvidia-smi &> /dev/null; then
    echo "NVIDIA SMI found, checking GPU status:"
    nvidia-smi
else
    echo "ERROR: nvidia-smi not found. Check NVIDIA drivers and runtime."
    exit 1
fi

# Run the Python validation script
echo -e "\nRunning Python CUDA validation..."
if [ -f validate_cuda.py ]; then
    python validate_cuda.py
else
    echo "ERROR: validate_cuda.py not found."
    echo "Make sure you're running this script from the test directory."
    exit 1
fi

echo -e "\n===== Validation complete ====="
