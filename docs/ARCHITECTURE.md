# MBP E-Commerce System Architecture

## 1. High-Level System Topology
This project uses a decoupled architecture running inside Docker containers. The frontend React single-page application (SPA) communicates with a Django REST/GraphQL backend over secure local HTTPS.




[ Client Browser ] (HTTPS)
│
├──► [ Docker: react_MBP_frontend ] ──► Vite Dev Server (Port 5173)
│                                              │
│ (REST API / GraphQL Requests)                │
▼                                              ▼
[ Docker: django_MBP_backend ] ◄──────────────────────┘
│  Django REST Framework (Port 8000)
│  ├── apps/accounts  ──► Auth, JWT/Session, Profiles, Security
│  ├── apps/products  ──► Product Catalog, Categories, Inventory
│  ├── apps/cart      ──► Shopping Cart Management
│  ├── apps/core      ──► Global Exceptions, Middleware, Throttling
│  └── apps/common    ──► Shared Utilities, Role Choices, Trees(sorting backend responce to parent child relation)
│
├──► [ Docker: redis_MBP_cache ] ──► Redis 7 (Port 6379)
│      │
│      └──► [ Docker: celery_MBP_worker ] ──► Async Tasks (Emails, Processing)
│             │
▼             ▼
[ Docker: postgres_MBP_db ] ──► PostgreSQL 18 (Port 5432)



## 2. Docker Container Ecosystem
Our `docker-compose.yml` orchestrates 5 interconnected services using Docker Watch for hot-reloading without container restarts.

| Container Name | Technology | Port | Core Responsibility |
|---|---|---|---|
| `django_MBP_backend` | Python 3.12 / Django | 8000 | Serves REST APIs, GraphQL endpoints, and business logic over HTTPS. |
| `react_MBP_frontend` | Node 20 / Vite + React | 5173 | Serves the interactive user interface and proxies client state. |
| `postgres_MBP_db` | PostgreSQL 16| 5432 | Persistent relational data storage (Users, Orders, Products). |
| `redis_MBP_cache` | Redis 7 Alpine | 6379 | In-memory cache and message broker for Celery task queues. |
| `celery_MBP_worker` | Python 3.12 / Celery | None | Background job execution (email sending, token cleanup, heavy ops). |

## 3. Backend Domain Architecture (`/backend/apps/`)
Instead of a monolithic Django structure, the backend is partitioned into domain-specific apps following separation of concerns:

* **`accounts`**: Manages user authentication, security settings, passwords, and profile management.
* **`products`**: Manages product listings, detail views, category hierarchies, and brand associations.
* **`cart`**: Manages active shopping carts, item additions, removals, and total calculations.
* **`core`**: Contains project-wide infrastructure including custom exception handling (`api/exceptions.py`), API throttling, middleware, and caching logic.
* **`common`**: Houses reusable utilities, tree structures for categories, and shared enums (`role.py`).

## 4. Frontend Architecture (`/frontend/src/`)
The React frontend is structured for scalability and clean API separation:

* **`/api` & `/services`**: Decoupled HTTP clients (`client.js`, `auth.js`) with request/response interceptors and data transformers.
* **`/hooks`**: Custom domain hooks (`useLoginForm`, `useProfileForm`) that encapsulate business logic away from UI components.
* **`/components` & `/pages`**: Modular UI pieces organized by feature (`/account`, `/cart`, `/products`) using Tailwind CSS.
* **`/stores`**: Global state management (`authStore.js`) for persistent client sessions.

## 5. Automated Guardrails (CI/CD)
Managed via GitHub Actions (`.github/workflows/ci.yml`):
* **Backend Pipeline**: Provisions ephemeral Postgres/Redis containers, restores pip cache, executes `pytest`, and validates zero missing migrations (`makemigrations --check`).
* **Frontend Pipeline**: Restores npm cache, executes component unit tests (`npm test`), and verifies production bundling (`npm run build`).