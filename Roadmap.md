## 📍 Project Roadmap: Chat-Analysis Platform

### 🟢 Phase 0: MVP (Completed)

- ✅ Flask-based backend with FAISS and KMeans
- ✅ React frontend with basic file upload and search
- ✅ Initial Docker setup with Dask and RabbitMQ
- ✅ Batch queueing and embedding pipeline
- ✅ Initial model versioning

---

### 🚀 Phase 1: Core Refactor and Productionization (✅ Completed)

#### 🔧 Backend

- ✅ Modularized API into Blueprints
- ✅ Implemented service layer (Embedding, Index, Queue)
- ✅ Switched to Dask-distributed embedding
- ✅ Git-based FAISS index versioning
- ✅ RabbitMQ integration (producer/consumer)

#### 🔐 Auth System

- ✅ JWT auth with refresh rotation
- ✅ OAuth (Google, GitHub)
- ✅ Role-based access control (RBAC)
- ✅ Token persistence in SQLAlchemy (SQLite/MySQL)
- ✅ Alembic migrations + CLI for user/role mgmt

#### 🖥️ Frontend

- ✅ AuthContext + token rotation
- ✅ Login/signup flow with redirect
- ✅ Protected routes and access control
- ✅ Search UI with semantic/hybrid toggle
- ✅ Dashboard visualizations (Recharts)

#### 🐳 Infrastructure

- ✅ Docker Compose dev/prod split
- ✅ MariaDB replacement for MySQL
- ✅ Port exposure minimized (nginx: 881 only)
- ✅ `.drone.yml` builds backend/frontend/nginx

#### 🔬 CI/CD & GPU

- ✅ DroneCI setup for Docker builds
- ✅ Added CUDA support in both CI and production
- ✅ Custom CUDA-enabled test image
- ✅ Backend validated with `nvidia-smi` and Torch

---

### ⚙️ Phase 2: Stability, Scaling & Dev Tooling (In Progress)

#### 📦 Database & Auth Enhancements

- [ ] Add session tracking, audit logs, and MFA UI
- [ ] Extend user profiles and metadata management
- [ ] Batch refresh-token cleanup logic

#### 📈 Monitoring & Observability

- [ ] Add Prometheus & Grafana for backend + workers
- [ ] Implement structured JSON logging with correlation IDs
- [ ] Integrate Sentry for frontend + backend errors

#### 🧪 Testing

- [ ] React Testing Library + component snapshots
- [ ] End-to-end (Cypress) auth + file upload flow
- [ ] Enable `test-backend` in `.drone.yml`
- [ ] GPU test coverage: sentence-transformers + search

#### 🛠 Dev Experience

- [ ] Create `developer-guide.md` for CLI, auth, env setup
- [ ] Add `pre-commit` with Black, Flake8, isort
- [ ] Add Swagger/OpenAPI docs with auth/token examples
- [ ] Generate type-safe API client for frontend

---

### 🧠 Phase 3: Advanced Features (Planned)

#### 🔍 Search

- [ ] Federated search across FAISS index versions
- [ ] Search analytics (queries, trends)
- [ ] Clustering visualization with t-SNE/UMAP

#### 🧑‍🤝‍🧑 User Experience

- [ ] Multi-user org/tenant support
- [ ] Admin panel for managing users/roles/providers
- [ ] MFA enrollment & recovery flow

#### 🧰 AI Features

- [ ] Add OpenAI-compatible embedding API
- [ ] Enable dynamic model loading with registry
- [ ] Add model metadata exposure API

#### 🧩 Infrastructure

- [ ] Kubernetes-ready manifests (Helm or Kustomize)
- [ ] Horizontal scaling of Dask workers
- [ ] PostgreSQL migration support (optional)

---

## 🔚 Final Deliverables

- Fully modular and scalable AI-powered search platform
- Secure user auth system with MFA and OAuth
- GPU-enabled vector pipeline (FAISS + Dask)
- CI/CD + monitoring for continuous delivery
- Clear developer onboarding and operational docs
