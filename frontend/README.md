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

Sign-in goes through the backend: **Sign in** opens Cognito's hosted page, and the backend
keeps the session in an HttpOnly cookie, so the UI never holds a token. Each user's groups,
dashboard picks and background are saved to the API. Run the backend with the Cognito
settings in `backend/.env`; the pool already accepts `http://localhost:4200` as a callback.

## Backgrounds

Images in `public/backgrounds/` (`.webp`, `.avif`, `.jpg` or `.png`) are what the
change-background button picks from. `npm start` and `npm run build` regenerate the
folder's `index.json`, because hosts like S3 can't list a folder. Keep the images small:
WebP at 2560 px wide is plenty behind the dark overlay.

## Deploy

From `backend/`, `uv run nox -s deploy_ui` builds the UI, uploads it to the stack's S3
bucket and invalidates CloudFront. See [backend/README.md](../backend/README.md).
