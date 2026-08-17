# SupplyMind Codex Handoff

This file is the continuation contract for a new Codex window. Read it before changing code.

## Current Snapshot

- Repository: `supplymind-enterprise`
- Current commit: `a432178 feat: complete demo sources and analysis workflow`
- Branch: `main`
- Working tree: clean at the time this handoff was written.
- Product: SupplyMind, an original multi-tenant, read-only AI supply-chain analytics teaching project inspired by DB-GPT architecture. Do not copy DB-GPT branding or UI.

## Product Requirements

The course case must provide organization isolation, fixed roles (`platform_admin`, `org_admin`, `analyst`, `viewer`), JWT login/refresh/logout, OIDC authorization-code integration, MySQL 8+/PostgreSQL 14+ read-only data sources, encrypted credentials, host/CIDR and table allowlists, schema snapshots, AST-guarded single-statement `SELECT`/`WITH` execution, query limits/timeouts, audit records, usage/version metadata, knowledge-base RAG, MCP tools, an eight-stage Agent workflow, SSE progress, Markdown/PDF reports, a five-component supply-chain dashboard, Celery/Redis tasks, OpenTelemetry/Prometheus/Grafana, Docker Compose, Helm, CI, and a complete course package.

The canonical scope and exclusions are in `docs/IMPLEMENTATION_PLAN.md`, `docs/ARCHITECTURE.md`, and `docs/ACCEPTANCE_CHECKLIST.md`. The platform database is separate from customer source databases; source business data must not be copied in full.

## Completed

- Repository classified into `backend`, `frontend`, `database`, `infra`, and `docs`.
- Domain boundaries and compatibility layer established for audit, dashboards, datasources, tenancy, knowledge, analysis, reports, and MCP.
- JWT/password auth, refresh rotation, logout, member roles, OIDC discovery/callback flow, tenant predicates, and audit APIs exist.
- Dashboard persistence/cache metadata and asynchronous refresh task exist.
- Data-source creation, encrypted passwords, host/CIDR validation, connection test, schema sync, guarded query, and tenant filtering exist.
- Knowledge-base creation, PDF/Markdown/TXT upload, idempotent ingestion tasks, chunking, embedding calls, retrieval citations, and ingestion status APIs exist.
- Analysis service persists runs and Agent steps, calls MCP tools, emits `queued`, `step_started`, `sql_draft`, `tool_result`, `chart_ready`, `completed`, and `failed`, and creates reports/PDF exports.
- Frontend console contains overview, datasource management, knowledge-base upload/status, analysis session result detail, reports, members, and audit views.
- Compose runs platform PostgreSQL/pgvector, Redis, API, Worker, frontend, MinIO, Prometheus/Grafana, plus isolated `demo-postgres` and `demo-mysql` source databases.
- Demo source seed assets are in `database/seeds/postgresql/001_supply_chain.sql` and `database/seeds/mysql/001_supply_chain.sql`. They cover suppliers, materials, purchase orders, production work orders, inventory, quality inspections, sales orders, and delivery plans.
- DeepSeek-compatible chat and Alibaba Bailian-compatible embedding endpoints were reachable from the API container. Secrets remain local in `.env` and must never be committed or printed.

## Verification Baseline

Run from the repository root:

```powershell
docker compose up -d --build
docker compose ps
docker exec -e SUPPLYMIND_INGESTION_MODE=eager 1-api-1 pytest -q
docker exec 1-api-1 ruff check app tests
Push-Location frontend; npm run build; Pop-Location
```

Expected baseline: backend `20 passed`, Ruff clean, frontend build succeeds, API live and frontend return HTTP `200`. The current Compose project name is usually `1`; use `docker compose ps` and substitute actual container names if Docker assigns a different prefix.

Demo source connection values inside the Compose network:

- PostgreSQL: host `demo-postgres`, port `5432`, database `supplychain`, user `supplymind_ro`.
- MySQL: host `demo-mysql`, port `3306`, database `supplychain`, user `supplymind_ro`.
- The local demo password is defined only by Compose/.env conventions; never put credentials in docs, commits, screenshots, or final reports.

## Next Work, In Order

1. Add a reliable browser/E2E test (Playwright or the browser skill) for login, datasource list, document upload, ingestion status, analysis SSE, report/PDF download, and unauthorized states.
2. Run the full real-model path with a seeded source: create a knowledge base/document, ask `近 30 天各工厂生产达成率与缺料风险`, verify SQL Guard, rows, chart, citations, Markdown/PDF, and audit events.
3. Fix or document any browser multipart-upload issue; API and unit/integration coverage already exist, but browser upload must be observed end to end.
4. Complete remaining hardening backlog: production-only Alembic startup policy, full initial migration/RLS verification, OIDC mocked integration tests, task retry/dead-letter inspection, and source-database E2E assertions.
5. Finish course acceptance materials and CI checks for migrations, API contracts, SAST, dependency/image scans, Helm rendering, and 16 GB Compose reproduction.

## Development Rules

- Preserve `/api/v1` compatibility routes and tenant checks. Do not perform a destructive rewrite.
- Production must not call `create_all` or seed demo data; use explicit Alembic migrations.
- Every tenant query must include service-layer `tenant_id` filtering and retain PostgreSQL RLS enforcement.
- New backend code belongs under the relevant `backend/app/modules/<domain>` boundary; compatibility imports remain until migration is verified.
- Frontend visual changes must first read and follow both `taste-skill` and `impeccable`, run Impeccable context/detector, rebuild, and verify Docker HTTP `200`.
- Use Docker for the primary development/test environment. Keep API keys in ignored `.env` or deployment secrets only.
- Make each small slice independently testable and commit it separately with a focused message.

## Useful References

- Requirements and slice status: `docs/IMPLEMENTATION_PLAN.md`
- Architecture and ownership: `docs/ARCHITECTURE.md`
- Acceptance criteria: `docs/ACCEPTANCE_CHECKLIST.md`
- Deployment: `docs/HELM_DEPLOYMENT.md`
- Course package: `docs/COURSE_PACKAGE.md`, `docs/COURSE_OUTLINE.md`
- Rollback: `docs/ROLLBACK_RUNBOOK.md`
