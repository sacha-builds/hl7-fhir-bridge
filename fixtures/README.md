# Demo message fixtures

Curated HL7 v2 messages that tell a small clinical story end-to-end. The
`bridge-replay` CLI streams them to the MLLP listener in filename order so the
viewer inbox fills up with a believable sequence:

| # | Message | Story |
| - | ------- | ----- |
| 01 | `ADT^A01` Jane Doe admit | First patient arrives (inpatient). |
| 02 | `ADT^A01` John Smith admit | Second patient arrives (emergency). |
| 03 | `ORU^R01` Lipid panel for Jane | Lab results — mostly normal, one high LDL. |
| 04 | `ORU^R01` CBC for John | Abnormal WBC (high), anemic on Hgb/Hct. |
| 05 | `ADT^A08` Jane update | Patient demographics update. |
| 06 | `ADT^A03` Jane discharge | Encounter closed, `period.end` populated. |

## Replay

```bash
# From the repo root, with the bridge running on localhost:2575:
bridge-replay fixtures/messages --delay 800

# Loop indefinitely for a live demo:
bridge-replay fixtures/messages --delay 1500 --loop --shuffle
```

## PHI

These are synthetic. No real patient data, no real MRNs, no real providers.
