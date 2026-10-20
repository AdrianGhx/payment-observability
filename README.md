# Payment Observability Platform

Demo platformy obserwowalności dla mikroserwisów płatniczych:
metryki (VictoriaMetrics), dashboardy (Grafana), alerting oparty o SLO.

## Status
🚧 W budowie: v0.1 (serwis payments)

## Uruchomienie lokalne
```bash
cd services/payments
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Dokumentacja API: http://localhost:8000/docs
