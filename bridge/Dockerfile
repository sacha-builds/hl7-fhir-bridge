FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml README.md ./
COPY src ./src

RUN uv pip install --system --no-cache -e .

EXPOSE 2575 8000

CMD ["python", "-m", "bridge.main"]
