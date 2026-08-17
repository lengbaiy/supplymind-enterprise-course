# SupplyMind

SupplyMind is a multi-tenant, read-only AI data analysis console for manufacturing supply chains. It is an original teaching implementation inspired by the architecture of DB-GPT, not a fork or redistribution of DB-GPT.

## Quick start

```powershell
Copy-Item .env.example .env
docker compose up --build
```

Open `http://localhost:5173`. The seeded organization is `demo-factory`; sign in with `admin@demo.local` and password `ChangeMe123!`.

## Architecture

- `backend/`: FastAPI API, tenant isolation, SQL guard, analysis workflow and audit trail.
- `frontend/`: React console for conversations and the supply-chain dashboard.
- `infra/`: Docker initialization files, Prometheus profile and Helm chart.
- `docs/`: course package and operational guidance.

## Security boundary

Only source-database accounts with read-only permissions are supported. Every submitted SQL statement is parsed and checked before execution; only one `SELECT` or `WITH` statement may run. Credentials are encrypted at rest and never returned from the API.

See `docs/THIRD_PARTY_NOTICES.md` for the upstream reference and license notice.
