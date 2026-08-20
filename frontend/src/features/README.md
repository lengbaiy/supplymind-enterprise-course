# Feature modules

Business screens are grouped by domain: identity, datasources, knowledge, analysis,
reports, dashboards, audit, and system. Each domain owns its views and local state
while shared API/SSE calls remain in `src/services`.

Each business domain also owns `pages`, `components`, `api`, `hooks`, `types`, and
tests. New functionality must not be added to `main.tsx`; that file is the temporary
legacy compatibility surface while the existing console is migrated route by route.
