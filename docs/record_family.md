# TraceLab Record Family

TraceLab v0.1 writes a simulation-only record chain:

1. `experiment_request.json` records the research request.
2. `run_plan.json` records the proposed simulated plan.
3. `approval_record.json` records scoped approval for simulation only.
4. `adapter_capability_manifest.json` records what the adapter can and cannot do.
5. `dry_run_record.json` records non-executing dry-run status.
6. `adapter_action_record.json` records the simulated action.
7. `telemetry_manifest.json` records telemetry artifact paths and hashes.
8. `validation_record.json` records operational simulation checks.
9. `lab_run_record.json` records the simulated run summary.
10. `evidence_packet_manifest.json` records included evidence, gaps, and not-proven claims.
11. `review_record.json` records that human review is still required.
12. `neuml_handoff_manifest.json` records future ingestion candidates.

These records preserve traceability. They do not prove scientific truth or promote durable claims.


## Overwrite boundary

TraceLab v0.1 refuses to create a new simulated run inside a non-empty output directory. Existing run records and telemetry are evidence artifacts, so the demo workflow must not silently overwrite them. Users should choose a new run directory or explicitly remove the old demo directory before running another simulation.


## Record-link integrity

The v0.1 validator now checks that the request, run plan, approval, telemetry manifest, lab run record, evidence packet, and review record agree on their declared identifiers and references. This is still an operational check only. It prevents broken evidence chains from looking complete, but it does not prove scientific validity.
