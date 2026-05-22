# Operator Review Packet

TraceLab v0.1 writes `operator_review_packet_manifest.json` as a local navigation artifact for human review.

The packet gathers the required simulated-run evidence items that a human reviewer would inspect:

- request, plan, approval, dry-run, action, telemetry, and lab-run records;
- state-chain, runtime, execution policy, telemetry profile, ingestion preview, provenance, closeout, and claim-ledger records;
- the simulated telemetry CSV artifact.

The packet is deliberately not a review decision. It preserves these boundaries:

- evidence != truth;
- operational validation != scientific validity;
- approval record != agent permission;
- dry-run != physical execution;
- NeuML handoff != claim promotion;
- simulated adapter != hardware adapter.

## CLI

```bash
python -m trace_lab.cli review-packet --run-dir .trace_lab_demo
python -m trace_lab.cli review-packet --run-dir .trace_lab_demo --write
```

`--write` creates `operator_review_packet_summary.json`.

`--write-manifest` refreshes `operator_review_packet_manifest.json`, but refuses silent overwrite unless `--force` is supplied.

## Validation

`validate` reports review-packet issues under `review_packet_errors`.

The validator catches:

- missing `operator_review_packet_manifest.json`;
- unsafe or escaping packet item paths;
- missing required packet item references;
- packet item hash drift;
- false claims that human review is complete;
- agent-reviewed, automatic-promotion, claim-promotion, or scientific-truth authority drift.

This remains operational validation only. It does not validate scientific truth, complete human review, approve hardware execution, or promote durable claims.
