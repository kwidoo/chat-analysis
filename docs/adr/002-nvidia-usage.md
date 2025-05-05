## 🛠️ NVIDIA GPU (CUDA) Support Implementation

### 🎯 Objective

Enable and configure **CUDA-enabled GPU operations** for both **Drone CI pipeline** and **Docker production deployment**, required by the NLP/AI pipeline.

---

### ⚠️ Problem Summary

- **Tests were disabled** in `.drone.yml` due to GPU access issues.
- **Drone CI couldn't access the A4000 GPU** because CUDA was not exposed correctly.
- **Production Docker deployment failed** to utilize the A4000 GPU properly.
- Host system supports CUDA (`nvidia-smi` and Docker with `nvidia` runtime work correctly).

---

### ✅ Implementation Status

- [x] **CI:** Enabled CUDA GPU support in the `test-backend` step of `.drone.yml`
- [x] **Prod:** Ensured backend container in `docker-compose.prod.yml` uses CUDA correctly
- [x] Built a custom **GPU-enabled test image** via `backend/test/Dockerfile.test`
- [x] Added validation scripts with a minimal CUDA-based inference for `transformers`

---

### 🧠 Architecture Decision

**Decision**: Implemented NVIDIA CUDA support in both CI and production environments.

**Context**:

- Our NLP pipeline requires GPU acceleration for efficient inference and model training
- The A4000 GPU available on our servers provides sufficient compute capacity for our needs
- Previous Docker setup failed to properly expose GPU capabilities to containers
- Tests involving transformer models were skipped/failing due to unavailable CUDA

**Consequences**:

- **Positive**: Faster model inference and training in production
- **Positive**: Complete test coverage including GPU-dependent tests
- **Negative**: Additional configuration complexity
- **Negative**: Potential increases in build times for CI

---

### 🔧 Implementation Details

#### 1. CI: Updated `.drone.yml`

- Uncommented and modified the `test-backend` step:

  ```yaml
  - name: test-backend
    image: nvidia/cuda:12.2.0-cudnn8-runtime-ubuntu22.04
    volumes:
      - name: docker_sock
        path: /var/run/docker.sock
      - name: nvidia_gpu
        path: /usr/local/nvidia
    environment:
      - NVIDIA_VISIBLE_DEVICES=all
      - NVIDIA_DRIVER_CAPABILITIES=compute,utility
    commands:
      - apt-get update && apt-get install -y python3 python3-pip
      - cd backend
      - pip3 install -r requirements.txt
      - pip3 install pytest
      - python3 -c "import torch; print('CUDA available:', torch.cuda.is_available()); print('Device count:', torch.cuda.device_count())"
      - nvidia-smi
      - pytest tests/
  ```

- Added a new volume to the volumes section:
  ```yaml
  volumes:
    - name: nvidia_gpu
      host:
        path: /usr/local/nvidia
  ```

#### 2. Prod: Updated `docker-compose.prod.yml`

- Added NVIDIA runtime settings to backend service:

  ```yaml
  backend:
    # ...existing settings...
    runtime: nvidia
    # ...existing volumes...
    deploy:
      resources:
        limits:
          memory: 4G
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
  ```

- Environment variables were already correctly set:
  ```yaml
  environment:
    - NVIDIA_VISIBLE_DEVICES=all
    - NVIDIA_DRIVER_CAPABILITIES=compute,utility
    # ...other environment variables...
  ```

#### 3. Updated `backend/Dockerfile`

- Changed base image from Python to NVIDIA CUDA:

  ```dockerfile
  FROM nvidia/cuda:12.2.0-cudnn8-runtime-ubuntu22.04
  ```

- Added Python setup for Ubuntu-based image:

  ```dockerfile
  # Install system dependencies
  RUN apt-get update && apt-get install -y \
      python3 \
      python3-pip \
      python3-dev \
      libgomp1 \
      curl \
      git \
      && rm -rf /var/lib/apt/lists/*

  # Use python3 instead of python
  RUN ln -s /usr/bin/python3 /usr/bin/python && \
      ln -s /usr/bin/pip3 /usr/bin/pip
  ```

- Added CUDA validation step:
  ```dockerfile
  # Validate CUDA availability
  RUN python -c "import torch; print('CUDA available:', torch.cuda.is_available()); print('Device count:', torch.cuda.device_count())"
  ```

#### 4. Created Custom GPU Test Files

- Created `backend/test/Dockerfile.test` with dedicated GPU testing setup:

  ```dockerfile
  FROM nvidia/cuda:12.2.0-cudnn8-runtime-ubuntu22.04

  # ...system setup...

  # Install test dependencies
  RUN pip install --no-cache-dir \
      pytest \
      pytest-cov \
      torch==2.2.0+cu121 \
      torchvision==0.17.0+cu121 \
      transformers==4.37.0

  # ...validation steps...
  ```

- Created `backend/test/validate_cuda.py` for thorough CUDA validation:

  - Runs `nvidia-smi`
  - Checks PyTorch CUDA availability
  - Tests simple tensor operations on GPU
  - Loads a small Transformers model to verify end-to-end inference

- Added `backend/test/validate_gpu.sh` shell script for easier validation

---

### 📂 Files Modified

- `.drone.yml` - Updated CI pipeline with CUDA support
- `docker-compose.prod.yml` - Added NVIDIA runtime configuration
- `backend/Dockerfile` - Changed to CUDA-enabled base image

### 📂 Files Created

- `backend/test/Dockerfile.test` - Custom CUDA-enabled test image
- `backend/test/validate_cuda.py` - Python validation script
- `backend/test/validate_gpu.sh` - Shell validation script

---

### 📚 References

- [NVIDIA Container Toolkit Documentation](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/overview.html)
- [Docker GPU Support Documentation](https://docs.docker.com/config/containers/resource_constraints/#gpu)
- [PyTorch CUDA Setup Guide](https://pytorch.org/get-started/locally/)

---

### 📌 Validation Process

To validate the setup:

1. **In CI environment**:

   - The test pipeline now runs `nvidia-smi` and a PyTorch CUDA check
   - Tests using GPU acceleration will no longer be skipped

2. **In production environment**:

   - Run: `docker exec -it backend python -c "import torch; print(torch.cuda.is_available())"`
   - Run: `docker exec -it backend nvidia-smi`

3. **Using the validation script**:
   - Build and run the test container:
   ```bash
   cd backend
   docker build -t gpu-test -f test/Dockerfile.test .
   docker run --gpus all -it --rm gpu-test /app/test/validate_gpu.sh
   ```

### 🚀 Implementation Complete: May 5, 2025
