# 🏍️ MBP_ecommerce  
### Motor Bike Parts E‑Commerce Platform (Pakistan)

MBP_ecommerce is a production‑oriented full‑stack eCommerce platform designed to provide Pakistani users with a centralized marketplace for motorbike parts.

Although initially started as a learning project, it is being developed with a production mindset, focusing on scalability, security, clean architecture, and DevOps best practices.

---

# 🚀 Project Vision

To build a scalable, secure, and production-ready eCommerce system where users can:

- Browse motorbike parts
- Search and filter products
- Purchase parts easily
- Access a reliable platform tailored for the Pakistani market

---

# 🧱 Tech Stack

## 🔹 Backend
- Python 3.14
- Django 6
- Django REST Framework 3.17
- PostgreSQL 18
- Redis 7
- Celery (Async Tasks)
- drf-spectacular (Swagger / OpenAPI)
- Django Debug Toolbar

## 🔹 Frontend
- React 19.2.6
- Node 24.16
- NPM 11.17

## 🔹 DevOps
- Docker
  - python:3.12-slim
  - node:24
  - postgres:16
  - redis:7-alpine
- HTTPS enabled locally and in Docker
- Structured Git workflow

---

# 📂 Project Structure

MBP_ecommerce/
│
├── backend/        # Django + DRF API
├── frontend/       # React application
├── docker/         # Docker configurations
├── .env            # Local environment variables
├── .env.docker     # Docker environment variables
├── .env.example    # Public environment template
└── README.md

---

# ⚙️ Environment Configuration

The project uses:

- `.env` → Local development
- `.env.docker` → Docker environment
- `.env.example` → Public template

Environment variables include:

- SECRET_KEY
- DEBUG
- Database credentials
- Redis configuration
- Celery configuration

⚠️ Database is currently configured directly inside `settings.py`.

---

# 🧪 Local Development Setup

## 1️⃣ Backend (Django)

```bash
cd backend
venv/Scripts/activate        # Windows
# OR
source venv/bin/activate     # Linux / Mac

python manage.py runserver_plus --cert-file D:\MBP_ecommerce\backend\certs\localhost.crt --key-file D:\MBP_ecommerce\backend\certs\localhost-key.pem 0.0.0.0:8000

```

Runs on HTTPS locally.

---

## 2️⃣ Frontend (React)

```bash
cd frontend
npm install
npm run dev
```

Runs on HTTPS.

---

## 3️⃣ Redis (Docker)

```bash
docker run -d \
--name redis7 \
--restart unless-stopped \
-p 6380:6379 \
redis:7
```

---

## 4️⃣ Celery Worker

```bash
python -m celery -A config worker --pool=threads --loglevel=info
```

---

# 🐳 Docker Setup

After local testing is successful:

```bash
docker compose up --build
```

Docker stack includes:

- Django backend
- React frontend
- PostgreSQL
- Redis
- Celery worker

Both frontend and backend run on HTTPS inside Docker.

---

# 📘 API Documentation

Swagger & OpenAPI documentation:

- Swagger UI → /api/docs/
- ReDoc → /api/redoc/
- Schema → /api/schema/

Powered by drf-spectacular.

---

# 🔄 Celery Test Endpoint

Test async task execution:

GET /api/test-celery/

Example response:

```json
{
  "task_id": "123456",
  "status": "queued"
}
```

---

# 🧑‍💻 Git Workflow

Branches used:

- develop → Active development
- main → Stable tested branch
- master → Production-ready branch

Workflow:

1. Develop features in develop
2. Fully test locally
3. Test in Docker
4. Merge into main
5. Promote to master after validation

---

# 🛠️ Current Status

- Project configuration finalized  
- HTTPS enabled (Local & Docker)  
- Celery + Redis configured  
- Swagger configured  
- Git workflow established  

Business features (products, orders, users, payments) coming next.

---

# 🔐 Production Goals

Planned improvements:

- Nginx reverse proxy
- Payment gateway integration (Pakistan)
- Role-based authentication
- Rate limiting
- CI/CD pipeline
- Logging & monitoring
- Caching optimization
- Deployment to cloud infrastructure

---

# 🎯 Long-Term Goals

- Multi-vendor support
- Inventory management
- Order tracking system
- Analytics dashboard
- Mobile-ready frontend
- Cloud deployment (AWS / DigitalOcean)

---

# 👨‍💻 Author

Developed with a production mindset by a passionate backend engineer building scalable real-world systems.

---

# 📜 License

This project is under active development.  
License will be defined before public production release.

---

# 💬 Final Note

This is not just a learning project.

It is being engineered step-by-step as a production-grade eCommerce platform for real-world use in Pakistan.