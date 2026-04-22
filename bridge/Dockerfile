# Build context must be the REPO ROOT (not bridge/), so the Dockerfile can
# copy both the Python package and the top-level fixtures/ used by the demo
# seeder in production.
#
#   docker build -f bridge/Dockerfile .

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY bridge/pyproject.toml bridge/README.md ./
COPY bridge/src ./src

RUN uv pip install --system --no-cache -e .

# Demo fixtures used by the /v2/demo/random endpoint and the background
# seeder. Path matches the BRIDGE_DEMO_FIXTURES_PATH default.
COPY fixtures/messages /app/fixtures/messages

EXPOSE 2575 8000

CMD ["python", "-m", "bridge.main"]
