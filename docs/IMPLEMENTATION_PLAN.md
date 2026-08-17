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

## Next Small Tasks

- [ ] Worker dispatch hardening: route document tasks through Celery by default in deployed environments while retaining eager local development mode.
  - Done when: Compose worker consumes an upload task and API can inspect retry/failure state without duplicate chunks.
- [ ] Retrieval integration verification: mock the embedding provider in an API integration test and verify cited search results plus cross-tenant denial.
  - Done when: a search response returns text, score, document name, and chunk location under a mocked provider.
- [ ] Report delivery: persist Markdown, export PDF in a worker, and authorize downloads by tenant and role.
  - Done when: an analyst can download only their organization report.
- [ ] Identity and tenancy: membership management, refresh/logout, OIDC authorization-code flow, Alembic migration, and PostgreSQL RLS policies.
  - Done when: cross-tenant access fails in API and database-policy tests.
- [ ] Product and delivery: split React pages, add managed datasource/knowledge/report screens, complete Compose/Helm/monitoring, and expand the course package.
  - Done when: Compose runs the documented end-to-end scenario and browser tests pass.
  - Constraint: any frontend implementation must load both `taste-skill` and `impeccable` first.
