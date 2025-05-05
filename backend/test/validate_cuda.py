#!/usr/bin/env python3
"""
CUDA Validation Script

This script verifies that CUDA and GPU resources are properly configured
and available to the Python environment.
"""
import sys
import subprocess
try:
    # Try to call nvidia-smi
    print("Running nvidia-smi:")
    nvidia_smi = subprocess.run(['nvidia-smi'], stdout=subprocess.PIPE, text=True)
    print(nvidia_smi.stdout)
except Exception as e:
    print(f"Error running nvidia-smi: {e}")

try:
    import torch
    print("\n--- PyTorch CUDA Information ---")
    print(f"PyTorch version: {torch.__version__}")
    print(f"CUDA available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"CUDA version: {torch.version.cuda}")
        print(f"Device count: {torch.cuda.device_count()}")
        print(f"Current device: {torch.cuda.current_device()}")
        print(f"Device name: {torch.cuda.get_device_name(0)}")

        # Test a simple tensor operation on GPU
        print("\nRunning a simple GPU tensor operation...")
        x = torch.rand(5, 3).cuda()
        y = torch.rand(5, 3).cuda()
        z = x + y
        print(f"Operation successful. Result tensor device: {z.device}")
    else:
        print("CUDA is not available. Check your PyTorch installation and NVIDIA drivers.")
        sys.exit(1)
except ImportError:
    print("PyTorch not installed. Install it with 'pip install torch'.")
    sys.exit(1)

try:
    from transformers import AutoModel
    print("\n--- Hugging Face Transformers Test ---")
    print("Loading a small model to test GPU capability...")
    model = AutoModel.from_pretrained("distilbert-base-uncased")

    # Move model to GPU
    if torch.cuda.is_available():
        model = model.to("cuda")
        print(f"Model successfully moved to {next(model.parameters()).device}")

        # Run a simple forward pass
        inputs = torch.randint(0, 1000, (1, 10)).to("cuda")
        outputs = model(inputs)
        print("Model forward pass successful on GPU")
    else:
        print("CUDA not available for transformers model")
except ImportError:
    print("Transformers not installed. Install it with 'pip install transformers'.")

print("\nValidation complete.")
