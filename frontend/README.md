# Frontend

Angular 22 UI for the price tracker: a chart and table of price history, a sidebar for
adding products, and a Customize dialog for choosing what the dashboard shows, archiving,
restoring and deleting products.

## Commands

```bash
npm install
npm start      # http://localhost:4200; /api is proxied to the backend on :8000
npm test       # Vitest
npm run build  # output in dist/frontend/browser
```

The API needs the owner's token. On the first 401 the UI asks for it and keeps it in the
browser's localStorage; it is the `PT_API_TOKEN` value from `backend/.env`.

## Backgrounds

Images in `public/backgrounds/` (`.webp`, `.avif`, `.jpg` or `.png`) are what the
change-background button picks from. `npm start` and `npm run build` regenerate the
folder's `index.json`, because hosts like S3 can't list a folder. Keep the images small:
WebP at 2560 px wide is plenty behind the dark overlay.

## Deploy

From `backend/`, `uv run nox -s deploy_ui` builds the UI, uploads it to the stack's S3
bucket and invalidates CloudFront. See [backend/README.md](../backend/README.md).
