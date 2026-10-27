import asyncio
import logging
import random
import time
import uuid
from datetime import UTC, datetime
from enum import Enum

from fastapi import FastAPI, HTTPException, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from pydantic import BaseModel, Field
from starlette.routing import Match

from app.logging_config import request_id_var, setup_logging
from app.metrics import (
    HTTP_REQUEST_DURATION,
    HTTP_REQUESTS_TOTAL,
    PAYMENTS_IN_PROGRESS,
    PAYMENTS_TOTAL,
)

setup_logging()
logger = logging.getLogger("payments")

app = FastAPI(title="Payments Service", version="0.1.0")

FAILURE_RATE = 0.05
payments_db: dict[str, dict] = {}


class Currency(str, Enum):
    PLN = "PLN"
    EUR = "EUR"
    USD = "USD"


class PaymentRequest(BaseModel):
    amount: float = Field(gt=0, le=100_000)
    currency: Currency


# ---------- Monitoring ----------

def get_route_template(request: Request) -> str:
    """Zwraca szablon ścieżki (np. /payments/{payment_id}), a nie faktyczny URL.
    Chroni przed eksplozją kardynalności labela 'endpoint'."""
    for route in request.app.routes:
        match, _ = route.matches(request.scope)
        if match == Match.FULL:
            return route.path
    return "unmatched"


@app.middleware("http")
async def observability_middleware(request: Request, call_next):
    if request.url.path == "/metrics":
        return await call_next(request)

    # Bierzemy ID od klienta (jeśli przysłał), w przeciwnym razie generujemy nowe
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    token = request_id_var.set(request_id)

    endpoint = get_route_template(request)
    method = request.method
    status_code = 500
    start = time.perf_counter()

    try:
        response = await call_next(request)
        status_code = response.status_code
        response.headers["X-Request-ID"] = request_id
        return response
    except Exception:
        logger.exception("unhandled exception")
        raise
    finally:
        duration = time.perf_counter() - start

        HTTP_REQUEST_DURATION.labels(method=method, endpoint=endpoint).observe(duration)
        HTTP_REQUESTS_TOTAL.labels(
            method=method, endpoint=endpoint, status=str(status_code)
        ).inc()

        if status_code >= 500:
            level = logging.ERROR
        elif status_code >= 400:
            level = logging.WARNING
        else:
            level = logging.INFO

        logger.log(level, "request completed", extra={"fields": {
            "method": method,
            "endpoint": endpoint,
            "path": request.url.path,
            "status": status_code,
            "duration_ms": round(duration * 1000, 2),
        }})

        request_id_var.reset(token)


@app.get("/metrics", include_in_schema=False)
async def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


# ---------- API ----------

@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/payments", status_code=201)
async def create_payment(req: PaymentRequest):
    with PAYMENTS_IN_PROGRESS.track_inprogress():
        await asyncio.sleep(random.uniform(0.05, 0.5))

        if random.random() < FAILURE_RATE:
            PAYMENTS_TOTAL.labels(status="failed", currency=req.currency.value).inc()
            logger.error("payment failed", extra={"fields": {
                "amount": req.amount,
                "currency": req.currency.value,
                "reason": "processor_error",
            }})
            raise HTTPException(status_code=500, detail="Payment processor error")

        payment_id = str(uuid.uuid4())
        payment = {
            "id": payment_id,
            "amount": req.amount,
            "currency": req.currency.value,
            "status": "completed",
            "created_at": datetime.now(UTC).isoformat(),
        }
        payments_db[payment_id] = payment
        PAYMENTS_TOTAL.labels(status="success", currency=req.currency.value).inc()
        logger.info("payment completed", extra={"fields": {
            "payment_id": payment_id,
            "amount": req.amount,
            "currency": req.currency.value,
        }})
        return payment


@app.get("/payments/{payment_id}")
async def get_payment(payment_id: str):
    payment = payments_db.get(payment_id)
    if payment is None:
        logger.warning("payment not found", extra={"fields": {
            "payment_id": payment_id,
        }})
        raise HTTPException(status_code=404, detail="Payment not found")
    return payment