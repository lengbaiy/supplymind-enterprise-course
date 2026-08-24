# SupplyMind Architecture

## Repository ownership

| Directory | Responsibility | Must not contain |
| --- | --- | --- |
| `backend/` | FastAPI API, domain services, Celery tasks, migrations, backend tests | Frontend assets or production secrets |
| `frontend/` | React/TypeScript console, API/SSE clients, browser tests | Database migrations or server credentials |
| `database/` | Database contracts, seed documentation, migration index | A second executable migration system |
| `infra/` | Compose support, Prometheus, Grafana, Helm and deployment manifests | Domain business logic |
| `docs/` | Architecture, configuration, API and operations documentation | Runtime configuration or generated claims |

## Backend layering

`app/core` provides configuration and cross-cutting infrastructure. `app/modules`
contains bounded domains. `app/api.py` is the versioned API entry point, while
domain services call repositories and declared ports. Background tasks persist
state before external work.

## Runtime boundaries

The API and Worker share the platform PostgreSQL database and Redis broker. MinIO
is the local S3-compatible object store. Customer MySQL/PostgreSQL databases are
accessed through short-lived, read-only connections and are never mounted into
the application container.

## Environment modes

- Development: Compose, automatic schema creation, demo platform seed, eager local ingestion.
- Test: isolated SQLite/PostgreSQL test database, mocked model providers, no external customer data.
- Production: explicit Alembic migration, external PostgreSQL/Redis/S3/OIDC, no demo seed, broker-backed tasks.

## Enterprise Agent runtime

The root LangGraph uses `TypedDict + Annotated` state reducers and durable
PostgreSQL checkpoints. The Router emits `data`, `knowledge`, `hybrid` or
`unsupported`; hybrid work uses LangGraph `Send` to run the data and knowledge
Subagents concurrently. Handoffs, retries and verification remain in the graph
state, not in browser code.

Subagents call the separately deployed MCP Server. Tool calls carry a short
lived tenant token, are RBAC checked, schema validated, audited and restricted
to read-only SQL or an explicit approval workflow. Analysis events are saved in
PostgreSQL, published to Redis and replayed through SSE with `Last-Event-ID`.

Knowledge retrieval uses parent/child chunks, Multi-Query, HyDE, dense and
PostgreSQL BM25 retrieval, RRF fusion, reranking and parent-context mapping.
User memory is stored independently from checkpoints with a category allowlist,
confidence, version, expiry and user controls.

## API stability rule

All changes preserve the existing `/api/v1` contract. New enterprise APIs use
additive routes. A module change is complete only after API and domain tests
pass together.
