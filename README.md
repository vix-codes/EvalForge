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

## Scoring Engine & RAGAS Metrics

EvalForge supports two distinct evaluation target types:
1. **`raw_llm`**: Benchmarks direct LLM outputs against golden answers without context retrieval.
2. **`rag`**: Ingests document collections (`.md`, `.pdf` in `/docs`), indexes them into a persistent **Chroma** vector store, retrieves top-k contexts, and calculates **RAGAS-style metrics**.

### RAGAS Metrics (for `rag` target)

| Metric | Focus | Scale | Description |
|--------|-------|-------|-------------|
| **Faithfulness** | Groundedness | 0.0 – 1.0 | Measures if answer claims are strictly supported by retrieved context chunks without hallucination. |
| **Answer Relevance** | Directness | 0.0 – 1.0 | Measures if the response directly addresses the prompt without extraneous details. |
| **Context Precision** | Retrieval Quality | 0.0 – 1.0 | Evaluates AP@K ranking of retrieved chunks against golden answer & question. |

### Sample RAG Evaluation Output

```
+-----------------------------------------------------------------------------------+
| Total Questions | Pass Rate | Faithfulness | Answer Relevance | Context Precision |
+-----------------+-----------+--------------+------------------+-------------------+
|       16        |   87.5%   |    0.925     |      0.880       |       0.910       |
+-----------------------------------------------------------------------------------+

Detailed Results:
+------------------------------------+-------------------------+--------------+-----------+-----------+--------+
| Question                           | Model Answer Snippet    | Faithfulness | Relevance | Precision | Status |
+------------------------------------+-------------------------+--------------+-----------+-----------+--------+
| What is EvalForge and what does... | EvalForge is an enterprise|    0.950     |   0.920   |   1.000   |  PASS  |
| What vector store is used for...   | Uses ChromaDB locally.. |    1.000     |   0.950   |   0.833   |  PASS  |
+------------------------------------+-------------------------+--------------+-----------+-----------+--------+
```

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
docker compose up -d postgres redis api worker

# 5. Run migrations
docker compose exec api alembic upgrade head

# 6. Seed sample data
python scripts/seed_sample_data.py http://localhost:8765

# 7. Open dashboard
open http://localhost:3090
```

## Native CLI Auto-Test

The native CLI generates a small golden dataset from a plain-English intent file, creates an EvalForge suite through the REST API, runs a local Ollama model, polls the Celery run, and renders a Rich terminal report.

```bash
# 1. Install CLI dependencies
python -m pip install -r cli/requirements.txt

# 2. Create an intent file
cat > intent.txt <<'EOF'
This GenAI assistant is specialized in backend architecture and database optimization.
It must provide highly accurate code snippets using Node.js, Express, and PostgreSQL.
It needs to handle complex concurrency issues, transaction isolation levels, and row-locking mechanisms.
The tone must be purely technical, avoiding introductory fluff or generic explanations.
It must explicitly call out performance regressions or potential deadlocks in its answers.
EOF

# 3. Run the complete automated evaluation
python cli/main.py auto-test intent.txt --model phi4
```

On Windows, if `python` points to a broken install or the Microsoft Store shim, use the included launcher. It finds a healthy Python installation before installing dependencies or running the CLI:

```bat
scripts\evalforge-cli.cmd -Install
scripts\evalforge-cli.cmd auto-test intent.txt --model phi4
```

If Ollama crashes with a CUDA error while loading `phi4`, restart Ollama in CPU mode before running the eval:

```bat
scripts\start-ollama-cpu.cmd
scripts\evalforge-cli.cmd auto-test intent.txt --model phi4
```

The CLI uses ASCII terminal output by default on Windows CMD to avoid mojibake. Set `EVALFORGE_UNICODE=1` only if your terminal is configured for UTF-8 and you want Unicode Rich borders.

Preflight behavior is intentionally quota-safe: the CLI checks Ollama and the EvalForge API before making the single Gemini dataset-generation call. If `phi4` is missing, the CLI attempts to pull it from Ollama automatically. If the API is not ready, it exits before spending Gemini free-tier quota.

The worker path uses synchronous Ollama HTTP calls behind an async boundary. This avoids reusing `httpx.AsyncClient` instances across Celery prefork event loops while keeping the evaluation service API async-friendly. Local Ollama generations are also clamped with `OLLAMA_MAX_TOKENS`, `OLLAMA_NUM_CTX`, and `OLLAMA_NUM_BATCH` to reduce host memory pressure during code-heavy prompts.

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

Interactive docs: `http://localhost:8765/api/docs` when using Docker Compose.

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
