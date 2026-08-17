# Compatibility layer

The existing `app/api.py`, `app/models.py`, `app/schemas.py`, and `app/services`
remain stable entry points while domain modules are extracted. New routes should
be implemented in `app/modules/<domain>` and re-exported here only when an old
import path or API contract must remain unchanged.
