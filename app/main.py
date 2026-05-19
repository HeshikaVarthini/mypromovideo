"""FastAPI application — Video Competitor Intelligence & Report Generator."""

from __future__ import annotations

import json
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.analyzer import VideoAnalyzer
from app.models import ReportRequest
from app.report_generator import PowerPointReportGenerator
from app.youtube_client import YouTubeClient

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(
    title="Video Competitor Intelligence",
    description="Analyse YouTube video marketing across competitors and generate reports.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory cache for latest reports (per session simplicity)
_report_cache: dict[str, dict] = {}


def _cache_key(company: str, competitors: list[str]) -> str:
    parts = [company.lower().strip()] + sorted(c.lower().strip() for c in competitors)
    return "|".join(parts)


@app.get("/", response_class=HTMLResponse)
async def index():
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return HTMLResponse(index_path.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Video Competitor Intelligence</h1><p>Static files not found.</p>")


@app.get("/api/health")
async def health():
    has_key = bool(os.environ.get("YOUTUBE_API_KEY"))
    return {
        "status": "ok",
        "youtube_api_configured": has_key,
    }


@app.post("/api/analyze")
async def analyze(request: ReportRequest):
    if not os.environ.get("YOUTUBE_API_KEY"):
        raise HTTPException(
            status_code=503,
            detail=(
                "YouTube API key not configured. Set YOUTUBE_API_KEY environment variable. "
                "Create one at https://console.cloud.google.com/apis/credentials"
            ),
        )

    all_companies = [request.company] + request.competitors
    if len(all_companies) < 2:
        raise HTTPException(
            status_code=400,
            detail="Enter your company and at least one competitor.",
        )

    try:
        client = YouTubeClient()
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    channels = []
    for name in all_companies:
        channel = await client.fetch_company_channel(name)
        channels.append(channel)

    found = [c for c in channels if c.found]
    if not found:
        raise HTTPException(
            status_code=404,
            detail="No YouTube channels found for the provided company names. Try different spellings.",
        )

    analyzer = VideoAnalyzer()
    report = analyzer.analyze(request, channels)

    report_dict = report.model_dump(mode="json")
    key = _cache_key(request.company, request.competitors)
    _report_cache[key] = report_dict

    return JSONResponse(content=report_dict)


@app.get("/api/report/{cache_key:path}/download")
async def download_pptx(cache_key: str):
    report_dict = _report_cache.get(cache_key)
    if not report_dict:
        raise HTTPException(status_code=404, detail="Report not found. Generate a new report first.")

    from app.models import AnalysisReport

    report = AnalysisReport.model_validate(report_dict)
    generator = PowerPointReportGenerator()
    pptx_bytes = generator.generate(report)

    safe_name = report.company.replace(" ", "_")[:30]
    filename = f"video_intel_{safe_name}.pptx"

    tmp_path = BASE_DIR / "tmp" / filename
    tmp_path.parent.mkdir(exist_ok=True)
    tmp_path.write_bytes(pptx_bytes)

    return FileResponse(
        path=tmp_path,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
    )


@app.post("/api/download")
async def download_from_body(body: dict):
    """Download PPTX using report JSON from client."""
    from app.models import AnalysisReport

    try:
        report = AnalysisReport.model_validate(body)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid report data") from exc

    generator = PowerPointReportGenerator()
    pptx_bytes = generator.generate(report)

    safe_name = report.company.replace(" ", "_")[:30]
    filename = f"video_intel_{safe_name}.pptx"
    tmp_path = BASE_DIR / "tmp" / filename
    tmp_path.parent.mkdir(exist_ok=True)
    tmp_path.write_bytes(pptx_bytes)

    return FileResponse(
        path=tmp_path,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
    )


if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
