# Telemetry profile

TraceLab v0.1 records telemetry file shape as local mechanical evidence.

## Artifact

`telemetry_profile_manifest.json`

## CLI

```bash
python3 -m trace_lab.cli telemetry-profile --run-dir .trace_lab_demo
python3 -m trace_lab.cli telemetry-profile --run-dir .trace_lab_demo --write
```

## What it checks

- telemetry CSV path is relative and inside the run directory
- file hash matches `telemetry_manifest.json`
- column names remain stable
- row count remains stable
- numeric column min/max are recorded as data-shape evidence

## What it does not mean

- evidence != truth
- operational validation != scientific validity
- telemetry profile != sensor correctness
- telemetry profile != hardware readiness
- telemetry profile != claim promotion
