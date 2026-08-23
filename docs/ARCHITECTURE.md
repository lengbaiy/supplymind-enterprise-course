# SupplyMind Architecture

## Repository ownership

| Directory | Responsibility | Must not contain |
| --- | --- | --- |
| `backend/` | FastAPI API, domain services, Celery tasks, migrations, backend tests | Frontend assets or production secrets |
| `frontend/` | React/TypeScript console, API/SSE clients, browser tests | Database migrations or server credentials |
| `database/` | Database contracts, seed documentation, migration index | A second executable migration system |
| `infra/` | Compose support, Prometheus, Grafana, Helm and deployment manifests | Domain business logic |
| `docs/` | Requirements, architecture, course and operations documentation | Runtime configuration |

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

## API stability rule

All changes must preserve the existing `/api/v1` contract unless the course
exercise explicitly asks for a versioned API change. A module change is complete
only after API tests and domain tests pass together.
