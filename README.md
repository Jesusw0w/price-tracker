# Price Tracker
Tracks product prices from online shops. Add a product's https link from the UI or through an MCP agent; the scraper reads the price from the page's schema.org data or meta tags, with a dedicated parser for Amazon.

```
backend/    FastAPI API, MCP server, scraper, DB models and Alembic migrations
frontend/   Angular UI
docs/       architecture diagrams and ideas
```

## Backend

See [backend/README.md](backend/README.md) for local setup and an optional AWS deploy:
the API and MCP server on Lambda, the UI on S3 and CloudFront. The scraper always runs
locally.

## Docker

`compose.yaml` runs the UI, the API and the scraper. All three read `backend/.env`, so
they use the database configured there (the real one, unless you point it elsewhere).

```bash
docker compose up -d --build scraper   # just the scraper, e.g. on the home machine
docker compose up -d --build           # UI on http://localhost:4200, API docs on :8000/docs
docker compose logs -f scraper
docker compose run --rm scraper python -m app.scraper.run --once   # today's run now
docker compose run --rm api alembic upgrade head                    # migrations
docker compose down
```

Port 4200 is the local callback Cognito allows, so stop `npm start` first. The services
restart with Docker Desktop, so with Docker Desktop set to start at login, the scraper
keeps running without a terminal.

### Scraper

One process works the `refreshes` queue. Agents (`request_refresh`) and the daily run
both add to it:

- After `PT_SCRAPE_HOUR_UTC` (default 6), every tracked product not yet requested that
  UTC day is queued. A machine that was asleep at that hour catches up when it wakes.
- Products that several users track under the same URL are fetched once.
- Up to `PT_SCRAPE_WORKERS` sites (default 4) are scraped at once; requests to the
  same site stay 2 s apart.
- A page without a price, a block or an HTTP error marks the refresh `failed` with the
  reason, which `get_refresh_status` shows. A restart re-queues anything left `running`,
  so run only one scraper.

## Frontend (Angular)

```bash
cd frontend
npm install
npm start    # http://localhost:4200, proxies /api to the backend
npm test
```

Background images go in `frontend/public/backgrounds/` (`.webp`, `.avif`, `.jpg` or `.png`).
`npm start` and `npm run build` regenerate the folder's `index.json`, which the
change-background button picks from at random. Hosts like S3 can't list a folder, so the
index file is how the UI finds the images. With no images, the button stays hidden.
