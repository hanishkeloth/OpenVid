#!/bin/sh
set -eu
exec uvicorn app.webapp:app --host 0.0.0.0 --port "${PORT:-7795}" --workers 1
