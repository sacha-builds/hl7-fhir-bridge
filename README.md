# HL7 v2 → FHIR Interoperability Bridge

An HL7 v2 → FHIR R4 interoperability bridge with a live clinical viewer. Ingests v2 messages over MLLP, maps them to FHIR resources conforming to US Core profiles, persists to a HAPI FHIR server, and streams the results to a Vue 3 clinical viewer in real time.

> **Status:** Phase 0 — scaffolding. See [Roadmap](#roadmap).

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

## Roadmap

- [x] **Phase 0** — Repo scaffolding, Docker Compose, CI
- [x] **Phase 1** — MLLP listener, ADT^A01 → Patient + Encounter, golden-file tests
- [x] **Phase 2** — ADT^A03/A08, ORU^R01 → Observation + DiagnosticReport, LOINC, US Core validation
- [ ] **Phase 3** — Vue viewer: split-pane v2/FHIR, clinical chart, live WS updates
- [ ] **Phase 4** — Synthea integration, Inferno conformance, metrics dashboard, audit log viewer
- [ ] **Phase 5 (stretch)** — SMART on FHIR launch, CDS Hooks, FHIR Subscriptions, Bulk Data export

## Repo layout

```
.
├── bridge/              # Python HL7 v2 → FHIR service
├── viewer/              # Vue 3 clinical viewer
├── fixtures/            # Golden v2 messages + expected FHIR output
├── docs/                # Architecture & design notes
├── docker-compose.yml
└── .github/workflows/   # CI pipelines
```

## License

MIT
