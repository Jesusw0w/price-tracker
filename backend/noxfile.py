"""Development automation sessions."""

from typing import Final

import nox

nox.options.sessions = ["lint", "typecheck", "tests"]
nox.options.default_venv_backend = "uv"

PYTHON_VERSION: Final[str] = "3.14"
SOURCES: Final[tuple[str, ...]] = ("app", "migrations", "tests", "noxfile.py")


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
