FROM python:3.11-alpine

COPY --from=ghcr.io/astral-sh/uv:0.12.15 /uv /usr/local/bin/uv

ENV PYTHONUNBUFFERED=1
# Install dependencies into the system Python instead of a virtualenv
ENV UV_PROJECT_ENVIRONMENT=/usr/local
ENV UV_COMPILE_BYTECODE=1

COPY pyproject.toml /
COPY uv.lock /
RUN uv sync --locked --inexact --no-dev --no-install-project

COPY server.py /
COPY docker-entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

COPY ./api/ /api/
