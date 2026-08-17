# SupplyMind Incremental Delivery Plan

This file is the execution source of truth for the enterprise course case. Each item is completed only after its listed verification succeeds.

## Completed

- [x] Runtime configuration and dependency boundaries: OpenAI-compatible model settings, OIDC settings, report directory, and datasource host/CIDR allowlists.
  - Verify: configuration load, unit tests, Ruff.
- [x] Secure datasource foundation: MySQL/PostgreSQL URL construction, deployment network checks, connection test, schema inspection, and guarded read-only execution endpoints.
  - Verify: allowlist tests, SQL guard tests, API smoke test.
- [x] Real-model analysis boundary: missing model credentials fail closed; model plans must be JSON; Agent steps are persisted; analysis uses guarded live datasource execution.
  - Verify: model-configuration test and existing regression suite.
- [x] MCP tool registry: typed input/output contracts, role gates, timeout metadata, and side-effect declarations.
  - Verify: registry role/schema test.
- [x] Knowledge storage: tenant-scoped knowledge bases, documents, and chunks with administrator CRUD/upload APIs.
  - Verify: knowledge upload/list integration test and tenant filters.
- [x] Document ingestion state machine: persisted idempotency key, source storage, chunk replacement, completed/failed status, retry counter, task inspection endpoint, and Celery worker entry point.
  - Verify: upload integration test asserts completed task state; worker task is importable and bounded to tenant-owned records.
- [x] Embedding integration boundary: OpenAI-compatible `/embeddings` client, optional ingestion-time vector persistence, cosine ranking service, and tenant-scoped search endpoint with cited document/chunk locations.
  - Verify: embedding fail-closed test and cosine ranking unit test; live provider verification remains environment-dependent.
- [x] Ingestion dispatch boundary: eager local execution, broker-mode Celery dispatch for Compose, persisted Celery task ID, and content-hash idempotent upload response.
  - Verify: duplicate upload integration test, 15 backend tests, Ruff, and Compose configuration validation.
- [x] Retrieval integration verification: mocked Embedding Provider API test, cited result assertions, and tenant resource denial.
  - Verify: search integration test returns score/document/location; unknown tenant resource returns `404`.
- [x] Report Markdown foundation: tenant-scoped report model, Markdown renderer with SQL/rows/citations, and report CRUD endpoints with role gates.
  - Verify: Markdown renderer unit test and full backend regression suite.
- [x] Alembic baseline and PostgreSQL tenant isolation: initial metadata migration, RLS policies for tenant tables, and request-scoped tenant context.
  - Verify: Docker `alembic upgrade head`, PostgreSQL `rowsecurity = true`, 18 backend tests, and Ruff.
- [x] Analysis trace foundation: eight named Agent stages, model/prompt version fields, automatic Markdown report creation, and SSE report identifiers.
  - Verify: Docker regression suite, migration `0002_agent_step_trace`, and Ruff.
- [x] MCP analysis integration: schema lookup, guarded SQL, knowledge citations, chart rendering, and report export are routed through typed tools.
  - Verify: optional knowledge-base analysis context, tool audit events, 19 Docker tests, and Ruff.

## Next Small Tasks

- [x] S11 repository classification: backend/frontend/database/infra/docs ownership, database asset index, compatibility boundary, and runtime-file ignore rules.
  - Verify: path checks, Compose validation, backend/frontend builds, and no local database artifacts tracked.
- [x] S12 audit domain extraction: repository, service, DTO, and router with `/api/v1/audit` compatibility.
- [x] S13 dashboard domain extraction: persisted dashboard metadata, widget model, cache status, five-minute refresh interval, and RLS migration.
- [x] S14 datasource domain boundary: tenant repository, gateway port, and connection/query service entry points.
- [x] S15 tenancy boundary: JWT membership lookup, tenant context, and role dependency compatibility exports.
- [x] S16 knowledge domain boundary: tenant knowledge-base repository and retrieval service entry point.
- [x] S17 analysis/report boundaries: Agent service, report repository, and Markdown/PDF service entry points.
- [x] S18 frontend service boundary: centralized API error handling and SSE event parsing.
- [x] S19 frontend feature boundaries: identity, datasources, knowledge, analysis, reports, dashboards, and audit ownership directories.

- [ ] Framework hardening: production startup uses Alembic only; domain module boundaries are explicit.
  - Done when: development retains seeded Compose startup, production skips `create_all` and demo seeding, and new code follows `backend/app/modules` boundaries.

- [x] Worker runtime verification: run a full Compose broker upload against PostgreSQL and Redis and inspect retry/failure state without duplicate chunks.
  - Verify: Docker upload returned `queued`, Worker consumed `supplymind.documents.ingest`, task reached `completed`, attempts `1`, and one chunk was persisted.
- [x] Report delivery: persist Markdown, export PDF in a worker, record checksum/status, and authorize downloads by tenant and role.
  - Done when: an analyst can download only their organization report.
- [ ] Identity and tenancy: membership management, refresh/logout, OIDC authorization-code flow, Alembic migration, and PostgreSQL RLS policies.
  - Done when: cross-tenant access fails in API and database-policy tests.
