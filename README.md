# EvalForge

**Production-grade LLM evaluation and regression detection platform.**

EvalForge automates golden dataset evaluations, detects hallucinations, tracks latency regressions, compares models, and blocks AI quality regressions through CI/CD quality gates.

---

## Architecture

```
EvalForge/
├── backend/            FastAPI + SQLAlchemy + Celery + asyncpg
│   ├── app/
│   │   ├── api/        REST API routes
│   │   ├── core/       Config, logging, security
│   │   ├── db/         Models + session management
│   │   ├── schemas/    Pydantic DTOs
│   │   ├── services/   Ollama, Gemini, scoring, evaluation, analytics
│   │   └── workers/    Celery tasks
│   └── alembic/        Database migrations
├── frontend/           React + TypeScript + Vite + Recharts
│   └── src/
│       ├── pages/      Overview, EvalRuns, RunDetail, Datasets, Analytics, ModelComparison
│       ├── components/ Reusable UI components
│       ├── api/        Axios client + all API calls
│       └── hooks/      usePolling
├── nginx/              Reverse proxy config
├── .github/workflows/  CI + Quality Gate
└── scripts/            Deployment + seeding utilities
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.0 async, asyncpg |
| Queue | Celery + Redis |
| Database | PostgreSQL 16 |
| AI Inference | Ollama (local) + Gemini API (judge) |
| Frontend | React 18, TypeScript, Vite, TailwindCSS, Recharts |
| Infra | Docker, Docker Compose, Nginx |
| CI/CD | GitHub Actions |

## Supported Models (Ollama)

- `phi4` (default)
- `llama3.2`
- `qwen2.5`
- `gemma3`

## Scoring Engine

Each model response is scored using:

1. **Cosine similarity** (TF-IDF) — compares semantic overlap with golden answer
2. **Keyword coverage** — checks presence of expected keywords in response
3. **Gemini LLM-as-judge** (optional) — uses Gemini Flash to judge response quality

**Hallucination detection:** low similarity + low keyword coverage = flagged as hallucination

## Quick Start (Local)

```bash
# 1. Clone
git clone https://github.com/vix-codes/EvalForge.git
cd EvalForge

# 2. Configure environment
cp .env.example .env
# Edit .env with your values

# 3. Install Ollama and pull a model
curl -fsSL https://ollama.ai/install.sh | sh
ollama pull phi4

# 4. Start services
docker compose up -d

# 5. Run migrations
docker compose exec api alembic upgrade head

# 6. Seed sample data
python scripts/seed_sample_data.py http://localhost:8000

# 7. Open dashboard
open http://localhost:3090
```

## API Reference

### Core Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/health` | Health check |
| GET | `/api/v1/suites` | List eval suites |
| POST | `/api/v1/suites` | Create eval suite |
| GET | `/api/v1/suites/{id}/questions` | List golden questions |
| POST | `/api/v1/suites/{id}/questions/bulk` | Bulk import questions |
| POST | `/api/v1/evals` | Trigger evaluation run |
| GET | `/api/v1/evals` | List evaluation runs |
| GET | `/api/v1/evals/{id}` | Get run details |
| GET | `/api/v1/evals/{id}/results` | Get run results |
| GET | `/api/v1/analytics/summary` | Platform summary |
| GET | `/api/v1/analytics/models` | Model comparison |
| GET | `/api/v1/analytics/trends` | Hallucination/latency trends |
| POST | `/api/v1/webhooks/github` | GitHub push webhook |
| GET | `/api/v1/models` | List Ollama models |

Interactive docs: `http://localhost:8000/api/docs`

## CI/CD Quality Gates

Configure GitHub repository secrets:

```
EVALFORGE_API_URL      https://evalforge.your-domain.com
EVALFORGE_SUITE_ID     <uuid of your active suite>
EVALFORGE_MODEL        phi4
MAX_HALLUCINATION_RATE 0.15
MIN_PASS_RATE          0.80
MAX_P95_LATENCY_MS     10000
```

Set repository variable `EVALFORGE_ENABLED=true` to activate gate.

The quality gate blocks merges if:
- Hallucination rate > 15%
- P95 latency > 10,000ms
- Pass rate < 80%

## Deployment

### VPS Deployment (143.198.160.235)

```bash
# 1. Initial VPS setup (run once)
ssh root@143.198.160.235 bash < scripts/setup_vps.sh

# 2. Deploy
./scripts/deploy.sh 143.198.160.235

# 3. Configure SSL
certbot --nginx -d evalforge.your-domain.com
```

Ports used by EvalForge (avoiding conflicts):
- `8765` — API (internal, proxied by Nginx)
- `3090` — Frontend (internal, proxied by Nginx)
- `5434` — PostgreSQL (internal only)
- `6381` — Redis (internal only)

### Frontend (Vercel)

```bash
cd frontend
vercel deploy --prod
```

Set environment variable in Vercel:
```
VITE_API_URL=https://evalforge.your-domain.com/api/v1
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | required | 32+ char secret key |
| `DATABASE_URL` | postgresql+asyncpg://... | PostgreSQL connection |
| `REDIS_URL` | redis://localhost:6379/0 | Redis connection |
| `OLLAMA_BASE_URL` | http://localhost:11434 | Ollama API |
| `GEMINI_API_KEY` | — | Gemini API key (optional) |
| `GEMINI_JUDGE_ENABLED` | false | Enable LLM-as-judge scoring |
| `GITHUB_WEBHOOK_SECRET` | — | Webhook HMAC secret |
| `MAX_HALLUCINATION_RATE` | 0.15 | Quality gate threshold |
| `MIN_PASS_RATE` | 0.80 | Quality gate threshold |
| `MAX_P95_LATENCY_MS` | 10000.0 | Quality gate threshold |

## License

MIT
