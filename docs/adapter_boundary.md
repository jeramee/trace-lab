# Adapter boundary

TraceLab v0.1 is simulation-only. The adapter boundary exists to make that restriction explicit and machine-checkable.

The simulated demo run produces three adapter-facing records:

- `adapter_capability_manifest.json`
- `dry_run_record.json`
- `adapter_action_record.json`

Validation now checks that these records preserve a single simulated adapter identity, agree on the action and parameters, and do not declare hardware-control surfaces.

## Required v0.1 semantics

- Adapter mode must be `simulation_only`.
- Adapter action execution mode must be `simulated`.
- Physical execution must remain false.
- Physical action capability must remain false.
- Human approval remains required.
- Dry-run evidence must not become physical execution evidence.

## Forbidden v0.1 fields

The v0.1 simulation scaffold rejects adapter records that declare fields such as serial ports, device paths, hardware endpoints, LabVIEW VI paths, OPC UA endpoints, Modbus addresses, or driver modules. Those are future adapter concerns, not v0.1 behavior.

## CLI summary

```bash
python -m trace_lab.cli adapter-summary --run-dir .trace_lab_demo
python -m trace_lab.cli adapter-summary --run-dir .trace_lab_demo --write
```

`adapter_boundary_summary.json` is an operator-facing trace view. It does not call hardware, approve execution, validate scientific truth, perform retries, or promote claims.
