# Deployment Architecture

## Overview
The platform is designed to be cloud-agnostic, with a primary focus on containerized deployments using Docker and Kubernetes.

## Environment Separation
| Environment | Purpose | Infrastructure |
| :--- | :--- | :--- |
| **Development** | Local coding | Docker Compose (Local) |
| **Staging** | QA & Integration | AWS EKS (Small) / DigitalOcean |
| **Production** | Actual Users | AWS EKS (Multi-AZ) / Managed RDS |

## Infrastructure Components

### 1. Frontend Hosting
- **Provider**: Vercel or AWS Amplify.
- **Features**: Global CDN, SSR (Server Side Rendering) optimization, Edge Middleware.

### 2. Backend Hosting (API)
- **Deployment**: Kubernetes Pods (Autoscaled).
- **Graceful Shutdown**: Handled via FastAPI lifespan events.

### 3. Database
- **Primary**: AWS RDS PostgreSQL (Multi-AZ).
- **Extension**: `pgvector` must be enabled.

### 4. Vector Search & Cache
- **Redis**: Managed ElastiCache or Redis Cloud for task queuing and caching.

### 5. Storage
- **S3**: IAM-restricted bucket for resume artifacts and optimized PDFs.

## CI/CD Pipeline (GitHub Actions)
1. **Lint & Test**: Run Pytest and ESLint.
2. **Build**: Build Docker images for Backend and Worker.
3. **Push**: Push to Amazon ECR.
4. **Deploy**: Update K8s deployment using `helm` or `kubectl`.

## Monitoring
- **Logs**: CloudWatch or ELK Stack.
- **Traces**: Sentry for error tracking and OpenTelemetry for LLM latency monitoring.
