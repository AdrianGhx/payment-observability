import asyncio
import random
import uuid
from datetime import datetime, timezone
from enum import Enum

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

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


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/payments", status_code=201)
async def create_payment(req: PaymentRequest):
    await asyncio.sleep(random.uniform(0.05, 0.5))

    if random.random() < FAILURE_RATE:
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
    return payment


@app.get("/payments/{payment_id}")
async def get_payment(payment_id: str):
    payment = payments_db.get(payment_id)
    if payment is None:
        raise HTTPException(status_code=404, detail="Payment not found")
    return payment