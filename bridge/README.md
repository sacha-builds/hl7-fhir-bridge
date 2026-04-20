# Bridge service

HL7 v2 → FHIR R4 translation service. Accepts v2 messages over MLLP, maps them to FHIR resources per the [HL7 v2-to-FHIR IG](https://build.fhir.org/ig/HL7/v2-to-fhir/), validates against US Core profiles, and POSTs to a HAPI FHIR server.

## Local development

Requires Python 3.12+. Recommended: [uv](https://github.com/astral-sh/uv).

```bash
cd bridge
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"

# Run the service
python -m bridge.main

# Tests
pytest

# Lint + type check
ruff check .
ruff format --check .
mypy
```

## Layout

```
bridge/
├── src/bridge/
│   ├── main.py          # entrypoint (MLLP listener + FastAPI app)
│   ├── config.py        # pydantic-settings config
│   ├── mllp/            # MLLP TCP server
│   ├── parsers/         # HL7 v2 parsing (hl7apy wrappers)
│   ├── mappers/         # v2 → FHIR mapping per message type
│   ├── fhir_client/     # HAPI FHIR REST client
│   └── telemetry/       # structured logging + metrics
└── tests/
    ├── unit/
    └── integration/
```
