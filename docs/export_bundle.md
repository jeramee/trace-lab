# TraceLab v0.1 Local Export Bundle

TraceLab can export a validated simulation run into a local ZIP file.

The export command is intentionally narrow:

- it checks operational validation first
- it refuses failed runs
- it refuses silent overwrite unless `--force` is used
- it includes a `trace_lab_export_manifest.json`
- it includes hashed run records and telemetry artifacts from `run_manifest.json`
- it may include optional operator-facing summaries if they already exist

The export bundle is not a claim promotion artifact.

Boundary language:

```text
evidence != truth
operational validation != scientific validity
approval record != agent permission
dry-run != physical execution
NeuML handoff != claim promotion
simulated adapter != hardware adapter
```

The export command does not call NeuML, txtai, PaperAI, paperetl, hardware APIs, networks, or package installers.
