#choose stable image 
FROM node:24

#define working directory
WORKDIR /app


# Install ca-certificates tool
RUN apt-get update && apt-get install -y ca-certificates && rm -rf /var/lib/apt/lists/*

# Trust mkcert root CA
COPY ../certs/rootCA.pem /usr/local/share/ca-certificates/mkcert-rootCA.crt
RUN update-ca-certificates

COPY frontend/package*.json ./

RUN npm install -g npm@latest

RUN npm install 


COPY frontend/ .
EXPOSE 5173

CMD ["npm","run","dev","--","--host","0.0.0.0"]
