# Legacy console transition boundary

The existing console remains the compatibility implementation while pages move into
their domain folders. New code must use `app`, `design-system`, shared components,
and domain-local API hooks. Do not add new features to `main.tsx`.
