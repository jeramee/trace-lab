# Ingestion preview

TraceLab v20 adds `ingestion_preview_manifest.json` as a local index-candidate
manifest for simulated evidence runs.

The manifest exists to show what a future txtai, PaperAI, PaperETL, or evidence
search layer may consume later. It does not perform ingestion.

## Boundary

The ingestion preview is:

- local evidence metadata only
- candidate path listing only
- simulation-only
- safe for future indexing handoff planning

It is not:

- a NeuML/txtai/PaperAI call
- a model call
- a package installation
- network activity
- scientific-truth validation
- claim promotion
- human approval

## CLI

```bash
python3 -m trace_lab.cli ingestion-preview --run-dir .trace_lab_demo_inspect
python3 -m trace_lab.cli ingestion-preview --run-dir .trace_lab_demo_inspect --write
```

The `--write` command creates:

```text
ingestion_preview_summary.json
```

The demo run creates:

```text
ingestion_preview_manifest.json
```

## Validation

Validation reports ingestion-preview problems in:

```text
ingestion_errors
```

Examples include authority escalation, unsafe relative paths, malformed candidate
sections, and candidate-count drift.
