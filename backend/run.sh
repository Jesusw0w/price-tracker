#!/bin/bash
PYTHONPATH=$PYTHONPATH:$LAMBDA_RUNTIME_DIR exec python -m uvicorn --port="$PORT" app.main:app
