# Video Competitor Intelligence & Report Generator

A live web application that analyses YouTube video marketing across your company and up to 4 competitors, displays an interactive report, and exports a professional PowerPoint deck.

## Features

- **Real YouTube data** via YouTube Data API v3 (channels, videos, views, likes, comments)
- **Comparative analysis** with executive summary, rankings, gap analysis, and actionable recommendations
- **Web report** readable before download
- **PowerPoint export** (12 slides) with charts, tables, and professional design

## Quick Start (Local)

### 1. Get a YouTube API Key

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project and enable **YouTube Data API v3**
3. Create an API key under Credentials
4. Copy the key to `.env`:

```bash
cp .env.example .env
# Edit .env and set YOUTUBE_API_KEY=...
```

### 2. Run locally

```powershell
# Requires Python 3.10–3.12 (3.14 not yet supported by all packages)
py -3.10 -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
# Set YOUTUBE_API_KEY in .env or environment
uvicorn app.main:app --reload --port 8000
```

Or run: `.\run_local.ps1`

Open http://localhost:8000

### 3. Deploy to Render (free tier)

1. Push this repo to GitHub
2. Sign up at [render.com](https://render.com)
3. **New → Blueprint** and connect the repo (uses `render.yaml`)
4. Set environment variable `YOUTUBE_API_KEY` in the Render dashboard
5. Deploy — your public URL will be `https://vidintel.onrender.com` (or similar)

Alternatively: **New → Web Service → Docker**, point to this repo, set `YOUTUBE_API_KEY`.

## Usage

1. Enter your company name (e.g. `HubSpot`)
2. Add 1–4 competitors (e.g. `Salesforce`, `Marketo`, `Mailchimp`)
3. Click **Analyse & Generate Report**
4. Review the web report
5. Click **Download PowerPoint** for the full `.pptx`

## Report Slides (12)

1. Cover
2. Executive Summary
3. Channel Overview (table)
4. Audience Reach (subscriber chart)
5. Content Performance (top videos)
6. Content Topics & Themes
7. Posting Frequency & Consistency (chart)
8. Engagement Analysis (chart + table)
9. Gap Analysis
10. Video Marketing Recommendations
11. Competitive Scorecard (rankings)
12. *(Charts distributed across slides)*

## API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/analyze` | POST | Run analysis `{"company":"...", "competitors":["..."]}` |
| `/api/download` | POST | Download PPTX (send report JSON body) |

## Tech Stack

- **Backend:** FastAPI, httpx, python-pptx, matplotlib
- **Frontend:** HTML/CSS/JS
- **Data:** YouTube Data API v3

## Notes

- Analysis uses the most relevant YouTube channel match per company name
- API quota: each full report uses ~50–150 quota units depending on video count
- Default quota is 10,000 units/day (plenty for demo/testing)
