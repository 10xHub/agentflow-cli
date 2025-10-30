# Deployment Guide

This guide covers deploying your AgentFlow application to production using various deployment strategies.

## Table of Contents

- [Quick Start](#quick-start)
- [Docker Deployment](#docker-deployment)
- [Docker Compose](#docker-compose)
- [Kubernetes](#kubernetes)
- [Cloud Platforms](#cloud-platforms)
- [Production Checklist](#production-checklist)
- [Monitoring & Logging](#monitoring--logging)
- [Scaling](#scaling)

---

## Quick Start

The fastest way to deploy your AgentFlow application:

```bash
# 1. Generate Docker files
agentflow build --docker-compose --force

# 2. Build and run
docker compose up --build -d

# 3. Verify deployment
curl http://localhost:8000/ping
```

---

## Docker Deployment

### Step 1: Generate Dockerfile

```bash
agentflow build --python-version 3.13 --port 8000
```

This generates an optimized production Dockerfile with:
- ✅ Python 3.13 slim base image
- ✅ Non-root user for security
- ✅ Health checks
- ✅ Gunicorn + Uvicorn workers
- ✅ Multi-layer caching

### Step 2: Build Docker Image

```bash
# Basic build
docker build -t agentflow-api:latest .

# Build with custom tag
docker build -t mycompany/agentflow-api:v1.0.0 .

# Build with build args
docker build \
  --build-arg PYTHON_VERSION=3.13 \
  -t agentflow-api:latest \
  .
```

### Step 3: Run Container

**Basic run:**
```bash
docker run -p 8000:8000 agentflow-api:latest
```

**With environment file:**
```bash
docker run -p 8000:8000 --env-file .env agentflow-api:latest
```

**With environment variables:**
```bash
docker run -p 8000:8000 \
  -e GEMINI_API_KEY=your_key \
  -e LOG_LEVEL=INFO \
  agentflow-api:latest
```

**Detached mode with restart policy:**
```bash
docker run -d \
  --name agentflow-api \
  --restart unless-stopped \
  -p 8000:8000 \
  --env-file .env \
  agentflow-api:latest
```

### Step 4: Verify Deployment

```bash
# Check container status
docker ps

# Check logs
docker logs agentflow-api

# Follow logs
docker logs -f agentflow-api

# Health check
curl http://localhost:8000/ping
```

### Docker Best Practices

1. **Use specific Python versions** instead of `latest`:
   ```bash
   agentflow build --python-version 3.13
   ```

2. **Tag images with versions**:
   ```bash
   docker build -t myapp:v1.0.0 .
   docker build -t myapp:latest .
   ```

3. **Use multi-stage builds** for smaller images (already done in generated Dockerfile)

4. **Scan images for vulnerabilities**:
   ```bash
   docker scan agentflow-api:latest
   ```

5. **Use Docker secrets for sensitive data**:
   ```bash
   echo "my-secret" | docker secret create api_key -
   ```

---

## Docker Compose

### Generate docker-compose.yml

```bash
agentflow build --docker-compose --service-name my-agent-api
```

### Basic docker-compose.yml

```yaml
services:
  agentflow-cli:
    build: .
    image: agentflow-cli:latest
    environment:
      - PYTHONUNBUFFERED=1
      - PYTHONDONTWRITEBYTECODE=1
    ports:
      - '8000:8000'
    command: ['gunicorn', '-k', 'uvicorn.workers.UvicornWorker', '-b', '0.0.0.0:8000', 'agentflow_cli.src.app.main:app']
    restart: unless-stopped
```

### Production docker-compose.yml

```yaml
version: '3.8'

services:
  api:
    build:
      context: .
      dockerfile: Dockerfile
    image: agentflow-api:latest
    container_name: agentflow-api
    restart: unless-stopped
    ports:
      - "8000:8000"
    env_file:
      - .env
    environment:
      - ENVIRONMENT=production
      - LOG_LEVEL=INFO
      - WORKERS=4
    volumes:
      - ./logs:/app/logs
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/ping"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    networks:
      - agentflow-network
    depends_on:
      redis:
        condition: service_healthy
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          cpus: '1.0'
          memory: 1G

  redis:
    image: redis:7-alpine
    container_name: agentflow-redis
    restart: unless-stopped
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - agentflow-network

  nginx:
    image: nginx:alpine
    container_name: agentflow-nginx
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - api
    networks:
      - agentflow-network

volumes:
  redis-data:

networks:
  agentflow-network:
    driver: bridge
```

### Commands

```bash
# Start services
docker compose up -d

# Build and start
docker compose up --build -d

# View logs
docker compose logs -f

# View specific service logs
docker compose logs -f api

# Stop services
docker compose down

# Stop and remove volumes
docker compose down -v

# Restart a service
docker compose restart api

# Scale service
docker compose up -d --scale api=3
```

### Environment Variables

Create a `.env` file in your project root:

```bash
# Application
ENVIRONMENT=production
LOG_LEVEL=INFO
DEBUG=false

# API Keys
GEMINI_API_KEY=your_gemini_api_key
OPENAI_API_KEY=your_openai_api_key

# JWT Authentication
JWT_SECRET_KEY=your-super-secret-key-change-this
JWT_ALGORITHM=HS256

# Redis
REDIS_URL=redis://redis:6379

# Sentry (optional)
SENTRY_DSN=your_sentry_dsn

# Snowflake ID Generator
SNOWFLAKE_EPOCH=1609459200000
SNOWFLAKE_NODE_ID=1
SNOWFLAKE_WORKER_ID=1
```

---

## Kubernetes

### Basic Deployment

**deployment.yaml:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: agentflow-api
  labels:
    app: agentflow-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: agentflow-api
  template:
    metadata:
      labels:
        app: agentflow-api
    spec:
      containers:
      - name: api
        image: myregistry/agentflow-api:latest
        imagePullPolicy: Always
        ports:
        - containerPort: 8000
          name: http
        env:
        - name: ENVIRONMENT
          value: "production"
        - name: LOG_LEVEL
          value: "INFO"
        - name: GEMINI_API_KEY
          valueFrom:
            secretKeyRef:
              name: api-secrets
              key: gemini-api-key
        - name: JWT_SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: api-secrets
              key: jwt-secret
        - name: REDIS_URL
          value: "redis://redis-service:6379"
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "2000m"
        livenessProbe:
          httpGet:
            path: /ping
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /ping
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 3
```

**service.yaml:**
```yaml
apiVersion: v1
kind: Service
metadata:
  name: agentflow-api-service
spec:
  selector:
    app: agentflow-api
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: LoadBalancer
```

**secrets.yaml:**
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: api-secrets
type: Opaque
stringData:
  gemini-api-key: "your_gemini_api_key"
  jwt-secret: "your-jwt-secret-key"
```

**configmap.yaml:**
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: agentflow-config
data:
  agentflow.json: |
    {
      "agent": "graph.react:app",
      "env": ".env",
      "auth": "jwt",
      "redis": "redis://redis-service:6379"
    }
```

### Deploy to Kubernetes

```bash
# Create secrets (from .env file or manually)
kubectl create secret generic api-secrets \
  --from-literal=gemini-api-key=your_key \
  --from-literal=jwt-secret=your_jwt_secret

# Apply configurations
kubectl apply -f configmap.yaml
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml

# Check status
kubectl get pods
kubectl get services
kubectl get deployments

# View logs
kubectl logs -f deployment/agentflow-api

# Scale deployment
kubectl scale deployment agentflow-api --replicas=5

# Update image
kubectl set image deployment/agentflow-api api=myregistry/agentflow-api:v2.0.0

# Rollback
kubectl rollout undo deployment/agentflow-api
```

### Ingress

**ingress.yaml:**
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: agentflow-ingress
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - api.example.com
    secretName: agentflow-tls
  rules:
  - host: api.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: agentflow-api-service
            port:
              number: 80
```

---

## Cloud Platforms

### AWS ECS

**task-definition.json:**
```json
{
  "family": "agentflow-api",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "containerDefinitions": [
    {
      "name": "api",
      "image": "your-ecr-repo/agentflow-api:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "ENVIRONMENT",
          "value": "production"
        }
      ],
      "secrets": [
        {
          "name": "GEMINI_API_KEY",
          "valueFrom": "arn:aws:secretsmanager:region:account:secret:gemini-key"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/agentflow-api",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8000/ping || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 60
      }
    }
  ]
}
```

### Google Cloud Run

```bash
# Build and push to GCR
docker build -t gcr.io/your-project/agentflow-api:latest .
docker push gcr.io/your-project/agentflow-api:latest

# Deploy to Cloud Run
gcloud run deploy agentflow-api \
  --image gcr.io/your-project/agentflow-api:latest \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars ENVIRONMENT=production \
  --set-secrets GEMINI_API_KEY=gemini-key:latest \
  --memory 2Gi \
  --cpu 2 \
  --min-instances 1 \
  --max-instances 10
```

### Azure Container Instances

```bash
# Create resource group
az group create --name agentflow-rg --location eastus

# Create container
az container create \
  --resource-group agentflow-rg \
  --name agentflow-api \
  --image myregistry.azurecr.io/agentflow-api:latest \
  --cpu 2 \
  --memory 4 \
  --ports 8000 \
  --environment-variables \
    ENVIRONMENT=production \
    LOG_LEVEL=INFO \
  --secure-environment-variables \
    GEMINI_API_KEY=your_key \
  --dns-name-label agentflow-api
```

### Heroku

```bash
# Login to Heroku
heroku login

# Create app
heroku create agentflow-api

# Set environment variables
heroku config:set GEMINI_API_KEY=your_key
heroku config:set JWT_SECRET_KEY=your_secret

# Deploy
git push heroku main

# Scale
heroku ps:scale web=2

# View logs
heroku logs --tail
```

---

## Production Checklist

### Before Deployment

- [ ] **Environment Variables**: All required env vars set
- [ ] **Secrets Management**: API keys stored securely
- [ ] **Database**: Migrations run and tested
- [ ] **Dependencies**: All packages pinned in requirements.txt
- [ ] **Config Files**: Production config reviewed
- [ ] **Tests**: All tests passing
- [ ] **Security Scan**: Docker image scanned for vulnerabilities
- [ ] **Performance**: Load tested
- [ ] **Logging**: Log levels configured correctly
- [ ] **Monitoring**: Health checks and metrics configured

### Security

```bash
# 1. Use secrets management
# AWS Secrets Manager, Google Secret Manager, Azure Key Vault

# 2. Never commit secrets
echo ".env" >> .gitignore
echo "secrets.yaml" >> .gitignore

# 3. Use SSL/TLS
# Configure HTTPS with Let's Encrypt or cloud provider certs

# 4. Enable CORS properly
# Review ALLOWED_HOST and ORIGINS in settings

# 5. Run as non-root user
# Already configured in generated Dockerfile

# 6. Keep dependencies updated
pip install --upgrade 10xscale-agentflow-cli

# 7. Enable rate limiting
# Use nginx, Traefik, or API Gateway
```

### Performance

```bash
# 1. Use multiple workers
# Configured in Dockerfile with Gunicorn

# 2. Enable caching
# Configure Redis for session/response caching

# 3. Use CDN for static assets
# CloudFront, Cloudflare, etc.

# 4. Database connection pooling
# Configure in database settings

# 5. Optimize Docker image
# Multi-stage builds (already in generated Dockerfile)
```

---

## Monitoring & Logging

### Application Logs

**With Docker:**
```bash
# View logs
docker logs agentflow-api

# Follow logs
docker logs -f agentflow-api

# Last 100 lines
docker logs --tail 100 agentflow-api

# Since timestamp
docker logs --since 2024-01-01T00:00:00 agentflow-api
```

**With Docker Compose:**
```bash
docker compose logs -f api
```

**With Kubernetes:**
```bash
kubectl logs -f deployment/agentflow-api
kubectl logs -f -l app=agentflow-api
```

### Sentry Integration

Add Sentry to your project:

```bash
pip install "10xscale-agentflow-cli[sentry]"
```

Configure in `.env`:
```bash
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id
```

Update `agentflow.json`:
```json
{
  "agent": "graph.react:app",
  "sentry": {
    "dsn": "${SENTRY_DSN}",
    "environment": "production",
    "traces_sample_rate": 0.1
  }
}
```

### Health Checks

The generated Dockerfile includes a health check:

```dockerfile
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/ping || exit 1
```

Test health check:
```bash
curl http://localhost:8000/ping
# Expected: {"status": "ok"}
```

### Metrics

Integrate with Prometheus:

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'agentflow-api'
    static_configs:
      - targets: ['agentflow-api:8000']
    metrics_path: '/metrics'
```

---

## Scaling

### Horizontal Scaling

**Docker Compose:**
```bash
docker compose up -d --scale api=5
```

**Kubernetes:**
```bash
# Manual scaling
kubectl scale deployment agentflow-api --replicas=5

# Auto-scaling
kubectl autoscale deployment agentflow-api \
  --min=2 --max=10 --cpu-percent=80
```

### Load Balancing

**Nginx:**
```nginx
upstream agentflow_backend {
    least_conn;
    server api1:8000;
    server api2:8000;
    server api3:8000;
}

server {
    listen 80;
    server_name api.example.com;

    location / {
        proxy_pass http://agentflow_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Database Scaling

For PostgreSQL with connection pooling:

```python
# settings.py
DATABASE_URL = "postgresql://user:pass@host:5432/db"
DATABASE_POOL_SIZE = 20
DATABASE_MAX_OVERFLOW = 10
```

---

## Troubleshooting

### Container won't start

```bash
# Check logs
docker logs agentflow-api

# Check if port is available
lsof -i :8000

# Inspect container
docker inspect agentflow-api

# Run interactively for debugging
docker run -it --entrypoint /bin/sh agentflow-api:latest
```

### High memory usage

```bash
# Check container stats
docker stats agentflow-api

# Set memory limits
docker run -m 2g agentflow-api:latest

# In docker-compose.yml
deploy:
  resources:
    limits:
      memory: 2G
```

### Connection refused

```bash
# Check if service is running
docker ps

# Check port mapping
docker port agentflow-api

# Test from inside container
docker exec agentflow-api curl http://localhost:8000/ping
```

---

## Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [AWS ECS Documentation](https://docs.aws.amazon.com/ecs/)
- [Google Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Configuration Guide](./configuration.md)
- [Authentication Guide](./authentication.md)
