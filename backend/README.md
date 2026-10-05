# Backend (FastAPI, Python 3.14)

Run everything from this directory.

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
