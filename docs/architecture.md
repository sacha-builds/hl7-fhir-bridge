# Architecture

## Overview

The bridge sits between two worlds:

- **Upstream**: hospital EHRs / labs / HIEs emitting HL7 v2 messages over MLLP.
- **Downstream**: a FHIR R4 server (local HAPI for dev, Medplum cloud in production) and any FHIR-native clients (the viewer UI, analytics pipelines, third-party apps).

## Component responsibilities

### Bridge service (`bridge/`)

Python 3.12 + FastAPI + hl7apy + `fhir.resources`.

| Module               | Responsibility                                                              |
| -------------------- | --------------------------------------------------------------------------- |
| `bridge.mllp`        | TCP server implementing the MLLP framing protocol (start `0x0B`, end `0x1C 0x0D`). Accepts inbound v2 messages and returns ACK/NACK. |
| `bridge.parsers`     | Thin wrappers over `hl7apy` for parsing v2 segments into typed objects.     |
| `bridge.mappers`     | Per-message-type transformers to FHIR (e.g. `ADT^A01` → `Patient` + `Encounter`). Follows the HL7 v2-to-FHIR IG. |
| `bridge.fhir_client` | HTTP client for the FHIR REST API (`POST`, `PUT`, conditional create).      |
| `bridge.telemetry`   | Structured logging (structlog) + Prometheus-style counters.                 |
| `bridge.main`        | FastAPI app (health, metrics, replay endpoints) + MLLP lifecycle.           |

### FHIR server

- **Local dev:** HAPI FHIR R4 (official Docker image), Postgres-backed, via docker-compose.
- **Production:** Medplum cloud (Developer plan). Swappable via `BRIDGE_FHIR_BASE_URL` env var with no code changes.

### Viewer (`viewer/`)

Vue 3 + Vite + TypeScript + Pinia. Built as a static SPA so it can ship to Cloudflare Pages / Vercel / Netlify in production. Connects to the bridge (`/`, `/health`, WebSocket for live message events) and to the FHIR server (direct REST reads for patient charts).

## Message flow — `ADT^A01` (patient admit)

```
1. Hospital sends v2 over MLLP:
   MSH|^~\&|EPIC|HOSP|...|ADT^A01|...
   PID|1||12345^^^HOSP^MR||DOE^JANE^E||19800101|F|...
   PV1|1|I|2000^2012^01||...|12345^SMITH^JOHN^A|...

2. Bridge MLLP listener accepts, frames off the message, parses via hl7apy.

3. Router dispatches to the ADT^A01 mapper.

4. Mapper emits:
   - Patient  (identifier=MR, name, gender, birthDate)
   - Encounter (class=inpatient, status=in-progress, subject→Patient)

5. FHIR client writes with conditional create (idempotent on identifier).

6. Bridge returns MLLP ACK to the sender.

7. Viewer receives a WebSocket event; refreshes the patient list.
```

## Deployment topologies

### Local / demo mode

```
docker compose up
```

Brings up: Postgres → HAPI FHIR → Bridge → Viewer. One command, self-contained.

### Production / showcase mode

```
[Cloudflare Pages]                [AWS EC2 free tier]            [Medplum cloud]
 ┌────────────┐    HTTPS/WSS     ┌────────────────┐   HTTPS    ┌─────────────┐
 │  Viewer    │◀────────────────▶│  Bridge + MLLP │───────────▶│ FHIR server │
 │  (Vue SPA) │                  │  (Python)      │            │             │
 └────────────┘                  └────────────────┘            └─────────────┘
      │                                  ▲
      │  direct FHIR reads (HTTPS)       │
      └──────────────────────────────────┼─────────────────────▶
                                         │
                                   inbound v2 over MLLP
                                   (test harness / replay)
```

- Bridge is configured via `BRIDGE_FHIR_BASE_URL` to point at Medplum.
- Viewer is built with `VITE_FHIR_BASE_URL` baked in at build time.
- Bridge co-tenants with the Provender inventory app on the existing EC2 instance.

## Non-functional concerns

- **Idempotency.** All FHIR writes use conditional create on natural identifiers so that replaying a v2 feed doesn't duplicate resources.
- **Observability.** Structured JSON logs; every inbound message gets a correlation ID that propagates through parse, map, validate, write.
- **Conformance.** Outbound resources are validated against US Core profiles. CI publishes an Inferno conformance report.
- **Safety.** No real PHI in this repo. Fixtures are synthetic (Synthea-generated or hand-crafted).

## Out of scope for v1

- Outbound FHIR → v2 (reverse direction). Straightforward to add; demand is asymmetric.
- HL7 CDA / C-CDA documents. Different beast; not needed for the core use case.
- Real EHR vendor integration (Epic App Orchard, Cerner CODE). Requires paid dev credentials.
