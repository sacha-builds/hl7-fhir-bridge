# HL7 v2 → FHIR Interoperability Bridge

An HL7 v2 → FHIR R4 interoperability bridge with a live clinical viewer. Ingests v2 messages over MLLP, maps them to FHIR resources conforming to US Core profiles, persists to a HAPI FHIR server, and streams the results to a Vue 3 clinical viewer in real time.

> **Status:** end-to-end working — MLLP in, conditional-create FHIR out, live Vue viewer with message inbox, patient chart, and metrics. See [Roadmap](#roadmap) for what's next.

## Why this exists

Every major US healthcare integration role involves bridging legacy HL7 v2 pipelines to modern FHIR APIs. Hospital EHRs (Epic, Cerner, Meditech) emit v2 over MLLP. Modern digital health apps, analytics platforms, payer FHIR APIs (CMS Interoperability Rule), and public health reporting pipelines all speak FHIR. Companies like **Redox**, **Health Gorilla**, **1upHealth**, **Lyniate/Rhapsody**, and **Mirth Connect** exist to sit in the middle. This project demonstrates the same pattern end-to-end, with production-realistic choices at every layer.

## Standards referenced

- **HL7 v2.5.1** — ADT, ORU, ORM message types. [hl7.org/implement/standards/product_brief.cfm?product_id=185](https://www.hl7.org/implement/standards/product_brief.cfm?product_id=185)
- **HL7 v2-to-FHIR Implementation Guide** — authoritative mapping spec. [build.fhir.org/ig/HL7/v2-to-fhir](https://build.fhir.org/ig/HL7/v2-to-fhir/)
- **FHIR R4** — [hl7.org/fhir/R4](https://hl7.org/fhir/R4/)
- **US Core 6.1.0** — USCDI-aligned profiles. [hl7.org/fhir/us/core](https://hl7.org/fhir/us/core/)
- **MLLP** — Minimal Lower Layer Protocol for v2 transport
- **LOINC** (labs) and **SNOMED CT** (problems) for terminology
- **SMART on FHIR** (stretch goal) — [hl7.org/fhir/smart-app-launch](https://hl7.org/fhir/smart-app-launch/)

## Architecture

```
┌─────────────────────┐       ┌────────────────────────────────────────┐
│  Sample generators  │       │         Bridge Service (Python)        │
│  • Synthea          │       │                                        │
│  • Golden fixtures  ├──MLLP▶│  MLLP Listener                         │
│  • Replay CLI       │ :2575 │      │                                 │
└─────────────────────┘       │      ▼                                 │
                              │  v2 Parser (hl7apy)                    │
                              │      │                                 │
                              │      ▼                                 │
                              │  Router ──▶ Mappers (per message type) │
                              │               │                        │
                              │               ▼                        │
                              │       Terminology (LOINC/SNOMED)       │
                              │               │                        │
                              │               ▼                        │
                              │       FHIR Validator + US Core         │
                              │               │                        │
                              │               ▼                        │
                              │       Audit log / metrics              │
                              └────────────┬───────────────────────────┘
                                           │ REST
                                           ▼
                              ┌────────────────────────────┐
                              │  HAPI FHIR Server + Postgres│
                              └────────────┬───────────────┘
                                           │ REST + WS
                                           ▼
                              ┌────────────────────────────┐
                              │  Viewer UI (Vue 3 + Vite)  │
                              │  • Split pane v2 ↔ FHIR    │
                              │  • Patient chart           │
                              │  • Metrics dashboard       │
                              └────────────────────────────┘
```

See [docs/architecture.md](docs/architecture.md) for a deeper walkthrough.

## Tech stack

| Layer       | Choice                                          | Why                                                                 |
| ----------- | ----------------------------------------------- | ------------------------------------------------------------------- |
| Bridge      | Python 3.12 + FastAPI + `hl7apy` + `fhir.resources` | Richest HL7 v2 tooling in any non-Java language; mature Pydantic-based FHIR models. |
| FHIR server | HAPI FHIR (official Docker image) + Postgres    | Reference open-source FHIR server; what hospitals and HIEs actually run. |
| Viewer UI   | Vue 3 + Vite + TypeScript + Pinia               | Fast developer experience, strong typing, live WebSocket updates.   |
| Orchestration | Docker Compose                                | One command brings the whole system up.                             |
| CI          | GitHub Actions                                  | Lint, type-check, test on every push.                               |

## Quick start

> Requires Docker and Docker Compose.

```bash
docker compose up --build
```

Once everything is up:

| Service          | URL                               |
| ---------------- | --------------------------------- |
| Viewer UI        | http://localhost:5173             |
| HAPI FHIR server | http://localhost:8080/fhir        |
| Bridge API       | http://localhost:8000             |
| MLLP ingest      | `tcp://localhost:2575`            |

## Demo

The repo ships with a handful of curated HL7 v2 fixtures that tell a small
clinical story (two admits, two lab panels, one demographics update, one
discharge). Stream them through the bridge and watch the viewer:

```bash
# Terminal 1 — full stack
docker compose up --build

# Terminal 2 — replay the fixtures
make replay
# …or, for a live-feeling demo:
make demo        # loops + shuffles + 1.5s pacing

# Reset between runs
make reset
```

Then open:

- [http://localhost:5173](http://localhost:5173) — **Inbox** fills up live over WebSocket; click any row for the split-pane v2 ↔ FHIR view.
- [http://localhost:5173/patients](http://localhost:5173/patients) — patient list read from HAPI FHIR through the bridge proxy.
- [http://localhost:5173/metrics](http://localhost:5173/metrics) — throughput, accept rate, resources written, validation-issue counts.

## Deployment topology

Two modes, same codebase:

- **Local / reviewer demo** — `docker compose up`. Full self-contained stack: HAPI FHIR + Postgres + bridge + viewer.
- **Deployed showcase** — bridge on AWS EC2 (cohabiting with the author's Provender app, ~150 MB footprint), viewer shipped as a static Vue 3 SPA to Cloudflare Pages, FHIR hosted on Medplum cloud's Developer plan. The bridge's `BRIDGE_FHIR_BASE_URL` env var swaps the target with zero code changes. Mirrors real-world production — no one self-hosts HAPI in production; they use HealthLake / Google Cloud Healthcare / Medplum.

## Running the official HL7 FHIR Validator

For serious conformance checks (not just schema validation), run the
HL7-blessed validator against the mapper outputs. Requires Java 11+; the
~150 MB validator jar is cached under `tmp/` after the first run.

```bash
make fhir-validate
```

The report lands in `tmp/fhir-validation-report.json`. This is the same
validator used by the HAPI reference implementation and ONC's Inferno test
suite.

## Roadmap

- [x] **Phase 0** — Repo scaffolding, Docker Compose, CI
- [x] **Phase 1** — MLLP listener, ADT^A01 → Patient + Encounter, golden-file tests
- [x] **Phase 2** — ADT^A03/A08, ORU^R01 → Observation + DiagnosticReport, LOINC, US Core validation
- [x] **Phase 3** — Vue viewer: split-pane v2/FHIR, clinical chart, live WS updates
- [x] **Phase 4** — Replay CLI, curated demo fixtures, metrics endpoint + dashboard, Makefile, FHIR Validator integration
- [ ] **Phase 5 (stretch)** — Synthea-generated traffic, ONC Inferno conformance report, SMART on FHIR launch, CDS Hooks, FHIR Subscriptions, Bulk Data export

## Repo layout

```
.
├── bridge/              # Python HL7 v2 → FHIR service
│   ├── src/bridge/      # mllp, parsers, mappers, fhir_client, store, metrics, validators
│   ├── tests/           # unit + integration + golden fixtures (49+ tests)
│   └── scripts/replay.py # bridge-replay CLI entry point
├── viewer/              # Vue 3 clinical viewer (Inbox, Patient chart, Metrics)
├── fixtures/messages/   # Curated demo v2 messages (story-shaped)
├── docs/                # Architecture & design notes
├── Makefile             # up, test, lint, replay, demo, reset, fhir-validate
├── docker-compose.yml
└── .github/workflows/   # CI pipelines
```

## Acknowledgements

- **HL7 International** for the v2, FHIR, and v2-to-FHIR IG specifications that made this project possible.
- **HAPI FHIR** for the reference FHIR R4 server used in local dev.
- **hl7apy** for a solid Python v2 parser.
- **fhir.resources** for Pydantic-typed FHIR R4 models.
- **Medplum** for a genuinely free FHIR cloud tier that makes portfolio projects like this publicly demo-able.

## License

MIT
