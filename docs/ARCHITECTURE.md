# MBP E-Commerce System Architecture

## 1. High-Level System Topology
This project utilizes a dual-environment engineering workflow: a **Local Native Environment** optimized for rapid development, debugging, and IDE integration, and a **Containerized Docker Environment** used for environment parity, deployment verification, and CI/CD mirroring.

Both environments power a decoupled architecture where a React single-page application (SPA) communicates with a Django REST/GraphQL backend over local HTTPS.


[ Client Browser ] (HTTPS)
│
├───► Frontend Dev Server (Local: Port 5173 | Docker: Port 5173)
│
└───► Backend API Server  (Local: Port 8000 | Docker: Port 8000)
│
├──► [ Redis Cache & Broker ] (Local: Port 7000 | Docker: Port 6379)
│      │
│      └──► [ Celery Workers ] (Async Tasks & Background Jobs)
│
└──► [ PostgreSQL Database ]  (Local: Port 5432 | Docker: Port 5432)


---

## 2. Local Development Architecture (Primary)
The primary day-to-day development workflow runs natively on the host machine to leverage maximum execution speed, native IDE indexing, and simplified step-through debugging.

| Component | Tech / Version | Host Port | Execution Mode | Notes / Configuration |
|---|---|---|---|---|
| **Frontend** | React 19.2.6 / Vite 8.0.12 | `5173` | Native Node Process | Run via `npm run dev` with local HTTPS certs. |
| **Backend** | Python 3.14.5 / Django | `8000` | Native Python Virtualenv | Run via `python manage.py runserver_plus` over HTTPS. |
| **Database** | PostgreSQL 18 | `5432` | Native OS Service | Host-managed relational database instance. |
| **Cache/Broker** | Redis 7 | `7000` | Isolated Docker Container | Mapped `7000:6379` to prevent host port collisions. |
| **Workers** | Celery / Python 3.14.5 | Internal | Native Terminal Process | Connected to local Redis broker on port 7000. |

---

## 3. Containerized Architecture (Verification & CI Parity)
To prevent "it works on my machine" regressions, the application is mirrored in Docker Compose. This architecture is spun up to verify container builds, test inter-service networking, and replicate the CI/CD pipeline before pushing code.

| Service Name | Container Image / Build | Exposed Port | Internal Role | Key Volume Mounts |
|---|---|---|---|---|
| **`backend`** | Python 3.12 (Dockerfile) | `8000` | REST API & GraphQL Server | `./backend:/app`, `./certs:/app/certs` |
| **`frontend`** | Node.js 20 (Dockerfile) | `5173` | Vite SPA Dev Server | `./frontend:/app`, `frontend_node_modules` |
| **`db`** | PostgreSQL 16 | `5432` | Containerized Database | `postgres_data:/var/lib/postgresql/data` |
| **`redis`** | Redis 7 Alpine | `6379` | In-memory Cache & Broker | Ephemeral container storage |
| **`celery`** | Python 3.12 (Shared) | Internal | Background Job Execution | `./backend:/app`, `./certs:/app/certs` |

> **Architectural Note on Version Parity:** Notice the version splits between Local (Python 3.14 / Postgres 18) and Docker (Python 3.12 / Postgres 16). Documenting this explicitly ensures any version-specific syntax or SQL behavior differences can be traced immediately.

---

## 4. Backend Domain Architecture (`/backend/apps/`)
Instead of a monolithic structure, the backend is partitioned into domain-specific apps following strict separation of concerns:

* **`accounts`**: Manages user authentication, security settings, passwords, and profile management.
* **`products`**: Manages product listings, detail views, category hierarchies, and brand associations.
* **`cart`**: Manages active shopping carts, item additions, removals, and total calculations.
* **`core`**: Contains project-wide infrastructure including custom exception handling (`api/exceptions.py`), API throttling, middleware, and caching logic.
* **`common`**: Houses reusable utilities, tree structures for categories, and shared enums (`role.py`).

---

## 5. Frontend Architecture (`/frontend/src/`)
The React frontend is structured for scalability and clean API separation:

* **`/api` & `/services`**: Decoupled HTTP clients (`client.js`, `auth.js`) with request/response interceptors and data transformers.
* **`/hooks`**: Custom domain hooks (`useLoginForm`, `useProfileForm`) that encapsulate business logic away from UI components.
* **`/components` & `/pages`**: Modular UI pieces organized by feature (`/account`, `/cart`, `/products`) using Tailwind CSS.
* **`/stores`**: Global state management (`authStore.js`) for persistent client sessions.

---

## 6. Automated Guardrails (CI/CD)
Managed via GitHub Actions (`.github/workflows/ci.yml`):
* **Backend Pipeline**: Provisions ephemeral Postgres/Redis containers, restores pip cache, executes `pytest`, and validates zero missing migrations (`makemigrations --check`).
* **Frontend Pipeline**: Restores npm cache, executes component unit tests (`npm test`), and verifies  production bundling (`npm run build`).