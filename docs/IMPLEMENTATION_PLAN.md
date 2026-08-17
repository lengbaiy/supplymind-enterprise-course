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

## Next Small Tasks

- [ ] Document ingestion: upload PDF/Markdown/TXT, extract text, split chunks, enqueue work, and persist task state.
  - Done when: a document reaches `completed` or an inspectable `failed` state.
- [ ] Real embeddings and retrieval: call the configured OpenAI-compatible embedding endpoint and retrieve cited chunks.
  - Done when: a search response returns text, score, document name, and chunk location.
- [ ] Report delivery: persist Markdown, export PDF in a worker, and authorize downloads by tenant and role.
  - Done when: an analyst can download only their organization report.
- [ ] Identity and tenancy: membership management, refresh/logout, OIDC authorization-code flow, Alembic migration, and PostgreSQL RLS policies.
  - Done when: cross-tenant access fails in API and database-policy tests.
- [ ] Product and delivery: split React pages, add managed datasource/knowledge/report screens, complete Compose/Helm/monitoring, and expand the course package.
  - Done when: Compose runs the documented end-to-end scenario and browser tests pass.
  - Constraint: any frontend implementation must load both `taste-skill` and `impeccable` first.
