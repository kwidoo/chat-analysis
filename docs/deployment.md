* Use of **custom internal Docker networks** (`analysis-net`)
* Controlled access to **admin panels (RabbitMQ, Dask)** via **Nginx reverse proxy using specific `location` blocks**

---

## ✅ Task: Deploy Flask + React App Locally Using Docker Compose

### 🎯 Goal

Fully deploy a Flask + React app stack using the provided `docker-compose.yml`. Ensure:

1. All services run correctly in their own **internal network** (`analysis-net`).
2. Admin panels (RabbitMQ, Dask Dashboard) are accessible **only** through `nginx` at known paths (e.g. `/admin/rabbitmq`, `/admin/dask`).
3. Demo users or seed data are created where required.

---

### 📁 Pre-requisites

* Docker + Docker Compose installed
* Ports `5000`, `881`, `5672`, `15672`, `8786`, `8787` not blocked
* Local DNS for Nginx proxy set up if needed (or just use `localhost`)

---

### ⚙️ Deployment Steps

#### 1. 🧭 you are in root folder of app
```

---

#### 2. 📄 Setup `.env` (optional)

No `.env` is required unless you override secrets. Environment variables are currently declared inline in `docker-compose.yml`.

---

#### 3. 🐳 Run the Full Stack

```bash
docker-compose up --build
```

Services:

* **React Frontend**: [http://localhost:881](http://localhost:881)
* **Flask App** (internal): accessed by frontend and `app` service only
* **RabbitMQ**: via nginx at `/admin/rabbitmq`
* **Dask Dashboard**: via nginx at `/admin/dask`

---

#### 4. 🧑‍💻 Seed Demo User

If your app requires a demo user, add this script:

📄 `backend/seed_demo.py`

```python
from app import db
from models import User  # Adjust import

def seed():
    if not User.query.filter_by(email="demo@example.com").first():
        user = User(email="demo@example.com", password="demo123")  # use hashed!
        db.session.add(user)
        db.session.commit()
        print("Demo user created.")
    else:
        print("Demo user already exists.")

if __name__ == "__main__":
    seed()
```

Run it after containers are up:

```bash
docker-compose exec app python seed_demo.py
```

---

### 🌐 Admin Panel Access via Nginx

Ensure your **nginx config** exposes internal services via prefixed paths like:

📄 `nginx/default.conf` (example)

```nginx
server {
    listen 80;

    location / {
        proxy_pass http://frontend:3000;
    }

    location /api/ {
        proxy_pass http://app:5000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /admin/rabbitmq/ {
        proxy_pass http://rabbitmq:15672/;
        proxy_set_header Host $host;
    }

    location /admin/dask/ {
        proxy_pass http://dask-scheduler:8787/;
        proxy_set_header Host $host;
    }
}
```

🧠 **Note**: Nginx must be in the same `analysis-net` and its service must be added to `docker-compose.yml`:

```yaml
  nginx:
    image: nginx:latest
    volumes:
      - ./nginx:/etc/nginx/conf.d
    ports:
      - "80:80"
    depends_on:
      - frontend
      - app
      - rabbitmq
      - dask-scheduler
    networks:
      - analysis-net
    container_name: nginx-chat-analysis
```

---

### 🔐 Access Paths Summary

| Service  | Internal Container | Access Path         |
| -------- | ------------------ | ------------------- |
| Frontend | `frontend`         | `http://localhost/` |
| API      | `app`              | `/api/` (proxied)   |
| RabbitMQ | `rabbitmq`         | `/admin/rabbitmq/`  |
| Dask UI  | `dask-scheduler`   | `/admin/dask/`      |

---

### 🧪 Test Login (if seeded)

```
Email:    demo@example.com
Password: demo123
```

---

### 🧹 Stop Everything

```bash
docker-compose down
```

Or with volume cleanup:

```bash
docker-compose down -v
```

---

Would you like me to generate the complete `nginx/default.conf` and updated `docker-compose.yml` snippet with the nginx service included?
