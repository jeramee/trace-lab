# TraceLab v0.1 Run-State Machine Summary

TraceLab v0.1 now treats the simulated evidence path as a fixed operational lifecycle.
The state machine exists to make record order, record support, and boundary language explicit before any future adapter work is considered.

## Allowed state sequence

```text
requested
-> planned
-> approved_for_simulation_only
-> dry_run_checked
-> simulated_action_recorded
-> telemetry_recorded
-> evidence_packet_built
-> operationally_validated
-> review_required
-> handoff_prepared
```

## State-to-record support

```text
requested -> experiment_request.json
planned -> run_plan.json
approved_for_simulation_only -> approval_record.json
dry_run_checked -> dry_run_record.json
simulated_action_recorded -> adapter_action_record.json
telemetry_recorded -> telemetry_manifest.json
evidence_packet_built -> evidence_packet_manifest.json
operationally_validated -> validation_record.json
review_required -> review_record.json
handoff_prepared -> neuml_handoff_manifest.json
```

Each state must be present once, in order, and supported by its expected record. Validation fails for unknown states, missing states, duplicate states, skipped states, backward transitions, handoff before review, operational validation before evidence packet build, and state names that imply hardware execution, scientific truth, or claim promotion.

## Boundaries preserved

```text
evidence != truth
operational validation != scientific validity
approval record != agent permission
dry-run != physical execution
NeuML handoff != claim promotion
simulated adapter != hardware adapter
```

The state machine is still simulation-only. It does not validate scientific truth, safety certification, hardware readiness, or durable claim promotion. Future hardware adapter work must preserve this lifecycle as an operational trace contract rather than a truth contract.
