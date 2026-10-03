import atexit
import logging
import queue
import time
import uuid
from contextvars import ContextVar
from logging.handlers import QueueHandler, QueueListener
from typing import Any

from starlette.datastructures import MutableHeaders
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

request_id: ContextVar[str] = ContextVar("request_id", default="-")

access_log = logging.getLogger("app.access")

_base_factory = logging.getLogRecordFactory()


def _record_with_request_id(*args: Any, **kwargs: Any) -> logging.LogRecord:  # noqa: ANN401  # LogRecord's own signature
    record = _base_factory(*args, **kwargs)
    # Read here, on the calling task, not in the handler thread that has no context
    record.request_id = request_id.get()
    return record


def setup_logging(level: int = logging.INFO) -> None:
    """Log via a background thread so a slow stderr never blocks a request."""
    logging.setLogRecordFactory(_record_with_request_id)

    stream = logging.StreamHandler()
    stream.setFormatter(
        logging.Formatter(
            "%(asctime)s.%(msecs)03d %(levelname)s [%(request_id)s] %(name)s: "
            "%(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
    )
    log_queue: queue.SimpleQueue[logging.LogRecord] = queue.SimpleQueue()
    listener = QueueListener(log_queue, stream)
    listener.start()
    atexit.register(listener.stop)

    root = logging.getLogger()
    root.addHandler(QueueHandler(log_queue))
    root.setLevel(level)
    # Replaced by AccessLog, which adds the request id and duration
    logging.getLogger("uvicorn.access").disabled = True


class AccessLog:
    """Log every HTTP call and unhandled error under a per-request id."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        rid = uuid.uuid4().hex
        token = request_id.set(rid)
        start = time.perf_counter()
        status = 500
        started = False

        async def send_with_id(message: Message) -> None:
            nonlocal status, started
            if message["type"] == "http.response.start":
                status, started = message["status"], True
                MutableHeaders(scope=message).append("X-Request-ID", rid)
            await send(message)

        try:
            await self.app(scope, receive, send_with_id)
        except Exception:
            access_log.exception("Unhandled error")
            if started:
                raise
            # Answered here, or Starlette and uvicorn log the traceback again, sans id
            response = JSONResponse(
                {"detail": "Internal Server Error"},
                status_code=500,
                headers={"X-Request-ID": rid},
            )
            await response(scope, receive, send)
        finally:
            level = (
                logging.ERROR
                if status >= 500
                else logging.WARNING
                if status >= 400
                else logging.INFO
            )
            access_log.log(
                level,
                "%s %s %d %.1fms",
                scope["method"],
                scope["path"],
                status,
                (time.perf_counter() - start) * 1000,
            )
            request_id.reset(token)
