# Backend (FastAPI, Python 3.14)

Run everything from this directory.

```bash
uv sync --extra dev
cp .env.example .env                  # set PT_DATABASE_URL and PT_API_TOKEN, or export them
uv run alembic upgrade head           # create or update the schema
uv run fastapi dev                    # API on http://localhost:8000, docs at /docs
uv run python -m app.scraper.run      # scrape tracked products, save today's prices
uv run nox                            # ruff check + format --check, mypy --strict, pytest
uv run nox -s format                  # apply ruff fixes and formatting
```

After changing `app/db/models.py`: `uv run alembic revision --autogenerate -m "..."`,
review the generated file in `migrations/versions/`, then `alembic upgrade head`.

## Authentication

The app has one owner and one token. Every call to `/api` and `/mcp` must send
`Authorization: Bearer <PT_API_TOKEN>`; `/health` stays open for probes. The UI asks for the
token on its first 401 and keeps it in the browser's localStorage. MCP clients send it as a
header, for example in Claude Code:

```bash
claude mcp add --transport http price-tracker <url>/mcp --header "Authorization: Bearer <token>"
```

To rotate the token, change it (in `.env`, or in SSM when deployed) and enter the new one
in the UI.

## Deploy to AWS (optional)

`template.yaml` deploys the API and MCP server as one Lambda behind an HTTP API with SAM.
The Lambda Web Adapter layer starts uvicorn through `run.sh`. The same stack serves the UI
from a private S3 bucket through CloudFront, which also routes `/api/*` to the HTTP API, so
the UI and the API share one origin and need no CORS. The scraper stays on your own
machine because Amazon blocks requests from AWS IP ranges. Any Postgres the Lambda can
reach works as the database.

### One-time setup

- Install the AWS CLI and the SAM CLI, and sign in with a deploy user (not root).
- Store the database URL and the API token as SSM SecureStrings. The function reads them
  at cold start through `PT_DATABASE_URL_PARAM` and `PT_API_TOKEN_PARAM`, so neither
  appears in the Lambda configuration. If one is missing, the function fails to start.
  With a connection pooler, use its transaction mode.
  ```bash
  aws ssm put-parameter --name /price-tracker/database-url --type SecureString --value '<url>'
  aws ssm put-parameter --name /price-tracker/api-token --type SecureString --value '<token>'
  ```
- Build (below), then `sam deploy --guided`. It saves your answers to `samconfig.toml`.

### Build and redeploy

```bash
uv run nox                         # lint, types, tests
uv run alembic upgrade head        # if a migration was added; the Lambda never migrates
rm -rf build
uv export --frozen --no-dev --no-hashes --no-editable -o requirements.txt
uv pip install -r requirements.txt --target build --python-platform aarch64-manylinux_2_34 --python-version 3.14 --refresh-package gpu-price-tracker
cp run.sh build/
sam deploy
```

- The build skips `sam build`, which would zip the whole directory, `.env` included.
  `--no-editable` installs `app` as a package, so `build/` holds only code and dependencies.
- `manylinux_2_34` matches the python3.14 runtime (Amazon Linux 2023); psycopg has no arm64
  wheels for the default `manylinux2014` tag.
- `--refresh-package` makes uv rebuild this project. Without it, uv reuses its cached wheel
  until `pyproject.toml` changes, and code changes never reach the Lambda.
- `run.sh` must keep LF line endings: check with `git ls-files --eol run.sh`.
- In Git Bash on Windows, prefix the `aws ssm` commands with `MSYS_NO_PATHCONV=1`, or the
  parameter name is rewritten as a Windows path.

### Upload the UI

After the first deploy, and whenever the frontend changes (from `frontend/`):

```bash
npm run build
aws s3 sync dist/frontend/browser s3://<UiBucketName> --delete
aws cloudfront create-invalidation --distribution-id <CdnId> --paths "/*"
```

`UiBucketName` and `CdnId` are stack outputs. The invalidation makes CloudFront fetch the new
`index.html` instead of serving its cached copy for up to a day. The `/api/*` behavior
forwards `Authorization` and never caches, since responses depend on the token.

### Check and logs

```bash
sam list stack-outputs --stack-name <stack>          # API and UI URLs
curl <url>health/ready                                # 200 = parameter read and DB reachable
sam logs -n ApiFunction --stack-name <stack> --tail
```

`events/` holds HTTP API events for invoking the function directly, bypassing API Gateway.
The `*-no-token` events should still get a 401, because the app checks the token itself:

```bash
sam remote invoke ApiFunction --stack-name <stack> --event-file events/health.json
```

After changing the parameter (`put-parameter ... --overwrite`), running instances keep the
old value until their next cold start. Any configuration update forces one:

```bash
fn=$(aws cloudformation describe-stack-resource --stack-name <stack> --logical-resource-id ApiFunction --query StackResourceDetail.PhysicalResourceId --output text)
aws lambda update-function-configuration --function-name "$fn" --description "reload config"
```

### Tear down

`sam delete --stack-name <stack>` removes the function, API, role and log group. The
parameter is not part of the stack: `aws ssm delete-parameter --name /price-tracker/database-url`.
