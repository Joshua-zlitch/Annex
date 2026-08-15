# Deployment Guide

This document describes the complete deployment pipeline for ANNEX.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           CI/CD PIPELINE                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐              │
│  │  Push   │───►│   CI    │───►│  Tag    │───►│   CD    │              │
│  │  Code   │    │ (test,  │    │  v*     │    │ (deploy)│              │
│  │         │    │ lint,   │    │         │    │         │              │
│  │         │    │ build)  │    │         │    │         │              │
│  └─────────┘    └─────────┘    └─────────┘    └─────────┘              │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
            ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
            │ Cloud Run   │ │ Firebase    │ │ Chrome Web  │
            │ (Backend)   │ │ Hosting     │ │ Store       │
            └─────────────┘ └─────────────┘ └─────────────┘
                    │               │               │
                    ▼               ▼               ▼
            ┌─────────────────────────────────────────────┐
            │            Mobile Build Artifacts           │
            │         (iOS IPA / Android AAB)             │
            └─────────────────────────────────────────────┘
```

## Required Secrets

### GitHub Repository Secrets

| Secret | Description | Required For |
|--------|-------------|--------------|
| `GCP_PROJECT_ID` | Google Cloud project ID | Backend deploy |
| `GCP_REGION` | GCP region (e.g., `us-central1`) | Backend deploy |
| `GCP_SA_KEY` | Service account JSON (base64) | Backend deploy |
| `FIREBASE_PROJECT_ID` | Firebase project ID | Web deploy |
| `FIREBASE_SERVICE_ACCOUNT` | Firebase service account JSON | Web deploy |
| `DATABASE_URL` | PostgreSQL connection string | Backend runtime |
| `REDIS_URL` | Redis connection string | Backend runtime |
| `FIREBASE_SERVICE_ACCOUNT_PATH` | Path to Firebase SA in Cloud Run | Backend runtime |
| `OPENAI_API_KEY` | OpenAI API key | Backend runtime |
| `GEMINI_API_KEY` | Google Gemini API key | Backend runtime |
| `SENTRY_DSN` | Sentry DSN | Backend runtime |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | Tempo OTLP endpoint | Backend runtime |
| `CWS_CLIENT_ID` | Chrome Web Store OAuth client ID | Extension deploy |
| `CWS_CLIENT_SECRET` | Chrome Web Store OAuth client secret | Extension deploy |
| `CWS_REFRESH_TOKEN` | Chrome Web Store refresh token | Extension deploy |
| `CWS_EXTENSION_ID` | Chrome Web Store extension ID | Extension deploy |
| `SLACK_WEBHOOK_URL` | Slack webhook for notifications | Release |
| `DISCORD_WEBHOOK_URL` | Discord webhook for notifications | Release |

### Setting Up Secrets

```bash
# GitHub CLI (recommended)
gh secret set GCP_PROJECT_ID --body "my-project-id"
gh secret set GCP_REGION --body "us-central1"
gh secret set GCP_SA_KEY --body "$(cat sa-key.json | base64 -w 0)"
gh secret set FIREBASE_PROJECT_ID --body "annex-prod"
gh secret set FIREBASE_SERVICE_ACCOUNT --body "$(cat firebase-sa.json | base64 -w 0)"

# For runtime secrets (stored in Secret Manager)
gcloud secrets create DATABASE_URL --data-file=-
gcloud secrets create REDIS_URL --data-file=-
gcloud secrets create OPENAI_API_KEY --data-file=-
# ... etc
```

## GCP Setup

### 1. Enable APIs

```bash
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  secretmanager.googleapis.com \
  sqladmin.googleapis.com \
  redis.googleapis.com \
  monitoring.googleapis.com \
  logging.googleapis.com
```

### 2. Create Artifact Registry Repository

```bash
gcloud artifacts repositories create annex \
  --repository-format=docker \
  --location=us-central1 \
  --description="ANNEX Docker images"
```

### 3. Create Cloud SQL Instance

```bash
gcloud sql instances create annex-db \
  --database-version=POSTGRES_16 \
  --tier=db-f1-micro \
  --region=us-central1 \
  --root-password=SECURE_PASSWORD

gcloud sql databases create annex --instance=annex-db
```

### 4. Create Redis Instance

```bash
gcloud redis instances create annex-redis \
  --size=1 \
  --region=us-central1 \
  --redis-version=redis_7_0
```

### 5. Create Secret Manager Secrets

```bash
# Create secrets (values will be set via CI)
gcloud secrets create DATABASE_URL --replication-policy=automatic
gcloud secrets create REDIS_URL --replication-policy=automatic
gcloud secrets create FIREBASE_PROJECT_ID --replication-policy=automatic
gcloud secrets create FIREBASE_SERVICE_ACCOUNT --replication-policy=automatic
gcloud secrets create OPENAI_API_KEY --replication-policy=automatic
gcloud secrets create GEMINI_API_KEY --replication-policy=automatic
gcloud secrets create SENTRY_DSN --replication-policy=automatic
gcloud secrets create OTEL_EXPORTER_OTLP_ENDPOINT --replication-policy=automatic
```

### 6. Grant Cloud Run Access to Secrets

```bash
PROJECT_NUMBER=$(gcloud projects describe $GCP_PROJECT_ID --format='value(projectNumber)')
SERVICE_ACCOUNT="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

