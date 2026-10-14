from __future__ import annotations

import asyncio
import logging
import sys
from datetime import date

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .crawler import ThreadsCrawler, analyze_keyword

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Threads Keyword Analyzer", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["POST"],
    allow_headers=["*"],
)


class AnalyzeRequest(BaseModel):
    keyword: str = Field(min_length=1, max_length=100)
    start_date: date | None = None
    end_date: date | None = None


class AnalyzeResponse(BaseModel):
    dates: list[str]
    counts: list[int]
    posts: list[dict]
    top_engagement: list[dict]
    top_likes: list[dict]


@app.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze(request: AnalyzeRequest) -> AnalyzeResponse:
    keyword = request.keyword.strip()
    if not keyword:
        raise HTTPException(status_code=400, detail="keyword cannot be empty")
    if request.start_date and request.end_date and request.start_date > request.end_date:
        raise HTTPException(status_code=400, detail="start_date cannot be after end_date")

    try:
        result = await analyze_keyword(keyword, request.start_date, request.end_date)
    except Exception as error:
        logging.exception("Keyword analysis failed for %r", keyword)
        raise HTTPException(status_code=502, detail="Unable to fetch Threads data") from error

    return AnalyzeResponse(**result)


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/auth/status")
async def auth_status() -> dict[str, str | bool | None]:
    return await ThreadsCrawler().login_status()
