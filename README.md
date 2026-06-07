# BurgerPrints Text-to-API Agent

Core FastAPI service for mapping seller text requests to BurgerPrints API calls and rule-based agent answers.

## Setup

```powershell
conda activate OCR
pip install -r requirements.txt
copy .env.example .env
```

Set `BURGERPRINTS_API_KEY` in `.env`.

## Run API

```powershell
uvicorn src.main:app --reload
```

Docs:

```text
http://127.0.0.1:8000/docs
```

## Endpoints

```text
GET  /health
POST /text-to-api
POST /agent/chat
```

Example request:

```json
{
  "message": "Tôi bán Etsy giá 24.99 margin 40%, tìm SKU ship US"
}
```

## Tests

```powershell
python -m unittest test_core.py test_agent.py
python test_burgerprints_api.py
```

## Structure

```text
src/
  main.py
  api/
    router.py
    routes/
    schemas/
  core/
    config.py
    database.py
    normalizer.py
    text_parser.py
    engine.py
  services/
    burgerprints_client.py
    margin.py
    ranking.py
  agent/
    service.py
    orchestrator.py
    formatter.py
    agents/
    tools/
```

Note: current SKU search uses BurgerPrints Product API: `GET /v2/product`, `GET /v2/product/{short_code}`, and `GET /v2/product/outofstock`. Shipping fee and delivery time endpoints are still not confirmed.