- [ ] Product and delivery: split React pages, add managed datasource/knowledge/report screens, complete Compose/Helm/monitoring, and expand the course package.
  - Done when: Compose runs the documented end-to-end scenario and browser tests pass.
  - Constraint: any frontend implementation must load both `taste-skill` and `impeccable` first.

## Five-Point Acceptance Progress (2026-08-17)

- [x] Knowledge document upload: multipart upload, idempotent ingestion task, status/chunk display, and worker-backed processing.
- [x] Analysis detail: SSE completion preserves guarded SQL, result rows, chart specification, citations, and report/PDF action.
- [x] Real demo sources: Compose now runs isolated PostgreSQL and MySQL teaching databases with repeatable supply-chain seed data and read-only credentials.
- [x] Model/RAG connectivity: container configuration reaches the DeepSeek-compatible chat endpoint and Alibaba Bailian embedding endpoint; failures remain fail-closed.
- [x] Docker acceptance pass: API, Worker, frontend, platform PostgreSQL, Redis, MinIO, both demo databases, Prometheus, and Grafana are healthy; backend tests pass in-container and frontend build passes.

The five points validate the course demonstration path. Production-scale SLA, disaster-recovery rehearsal, and large-scale load testing remain outside the course acceptance scope.

## Detailed Backlog

The following slices are intentionally ordered by dependency. Each slice has one primary acceptance result and should be committed separately.

### S01 - Celery dispatch hardening

- Add an environment switch for eager local tasks versus broker dispatch.
- Upload creates one idempotent task and sends the task ID to Celery in deployed mode.
- Worker updates `queued -> processing -> completed/failed`, records retry count and error details.
- Acceptance: a Compose worker consumes an upload task; retrying the same task does not duplicate chunks.

### S02 - Retrieval integration and tenant denial

- Mock the embedding provider at the HTTP boundary in integration tests.
- Verify search returns text, score, document name, chunk ID, and location.
- Create two organizations and verify one cannot search or read the other organization knowledge base.
- Acceptance: API integration test covers successful search and cross-tenant `404`.

### S03 - Report domain and Markdown output

- Add `Report` persistence linked to an analysis run, with tenant ID, author, Markdown body, structured citations, and status.
- Generate Markdown from analysis result and cited RAG chunks.
- Add report list/detail endpoints with role checks.
- Acceptance: analyst can create and read a report; viewer can read but cannot create.

### S04 - PDF export and object storage boundary

- Add a Celery PDF export task using the existing report directory in development.
- Persist export status, failure reason, file path, and checksum.
- Add an S3-compatible storage adapter interface without requiring S3 in local mode.
- Acceptance: authorized tenant member downloads a generated PDF; another tenant receives `404`.

### S05 - Refresh tokens, logout, and membership administration

- Add refresh-token rotation and server-side revocation records.
- Add organization member list, invite/role update, disable, and audit endpoints.
- Enforce fixed role matrix for every management operation.
- Acceptance: expired/revoked refresh tokens fail; viewers cannot mutate membership or data sources.

### S06 - OIDC authorization-code flow

- Add discovery, state/nonce validation, callback, issuer subject mapping, and local membership linking.
- Return the same local JWT session shape as password login.
- Add failure handling for state mismatch, missing claims, and unmapped organization.
- Acceptance: mocked OIDC provider integration test completes login and rejects replayed state.

### S07 - Alembic migrations and PostgreSQL RLS

- Replace startup `create_all` as the deployment migration path with a complete initial Alembic revision.
- Add tenant policies for all tenant models and request-scoped tenant setting transaction hook.
- Keep service-layer tenant predicates as the first authorization boundary.
- Acceptance: clean PostgreSQL migrates from zero; direct cross-tenant SQL is rejected by RLS tests.

### S08 - Analysis workflow and MCP completion

- Persist all eight Agent stages with model/prompt version, input summary, output, timing, and failure reason.
- Route schema lookup, SQL query, knowledge search, chart render, and report export through MCP contracts.
- Add citation payloads and consistent SSE event envelopes.
- Acceptance: one end-to-end analysis returns guarded SQL, rows, chart spec, citations, report ID, and audit events.

### S09 - Frontend functional pages

- Replace navigation placeholders with data source, knowledge base, analysis session, report, audit, and status views.
- Connect upload, ingestion status, search citations, report download, and permission errors.
- Keep the existing frontend skill workflow mandatory for every visual change.
- Acceptance: browser test covers login, datasource list, document upload, SSE progress, report download, and unauthorized state.

### S10 - Deployment, observability, and course verification

- Complete Compose profiles for MinIO, Prometheus, and Grafana with health checks.
- Complete Helm Secret/ConfigMap, probes, resource limits, ingress, and HPA values.
- Add CI checks for backend/frontend tests, migrations, SAST, dependency and image scans.
- Add course start/end code, instructor notes, deployment runbook, and acceptance checklist.
- Acceptance: documented 16 GB local Compose run completes the core scenario and all CI checks pass.
