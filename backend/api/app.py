"""
FastAPI app exposing regime generation to the frontend.
Dev-only: no authentication.

Run from backend/:  ../.venv/bin/uvicorn api.app:app --reload --port 8000
"""

from contextlib import asynccontextmanager
from datetime import date, timedelta

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from api import store
from src.regime_hmm.palette import REGIME_COLORS

# Yahoo Finance only serves 1h bars for roughly the last 730 days
MAX_LOOKBACK_DAYS = 729

@asynccontextmanager
async def lifespan(app: FastAPI):
    imported = store.import_legacy_reports()
    if imported:
        print(f"Imported legacy reports: {', '.join(imported)}")
    yield

app = FastAPI(title="Market Regime API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class GenerateRequest(BaseModel):
    ticker: str
    start_date: date
    end_date: date
    max_regimes: int = Field(default=3, ge=1, le=10)
    fat_tail: bool = False
    switch_cost: float = Field(default=0.0, ge=0)

@app.get("/api/health")
def health():
    return {"status": "ok"}

@app.get("/api/palette")
def palette():
    return {"colors": REGIME_COLORS}

@app.post("/api/generate")
def generate(req: GenerateRequest):
    ticker = req.ticker.strip().upper()
    if not store.TICKER_RE.match(ticker):
        raise HTTPException(400, f"Invalid ticker: {req.ticker!r}")

    today = date.today()
    if req.start_date >= req.end_date:
        raise HTTPException(400, "Start date must be before end date.")
    if req.end_date > today:
        raise HTTPException(400, "End date cannot be in the future.")
    if req.start_date < today - timedelta(days=MAX_LOOKBACK_DAYS):
        raise HTTPException(400, f"Start date must be within the last {MAX_LOOKBACK_DAYS} days (Yahoo Finance hourly data limit).")

    try:
        generation, cached = store.generate(
            ticker=ticker,
            start_date=req.start_date.isoformat(),
            end_date=req.end_date.isoformat(),
            max_regimes=req.max_regimes,
            fat_tail=req.fat_tail,
            switch_cost=req.switch_cost,
        )
    except ValueError as e:
        raise HTTPException(422, str(e))
    except Exception as e:
        raise HTTPException(500, f"Generation failed: {e}")

    return {**generation, "cached": cached}

@app.get("/api/generations")
def list_generations():
    return store.list_generations()

@app.get("/api/generations/{gen_id}")
def get_generation(gen_id: str):
    generation = store.get_generation(gen_id)
    if generation is None:
        raise HTTPException(404, "Generation not found.")
    return generation

@app.delete("/api/generations/{gen_id}", status_code=204)
def delete_generation(gen_id: str):
    if not store.delete_generation(gen_id):
        raise HTTPException(404, "Generation not found.")

@app.get("/api/generations/{gen_id}/{filename}")
def get_image(gen_id: str, filename: str):
    path = store.image_path(gen_id, filename)
    if path is None:
        raise HTTPException(404, "Image not found.")
    return FileResponse(path, media_type="image/png")
