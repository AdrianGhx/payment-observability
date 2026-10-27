from prometheus_client import Counter, Gauge, Histogram, disable_created_metrics

# Wyłącza dodatkowe szeregi *_created (timestamp utworzenia licznika),
# których nie potrzebujemy, a zaśmiecałyby /metrics

disable_created_metrics()

# --- Metryki techniczne (RED) dla każdego endpointu ---

HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total number of HTTP requests",
    ["method", "endpoint", "status"],
)


HTTP_REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=(0.025, 0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.75, 1.0, 2.5, 5.0),
)

# --- Metryki biznesowe ---

PAYMENTS_TOTAL = Counter(
    "payments_total",
    "Total number of payment attempts",
    ["status", "currency"],
)

PAYMENTS_IN_PROGRESS = Gauge(
    "payments_in_progress",
    "Number of payments currently being processed",
)