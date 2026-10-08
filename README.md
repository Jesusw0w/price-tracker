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
