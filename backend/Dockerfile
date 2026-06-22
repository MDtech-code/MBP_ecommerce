# Dockerfile

FROM python:3.12-slim

# Set work directory
WORKDIR /app



# # Install ca-certificates
# RUN apt-get update && apt-get install -y ca-certificates && rm -rf /var/lib/apt/lists/*
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    libssl-dev \
    pkg-config \
    netcat-openbsd \
    ca-certificates \
  && rm -rf /var/lib/apt/lists/*


# Trust mkcert root CA inside container
COPY certs/rootCA.pem /usr/local/share/ca-certificates/mkcert-rootCA.crt
RUN update-ca-certificates

# Install dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ .




CMD ["python", "manage.py", "runserver_plus", "--cert-file", "/app/certs/localhost.pem", "--key-file", "/app/certs/localhost-key.pem", "0.0.0.0:8000"]
