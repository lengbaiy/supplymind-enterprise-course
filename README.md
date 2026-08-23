# SupplyMind

SupplyMind is a multi-tenant, read-only AI data analysis console for manufacturing supply chains. It is an original teaching implementation inspired by the architecture of DB-GPT, not a fork or redistribution of DB-GPT.

## Quick start

```powershell
Copy-Item .env.example .env
docker compose up --build
```

Open `http://localhost:5173`. The seeded organization is `demo-factory`; sign in with `admin@demo.local` and password `ChangeMe123!`.

For real AI analysis and knowledge-base retrieval, fill your own Chat and Embedding keys in `.env` before running the full scenario. See `docs/CONFIGURATION.md` for every required field and safe key-generation commands.

## Architecture

- `backend/`: FastAPI API, tenant isolation, SQL guard, analysis workflow and audit trail.
- `frontend/`: React console for conversations and the supply-chain dashboard.
- `database/`: platform/source database boundary, migration index, and demo seed contract.
- `infra/`: Docker initialization files, Prometheus profile and Helm chart.
- `docs/`: course package and operational guidance.

See `docs/ARCHITECTURE.md` for directory ownership and the module boundary policy.

## Course delivery

- Student lab path: `docs/COURSE_LABS.md`
- Instructor guide: `docs/INSTRUCTOR_GUIDE.md`
- Assessment rubric: `docs/ASSESSMENT_RUBRIC.md`
- Enterprise drills: `docs/ENTERPRISE_DRILLS.md`
- Configuration and keys: `docs/CONFIGURATION.md`

Useful classroom scripts:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/reset-demo.ps1 -Build
powershell -ExecutionPolicy Bypass -File scripts/acceptance-report.ps1 -RunTests
```

## Security boundary

Only source-database accounts with read-only permissions are supported. Every submitted SQL statement is parsed and checked before execution; only one `SELECT` or `WITH` statement may run. Credentials are encrypted at rest and never returned from the API.

See `docs/THIRD_PARTY_NOTICES.md` for the upstream reference and license notice.
# SupplyMind Enterprise Course Case

## Docker development

The default Compose stack runs the API, Celery worker, PostgreSQL/pgvector, Redis,
MinIO, and the React frontend. Build and start it with:

```powershell
docker compose build api worker
docker compose up -d
```

For day-to-day backend development, use the override with the source tree mounted
into the containers and API hot reload enabled:

```powershell
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build api worker
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec api pytest -q
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec api ruff check app scripts tests
```

The development override is intentionally explicit so the normal Compose command
remains suitable for the course's reproducible baseline. API: `http://localhost:8000`,
frontend: `http://localhost:5173`, MinIO console: `http://localhost:9001`.
