## 🔧 Task: Docker Compose Refactor for Secure and Scalable Deployment

### 🎯 Goal

Refactor all `docker-compose` configurations to:

* Replace **MySQL** with **MariaDB**
* Eliminate **unnecessary published ports** for internal services
* Restrict **port mapping** on **nginx** to `881:80` in `docker-compose.yml` only
* Ensure all services communicate via the internal **`analysis-net`**
* Apply production-safe and minimal surface exposure settings

---

### 🛠️ Subtasks

#### 1. Replace MySQL with MariaDB

* Change database image to:

  ```yaml
  image: mariadb:10.6
  ```
* Update both `docker-compose.yml` and `docker-compose.prod.yml`
* Test compatibility with SQLAlchemy/Alembic

#### 2. Remove Published Ports from Internal Services

* **Remove `ports:` entries** from:

  * `backend`
  * `db`
  * `rabbitmq` (unless management UI is needed)
* Exception:

  * `dask-scheduler`: Keep `8787` if dashboard access is externally needed

#### 3. NGINX Port Mapping Rule

* In `docker-compose.yml`:

  ```yaml
  ports:
    - "881:80"
  ```
* In `docker-compose.prod.yml`:
  ❌ **Do not expose any ports at all for nginx**
  Nginx must only attach to internal `analysis-net` and `nginx_proxy`.

#### 4. Verify Internal Networking

* Ensure every service declares:

  ```yaml
  networks:
    - analysis-net
  ```

#### 5. Update `.env.example`

* Add:

  ```env
  # Database image used in Docker Compose (mariadb preferred)
  DB_IMAGE=mariadb:10.6
  ```

#### 6. Update CI/CD Configuration

* In `.drone.yml`, ensure production builds use `mariadb`
* No extra ports should be exposed unless explicitly required

---

### ✅ Acceptance Criteria

* `docker-compose.yml` and `docker-compose.prod.yml` both use `mariadb:10.6`
* All internal services avoid exposing ports externally
* `nginx`:

  * **Maps port `881:80` only in `docker-compose.yml`**
  * **Has no ports exposed in `docker-compose.prod.yml`**
* All services use `analysis-net`
* `.env.example` contains the correct `DB_IMAGE`
* System passes integration boot tests in dev and prod modes
