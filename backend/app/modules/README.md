# Modular monolith boundaries

`app/modules` is the domain boundary for the SupplyMind backend. Each module owns
its schemas, services, API router, background tasks, and migration changes as the
implementation is extracted from the current compatibility layer (`app/api.py`,
`app/services`, and `app/models.py`).

Rules for new work:

1. A module may depend on `app/core`, `app/db`, and declared ports from another module.
2. A module must not import another module's SQLAlchemy internals directly; use a service or port.
3. Every tenant resource requires both a service-layer tenant predicate and a database RLS policy.
4. API handlers stay thin: validate input, resolve principal, call a domain service, and map the result.
5. Background tasks receive an idempotency key and persist state transitions before doing external work.

The first extraction targets dashboards and audit because they have bounded contracts;
identity and datasource extraction follows after the current compatibility endpoints
are covered by contract tests.
