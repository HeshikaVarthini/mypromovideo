# Run locally with Python 3.10+ (3.14 not yet supported by all deps)
py -3.10 -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt -q
$env:YOUTUBE_API_KEY = (Get-Content .env -ErrorAction SilentlyContinue | Where-Object { $_ -match '^YOUTUBE_API_KEY=' } | ForEach-Object { $_ -replace '^YOUTUBE_API_KEY=', '' })
.\.venv\Scripts\uvicorn app.main:app --reload --port 8000
