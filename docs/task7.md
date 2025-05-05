## ✅ Planned Task: Database Integration and Auth Flow Fix

### 🧩 Task Overview

Migrate the authentication system from in-memory/session storage to **relational database persistence** using **SQLAlchemy** and **Alembic**, as recommended in `refactoring-guidelines.md` under:

* `Security Enhancements > Future Enhancements for Authentication System`
* `Database Integration > Metadata Storage`

Ensure tokens persist between requests and user sessions, and that the auth flow redirects appropriately in the React app.

---

### 🛠️ Backend Tasks (FastAPI)

#### 1. Add SQLAlchemy-based User Persistence

* Create a `User` SQLAlchemy model with fields:
  `id`, `email`, `hashed_password`, `created_at`, `roles (optional)`
* Add Alembic migrations for user schema.
* Use SQLite by default (via file inside backend container volume).
* Add config option to switch to MySQL (optional).

#### 2. Update AuthService to Use Database

* On `/register`:

  * Hash password and store new user in DB.
  * Generate access and refresh tokens.
* On `/login`:

  * Validate credentials using DB lookup and hashed password comparison.
  * Return tokens if valid.
* On `/me`:

  * Decode token and return authenticated user from DB.

#### 3. Token Middleware

* Use `OAuth2PasswordBearer` with a `get_current_user()` dependency.
* Add automatic 401 response on expired/invalid token.
* Enable refresh token rotation if expired.

#### 4. Docker + Database

* Mount SQLite file to persistent backend volume (or configure MySQL).
* If MySQL:

  * Add `mysql` container in `docker-compose.yml` with env vars.
  * Use connection pooling and retry logic.

---

### 💻 Frontend Tasks (React)

#### 1. Token Storage and Redirection

* On successful login or registration:

  * Save access and refresh tokens in `localStorage`.
  * Redirect user to `/dashboard`.
* Implement Axios interceptor:

  * Attach `Authorization: Bearer <token>` to all requests.
  * On 401, try to refresh token and retry original request.
  * On refresh failure, redirect to `/login`.

#### 2. Auth Context Improvements

* Ensure `AuthContext` properly reflects user status (`loggedIn`, `loading`, `token`).
* On reload, rehydrate from localStorage and validate `/api/auth/me`.

---

### 🧪 Testing

* Add unit tests for:

  * Token generation and validation
  * Password hashing
  * Auth endpoints using test DB
* Add integration tests for login and protected route access.

---

### 📂 Files to Modify or Create

* `backend/models/user.py`
* `backend/services/auth_service.py`
* `backend/routes/auth.py`
* `backend/db/session.py`
* `frontend/context/AuthContext.tsx`
* `frontend/api/axios.ts`
* `docker-compose.yml`
* `.env` (DB settings, secret keys)

