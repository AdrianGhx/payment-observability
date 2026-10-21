import asyncio
import random
import time
import uuid
from datetime import datetime, timezone
from enum import Enum

from fastapi import FastAPI, HTTPException, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from pydantic import BaseModel, Field
from starlette.routing import Match

from app.metrics import (
    HTTP_REQUEST_DURATION,
    HTTP_REQUEST_TOTAL,
    PAYMENTS_IN_PROGRESS,
    PAYMENTS_TOTAL,
)

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
async def metrics_middleware(request: Request, call_next):
    # Nie mierzymy samego scrape'a, żeby nie zaśmiecać metryk
    if request.url.path == "/metrics":
        return await call_next(request)

    endpoint = get_route_template(request)
    method = request.method
    status_code = 500  # domyślnie 500, jeśli poleci nieobsłużony wyjątek
    start = time.perf_counter()

    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    finally:
        duration = time.perf_counter() - start
        HTTP_REQUEST_DURATION.labels(method=method, endpoint=endpoint).observe(duration)
        HTTP_REQUEST_TOTAL.labels(
            method=method, endpoint=endpoint, status=str(status_code)
        ).inc()


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
            raise HTTPException(status_code=500, detail="Payment processor error")

        payment_id = str(uuid.uuid4())
        payment = {
            "id": payment_id,
            "amount": req.amount,
            "currency": req.currency,
            "status": "completed",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        payments_db[payment_id] = payment
        PAYMENTS_TOTAL.labels(status="success", currency=req.currency.value).inc()
        return payment


@app.get("/payments/{payment_id}")
async def get_payment(payment_id: str):
    payment = payments_db.get(payment_id)
    if payment is None:
        raise HTTPException(status_code=404, detail="Payment not found")
    return payment