"""Development automation sessions."""

import json
import shutil
import tomllib
from pathlib import Path
from typing import Final

import nox

nox.options.sessions = ["lint", "typecheck", "tests"]
nox.options.default_venv_backend = "uv"

PYTHON_VERSION: Final[str] = "3.14"
SOURCES: Final[tuple[str, ...]] = ("app", "migrations", "tests", "noxfile.py")

BUILD: Final[Path] = Path("build")
UI: Final[Path] = Path("../frontend")
# Lambda's python3.14 runtime is Amazon Linux 2023 on arm64; psycopg has no arm64
# wheels for the older manylinux2014 tag
LAMBDA_PLATFORM: Final[str] = "aarch64-manylinux_2_34"


@nox.session(python=PYTHON_VERSION)
def lint(session: nox.Session) -> None:
    """Run ruff linter and formatter checks."""
    session.install("ruff")
    session.run("ruff", "check", *SOURCES)
    session.run("ruff", "format", "--check", *SOURCES)


@nox.session(python=PYTHON_VERSION)
def format(session: nox.Session) -> None:  # noqa: A001  # nox exposes the session name
    """Apply ruff formatting and safe autofixes."""
    session.install("ruff")
    session.run("ruff", "check", "--fix", *SOURCES)
    session.run("ruff", "format", *SOURCES)


@nox.session(python=PYTHON_VERSION)
def typecheck(session: nox.Session) -> None:
    """Run mypy strict type checking."""
    session.install("-e", ".[dev]")
    session.run("mypy", "--strict", *SOURCES)


@nox.session(python=PYTHON_VERSION)
def tests(session: nox.Session) -> None:
    """Run the pytest suite."""
    session.install("-e", ".[dev]")
    session.run("pytest", *session.posargs)


@nox.session(python=False)
def deploy(session: nox.Session) -> None:
    """Check, build and deploy the API and MCP Lambda. Extra args go to sam deploy."""
    session.run("nox", external=True)
    shutil.rmtree(BUILD, ignore_errors=True)
    # Not sam build: it would zip this whole directory, .env included
    session.run(
        "uv", "export", "--frozen", "--no-dev", "--no-hashes", "--no-editable",
        "-o", "requirements.txt", external=True,
    )  # fmt: skip
    session.run(
        "uv", "pip", "install", "-r", "requirements.txt", "--target", str(BUILD),
        "--python-platform", LAMBDA_PLATFORM, "--python-version", PYTHON_VERSION,
        # uv reuses its cached wheel of this project until pyproject.toml changes
        "--refresh-package", "gpu-price-tracker",
        external=True,
    )  # fmt: skip
    shutil.copy("run.sh", BUILD)
    session.run("sam", "deploy", *session.posargs, external=True)


@nox.session(python=False)
def deploy_ui(session: nox.Session) -> None:
    """Build the UI, upload it to the stack's bucket and invalidate CloudFront."""
    config = tomllib.loads(Path("samconfig.toml").read_text())
    params = config["default"]["deploy"]["parameters"]
    region = ["--region", params["region"]]
    raw = session.run(
        "aws", "cloudformation", "describe-stacks",
        "--stack-name", params["stack_name"],
        "--query", "Stacks[0].Outputs", "--output", "json", *region,
        external=True, silent=True,
    )  # fmt: skip
    outputs = {o["OutputKey"]: o["OutputValue"] for o in json.loads(str(raw))}

    session.run("npm", "--prefix", str(UI), "run", "build", external=True)
    session.run(
        "aws", "s3", "sync", str(UI / "dist/frontend/browser"),
        f"s3://{outputs['UiBucketName']}", "--delete", *region,
        external=True,
    )  # fmt: skip
    # Without it CloudFront serves its cached index.html, pointing at deleted bundles
    session.run(
        "aws", "cloudfront", "create-invalidation",
        "--distribution-id", outputs["CdnId"], "--paths", "/*",
        external=True,
    )  # fmt: skip
