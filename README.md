# Amazon Price Tracker
Price tracker for Amazon items, currently there is only data on graphical processing units available, but a feature will be added for you to add your own url.

## Backend (FastAPI, Python 3.14)

```bash
uv sync --extra dev
cp .env.example .env                  # optional, settings are read from env vars or .env
uv run fastapi dev                    # API on http://localhost:8000, docs at /docs
uv run python -m app.scraper.run      # scrape tracked products into app/data/gpu_data.csv
uv run nox                            # ruff check + format --check, mypy --strict, pytest
uv run nox -s format                  # apply ruff fixes and formatting
```

## Frontend (Angular)

```bash
cd frontend
npm install
npm start    # http://localhost:4200, proxies /api to the backend
npm test
```
