from prometheus_client import Counter, Histogram

HTTP_REQUESTS = Counter(
    "supplymind_http_requests_total",
    "Total HTTP requests handled by the API",
    ("method", "path", "status"),
)
HTTP_REQUEST_DURATION = Histogram(
    "supplymind_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ("method", "path"),
)
