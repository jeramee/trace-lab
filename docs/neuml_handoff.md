# NeuML Handoff Boundary

`neuml_handoff_manifest.json` is a future-ingestion manifest for tools such as `txtai`, PaperAI, paperetl, RunLab, or EvidenceAI Core.

TraceLab v0.1 does not call those tools. It only lists candidate records and artifacts that a later workflow may index or inspect.

The handoff manifest includes:

- evidence packet path;
- records included;
- text/index candidates;
- telemetry/data candidates;
- report candidates;
- known gaps;
- not-proven claims;
- recommended ingestion hints.

The handoff manifest keeps authority flags false for agent approval, scientific truth validation, physical execution, claim promotion, and handoff-driven promotion.
