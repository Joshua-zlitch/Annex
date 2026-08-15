# ANNEX — "Learn Before You Believe"

AI-powered media and information literacy platform. Backend foundation (Phase 1).

Users submit media (images, text) that might be misleading or fabricated. ANNEX
extracts the content (OCR via OpenAI vision), pulls out the claims being made,
and produces a credibility assessment so people can **learn before they believe**.

## Tech stack

| Layer      | Choice                                            |
| ---------- | ------------------------------------------------- |
| API        | FastAPI (Python 3.12)                             |
| Database   | Supabase Postgres (PostgREST)                     |
| Auth       | Supabase Auth (JWT)                               |
| Storage    | Supabase Storage                                  |
| AI / OCR   | OpenAI (gpt-4o vision; no Tesseract)              |
| Async jobs | FastAPI `BackgroundTasks` (no Redis / Celery yet) |
| Deploy     | Docker → Cloud Run                                |
| CI         | GitHub Actions                                    |

## Architecture (Clean Architecture)

```
┌────────────────────────────────────────────────────────────┐
│ interface   FastAPI routes, Pydantic schemas, DI, errors    │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ application   use cases (orchestration, pure async)  │   │
│  │  ┌────────────────────────────────────────────────┐  │   │
│  │  │ domain   entities, exceptions                   │  │   │
│  │  │          ports (ABC interfaces)                 │  │   │
│  │  └────────────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────┘   │
│ infrastructure   Supabase repos/storage/auth, OpenAI, DI    │
└────────────────────────────────────────────────────────────┘
```

Dependency rule: the **core** layer (domain + application) never imports from
FastAPI, Supabase or OpenAI. It depends only on ports (interfaces). The
**infrastructure** layer implements those ports; the **interface** layer wires
everything through a composition root (`app/infrastructure/container.py`).

```
app/
├── core/                     # innermost, framework-free
│   ├── entities/             # Media, Analysis, Claim, Assessment, User
│   ├── exceptions.py         # DomainError hierarchy
│   ├── ports/                # MediaRepository, AnalysisRepository,
│   │                         # AIProvider, StorageProvider, AuthProvider,
│   │                         # BackgroundJobRunner
│   └── use_cases/            # SubmitMedia, AnalyzeMedia, MediaQuery, AnalysisQuery
├── infrastructure/           # adapters
│   ├── config.py             # pydantic-settings
│   ├── container.py          # composition root (DI)
│   ├── ai/                   # OpenAIProvider (vision OCR + analysis)
│   ├── db/                   # Supabase repositories (PostgREST)
│   ├── storage/              # Supabase Storage
│   ├── auth/                 # Supabase Auth (JWT)
│   └── jobs/                 # FastAPIBackgroundRunner
└── interface/                # delivery
    ├── dependencies.py       # get_current_user, get_container
    └── api/                  # v1 routes, schemas, error handlers
supabase/migrations/          # SQL schema (tables + RLS + storage bucket)
tests/                        # unit (use cases w/ fakes) + API (TestClient)
```

## Phase 1 scope

- `POST /api/v1/media/upload` — image upload → Supabase Storage → media + pending analysis.
- `POST /api/v1/media/from-text` — raw text → analysis.
- `GET /api/v1/media`, `GET /api/v1/media/{id}`, `GET /api/v1/analysis/{id}`,
  `GET /api/v1/media/{id}/analysis` — owner-scoped reads.
- `GET /api/v1/health` — liveness probe.
- Analysis runs on FastAPI `BackgroundTasks` (image → OCR → claims → assessment).

Not yet (later phases): video/audio/document/URL ingestion, polling/webhooks for
long-running jobs, a durable queue, multi-model verification.

## Quickstart

```bash
# 1. Environment
cp .env.example .env          # fill in Supabase + OpenAI keys

# 2. Database
supabase db push              # or run supabase/migrations/*.sql in the SQL editor

# 3. Install & run
pip install -e ".[dev]"
uvicorn app.main:app --reload # http://localhost:8000/docs

# or with Docker
docker compose up
```

## Test & lint

```bash
pytest        # unit + API tests (no external services needed)
ruff check .  # lint
ruff format . # format
```

## Deployment (Cloud Run)

The GitHub Actions workflow `.github/workflows/deploy-cloud-run.yml` builds and
deploys on pushes to `main` (also `workflow_dispatch`). Configure these
secrets/vars first:

- Secrets: `GCP_WORKLOAD_IDENTITY_PROVIDER`, `GCP_SERVICE_ACCOUNT`,
  `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `OPENAI_API_KEY`
- Vars: `GAR_LOCATION`, `GCP_PROJECT_ID`, `GCP_REGION`

Secrets are injected from Secret Manager at deploy time (`--update-secrets`).