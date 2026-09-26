from prometheus_client import Counter, Histogram

HTTP_REQUESTS = Counter("http_requests_total", "HTTP requests", ["method", "path", "status"])
HTTP_LATENCY = Histogram(
    "http_request_duration_seconds", "HTTP latency", ["method", "path"]
)
TRIAGE_LATENCY = Histogram(
    "triage_duration_seconds",
    "Triage latency",
    ["provider"],
    buckets=(0.005, 0.01, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 20),
)
TRIAGE_FALLBACKS = Counter(
    "triage_fallback_total", "Triage fallbacks", ["provider", "error_class"]
)
TRIAGE_CACHE = Counter("triage_cache_total", "Triage cache lookups", ["result"])
