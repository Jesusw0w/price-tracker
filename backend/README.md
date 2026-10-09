# Backend (FastAPI, Python 3.14)

Run everything from this directory.

```bash
uv sync --extra dev
cp .env.example .env                  # set the database, token and Cognito values, or export them
uv run alembic upgrade head           # create or update the schema
uv run fastapi dev                    # API on http://localhost:8000, docs at /docs
uv run python -m app.scraper.run      # scrape tracked products, save today's prices
uv run nox                            # ruff check + format --check, mypy --strict, pytest
uv run nox -s format                  # apply ruff fixes and formatting
uv run nox -s deploy                  # checks, then build and deploy the Lambda (AWS)
uv run nox -s deploy_ui               # build the UI, upload it, invalidate CloudFront (AWS)
```

Plain `uv run nox` only checks; the deploy sessions run only when named.

After changing `app/db/models.py`: `uv run alembic revision --autogenerate -m "..."`,
review the generated file in `migrations/versions/`, then `alembic upgrade head`.

## Authentication

Users sign in with a Cognito user pool, created by the stack. Accounts are invite only.

- **UI and `/api`:** `/api/auth/login` sends the browser to Cognito's hosted sign-in page.
  Cognito redirects to `/api/auth/callback`, and the backend exchanges the code (with PKCE)
  and stores a session in the `sessions` table. The browser holds only a random session id,
  in an `HttpOnly`, `Secure`, `SameSite=Strict` cookie, so page scripts can't read it and
  other sites can't send it. Sessions last `PT_SESSION_DAYS` (14). `/health` stays open.
- **What users see:** your own products, plus products other users made public. Only the
  owner can archive, delete or share a product. Products start private. Each user's groups,
  dashboard picks and background are saved in `user_settings`.
- **`/mcp`:** MCP clients can't do a browser login, so they still send
  `Authorization: Bearer <PT_API_TOKEN>`. They act as the user `PT_OWNER_SUB`; leave it
  empty to turn `/mcp` off. The token no longer opens `/api`.

```bash
claude mcp add --transport http price-tracker <url>/mcp --header "Authorization: Bearer <token>"
```

### Managing users

Get the pool id from `sam list stack-outputs` (`UserPoolId`).

```bash
# Invite: Cognito emails a temporary password, and the first sign-in sets a new one
aws cognito-idp admin-create-user --user-pool-id <pool> --username friend@example.com \
  --user-attributes Name=email,Value=friend@example.com Name=email_verified,Value=true
# A user's sub, e.g. for PT_OWNER_SUB or the migration below
aws cognito-idp admin-get-user --user-pool-id <pool> --username you@example.com \
  --query "UserAttributes[?Name=='sub'].Value" --output text
aws cognito-idp admin-disable-user --user-pool-id <pool> --username friend@example.com
```

Disabling a user stops new sign-ins. Sessions that are already open last until they expire,
so to lock someone out right away, also delete their sessions:
`DELETE FROM sessions WHERE user_sub = '<sub>';`

Cognito's built-in email sender allows about 50 emails a day, which is plenty for invites.

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
- First deploy: `uv run nox -s deploy -- --guided`. It saves your answers to
  `samconfig.toml`. After that, `uv run nox -s deploy_ui` uploads the UI.
- `PublicUrl` (in `parameter_overrides` in `samconfig.toml`) must be the `UiUrl` output
  without the trailing slash. A brand-new stack doesn't know it yet: deploy once, copy
  `UiUrl` into the parameter, and deploy again.

### Adding sign-in to an existing deployment

The migration needs an owner for the products that already exist. That owner is a Cognito
user, and the pool comes from the deploy. So the order matters, and the API returns errors
between the deploy and the migration:

1. `uv run nox -s deploy`. This creates the user pool and ships the new code.
2. Invite yourself (see *Managing users*), then read your `sub`.
3. Back up the database, then run `uv run alembic -x owner=<your sub> upgrade head`.
4. Put `OwnerSub=<your sub>` in `parameter_overrides`, then `uv run nox -s deploy` to turn
   `/mcp` back on, and `uv run nox -s deploy_ui`.
5. Copy `CognitoDomain` and `CognitoClientId` from the outputs into `.env` for local runs.

### Build and redeploy

```bash
uv run alembic upgrade head    # only if a migration was added; the Lambda never migrates
uv run nox -s deploy           # lint, types, tests, then build and sam deploy
uv run nox -s deploy_ui        # npm build, sync to the bucket, invalidate CloudFront
```

`deploy` passes extra arguments to `sam deploy`, for example
`uv run nox -s deploy -- --no-confirm-changeset`. `deploy_ui` reads the stack name and
region from `samconfig.toml`, which the first guided deploy writes.

Notes on the build in `noxfile.py`:

- The build skips `sam build`, which would zip the whole directory, `.env` included.
  `--no-editable` installs `app` as a package, so `build/` holds only code and dependencies.
- `manylinux_2_34` matches the python3.14 runtime (Amazon Linux 2023); psycopg has no arm64
  wheels for the default `manylinux2014` tag.
- `--refresh-package` makes uv rebuild this project. Without it, uv reuses its cached wheel
  until `pyproject.toml` changes, and code changes never reach the Lambda.
- `run.sh` must keep LF line endings: check with `git ls-files --eol run.sh`.
- The invalidation in `deploy_ui` matters: without it CloudFront keeps serving its cached
  `index.html`, which points at bundles the sync just deleted.
- In Git Bash on Windows, prefix the `aws ssm` commands with `MSYS_NO_PATHCONV=1`, or the
  parameter name is rewritten as a Windows path.

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
The user pool is retained, so a stack delete never deletes accounts. Delete it from the
Cognito console when you really mean to.