for secret in DATABASE_URL REDIS_URL FIREBASE_PROJECT_ID FIREBASE_SERVICE_ACCOUNT OPENAI_API_KEY GEMINI_API_KEY SENTRY_DSN OTEL_EXPORTER_OTLP_ENDPOINT; do
  gcloud secrets add-iam-policy-binding $secret \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/secretmanager.secretAccessor"
done
```

### 7. Create Cloud Run Migration Job

```bash
gcloud run jobs create annex-migration \
  --image=us-central1-docker.pkg.dev/$GCP_PROJECT_ID/annex/backend:latest \
  --region=us-central1 \
  --cpu=1 --memory=512Mi \
  --max-retries=3 \
  --task-timeout=300 \
  --set-env-vars=DATABASE_URL=postgresql://... \
  --set-secrets=DATABASE_URL=DATABASE_URL:latest
```

## Deployment Triggers

### Automatic (Tag Push)
```bash
git tag v1.0.0
git push origin v1.0.0
```

### Manual (Workflow Dispatch)
```bash
gh workflow run cd.yml -f environment=staging
gh workflow run cd.yml -f environment=production
```

## Environments

| Environment | Backend URL | Web URL | Purpose |
|-------------|-------------|---------|---------|
| Staging | `https://annex-backend-staging-*.run.app` | `https://annex-staging.web.app` | Pre-production testing |
| Production | `https://annex-backend-prod-*.run.app` | `https://annex-prod.web.app` | Live users |

## Rollback Procedure

### Backend (Cloud Run)
```bash
# List revisions
gcloud run services describe annex-backend --region=us-central1

# Rollback to specific revision
gcloud run services update-traffic annex-backend \
  --to-revisions=annex-backend-00001-abc=100 \
  --region=us-central1
```

### Web (Firebase)
```bash
# List releases
firebase hosting:releases:list --project=annex-prod

# Rollback
firebase hosting:clone annex-prod:prod annex-prod:staging --project=annex-prod
```

## Monitoring & Alerts

### Health Checks
- Backend: `GET /health/live` (liveness), `GET /health/ready` (readiness)
- Web: Firebase Hosting health checks
- Metrics: Prometheus `/metrics` endpoint

### Grafana Dashboards
- URL: `https://grafana.annex.example.com`
- Pre-configured: Backend latency, error rates, DB connections, queue depth

### Sentry Alerts
- Error rate > 1% for 5min
- New error types
- Performance degradation > 2x baseline

## Troubleshooting

### Build Failures
```bash
# Check build logs
gcloud builds log BUILD_ID --region=us-central1

# Common issues:
# - Docker build timeout: increase timeout in cloudbuild.yaml
# - Memory limit: increase --memory flag
# - Secret access: verify IAM bindings
```

### Deployment Failures
```bash
# Check Cloud Run service logs
gcloud run services logs read annex-backend --region=us-central1 --limit=100

# Check revision status
gcloud run revisions describe REVISION_NAME --region=us-central1
```

### Database Migration Failures
```bash
# Run migration job manually
gcloud run jobs execute annex-migration --region=us-central1 --wait

# Check job logs
gcloud run jobs executions describe EXECUTION_NAME --job=annex-migration --region=us-central1
```

## Cost Optimization

| Resource | Staging | Production | Monthly Estimate |
|----------|---------|------------|------------------|
| Cloud Run (CPU) | 1 vCPU, 1Gi | 2 vCPU, 2Gi | $20-100 |
| Cloud SQL | db-f1-micro | db-custom-2-4096 | $15-150 |
| Redis | 1GB | 2GB | $30-60 |
| Artifact Registry | 10GB | 50GB | $1-5 |
| Secret Manager | 10 secrets | 20 secrets | $0.40 |
| **Total** |  |  | **~$66-315/mo** |

## Security Checklist

- [ ] All secrets in Secret Manager (not in code/env)
- [ ] Cloud Run: `--no-allow-unauthenticated` for internal services
- [ ] VPC connector for private DB/Redis access
- [ ] Binary Authorization for container images
- [ ] CORS origins restricted to known domains
- [ ] Rate limiting enabled on all endpoints
- [ ] CSP headers on web app
- [ ] Sentry DSN rotated periodically
- [ ] Dependency scanning in CI (Trivy, pip-audit)

## Support Contacts

| Component | Contact |
|-----------|---------|
| Backend/Cloud Run | @backend-team |
| Firebase/Web | @frontend-team |
| Mobile/iOS | @mobile-team |
| Extension | @extension-team |
| Infrastructure | @devops-team |