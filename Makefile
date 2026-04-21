.PHONY: help up down logs bridge-test bridge-lint bridge-format bridge-type viewer-build viewer-test test lint replay demo reset fhir-validate

help:
	@echo "Targets:"
	@echo "  up               - docker compose up --build"
	@echo "  down             - docker compose down"
	@echo "  logs             - tail bridge logs"
	@echo "  bridge-test      - run bridge pytest"
	@echo "  bridge-lint      - run ruff + mypy on bridge"
	@echo "  bridge-format    - auto-format bridge"
	@echo "  viewer-build     - type-check + production build of viewer"
	@echo "  test             - run both bridge and viewer checks"
	@echo "  replay           - stream fixtures/messages to MLLP on :2575"
	@echo "  demo             - looped, paced replay suitable for live demos"
	@echo "  reset            - clear the bridge inbox and metrics"
	@echo "  fhir-validate    - run the official HL7 FHIR Validator on sample outputs (Java required)"

up:
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f bridge

bridge-test:
	cd bridge && .venv/bin/pytest

bridge-lint:
	cd bridge && .venv/bin/ruff check . && .venv/bin/ruff format --check . && .venv/bin/mypy

bridge-format:
	cd bridge && .venv/bin/ruff check --fix . && .venv/bin/ruff format .

viewer-build:
	cd viewer && npm run type-check && npm run format:check && npm run build

viewer-test: viewer-build

test: bridge-lint bridge-test viewer-build

lint: bridge-lint
	cd viewer && npm run format:check && npm run type-check

replay:
	cd bridge && .venv/bin/bridge-replay ../fixtures/messages --delay 800

demo:
	cd bridge && .venv/bin/bridge-replay ../fixtures/messages --delay 1500 --loop --shuffle

reset:
	curl -X DELETE http://localhost:8000/v2/messages

# Run the official HL7 FHIR Validator CLI against mapper outputs dumped to tmp/.
# Requires Java 11+. Downloads validator_cli.jar on first run (~150 MB, cached).
fhir-validate:
	@mkdir -p tmp
	@if [ ! -f tmp/validator_cli.jar ]; then \
		echo "downloading validator_cli.jar..."; \
		curl -L -o tmp/validator_cli.jar https://github.com/hapifhir/org.hl7.fhir.core/releases/latest/download/validator_cli.jar; \
	fi
	@echo "dumping golden FHIR outputs..."
	@cd bridge && .venv/bin/python -c "\
import json, pathlib; \
from bridge.mappers import map_adt_a01, map_adt_a03, map_adt_a08, map_oru_r01; \
out = pathlib.Path('../tmp/fhir'); out.mkdir(parents=True, exist_ok=True); \
cases = [('adt_a01', map_adt_a01), ('adt_a03', map_adt_a03), ('adt_a08', map_adt_a08), ('oru_r01', map_oru_r01)]; \
[\
  [(out / f'{name}_{i}_{mr.resource.__class__.__name__}.json').write_text(mr.resource.model_dump_json(by_alias=True, exclude_none=True, indent=2)) \
   for i, mr in enumerate(fn(pathlib.Path(f'tests/fixtures/{name}_simple.hl7').read_text()))] \
  for name, fn in cases \
]"
	java -jar tmp/validator_cli.jar tmp/fhir/*.json -version 4.0 -output tmp/fhir-validation-report.json
	@echo "report → tmp/fhir-validation-report.json"
