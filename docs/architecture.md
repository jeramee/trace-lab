# TraceLab v0.1 Architecture

TraceLab v0.1 is a simulated-first evidence path for instrumented research workflows.

The scaffold proves this sequence:

```text
experiment request
  -> run plan
  -> scoped simulation approval
  -> adapter capability manifest
  -> dry run record
  -> simulated action record
  -> telemetry manifest
  -> lab run record
  -> evidence packet manifest
  -> validation record
  -> review record
  -> NeuML handoff manifest
```

The implementation is intentionally small:

- `workflow.py` creates the demo evidence chain.
- `adapters.py` defines the simulation-only adapter.
- `validate.py` performs operational record checks and unsafe authority-claim checks.
- `neuml_handoff.py` writes future-ingestion metadata without calling external services.
- `cli.py` exposes demo, validation, and handoff commands.

TraceLab v0.1 does not own scientific truth, hardware control, durable promotion, or external NeuML execution.
