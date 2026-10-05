# Amazon Price Tracker
Price tracker for Amazon items, currently there is only data on graphical processing units available, but a feature will be added for you to add your own url.

```
backend/    FastAPI API, MCP server, scraper, DB models and Alembic migrations
frontend/   Angular UI
docs/       architecture diagrams and ideas
```

## Backend

See [backend/README.md](backend/README.md).

## Frontend (Angular)

```bash
cd frontend
npm install
npm start    # http://localhost:4200, proxies /api to the backend
npm test
```
