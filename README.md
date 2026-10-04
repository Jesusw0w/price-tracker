# Amazon Price Tracker
Price tracker for Amazon items, currently there is only data on graphical processing units available, but a feature will be added for you to add your own url.

## Backend (FastAPI, Python 3.14)

```bash
uv sync --extra dev
cp .env.example .env                  # set PT_DATABASE_URL, or export it instead
uv run alembic upgrade head           # create or update the schema
uv run fastapi dev                    # API on http://localhost:8000, docs at /docs
uv run python -m app.scraper.run      # scrape tracked products, save today's prices
uv run nox                            # ruff check + format --check, mypy --strict, pytest
uv run nox -s format                  # apply ruff fixes and formatting
```

After changing `app/db/models.py`: `uv run alembic revision --autogenerate -m "..."`,
review the generated file in `migrations/versions/`, then `alembic upgrade head`.

## Frontend (Angular)

```bash
cd frontend
npm install
npm start    # http://localhost:4200, proxies /api to the backend
npm test
```
