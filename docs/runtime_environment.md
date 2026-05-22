# Runtime Environment Manifest

TraceLab v0.1 writes `runtime_environment_manifest.json` as reproducibility context for the simulated run.

The manifest records the Python/runtime context used to generate the local evidence packet. It is intentionally narrow:

- no package installation
- no network calls
- no hardware access
- no device-driver execution
- no scientific truth validation
- no claim promotion

The manifest is operational evidence only. It helps a future reviewer see what runtime created the simulated artifacts, but it does not certify the result or make the run scientifically valid.

The CLI can print or persist a small operator-facing summary:

```powershell
python -m trace_lab.cli environment-summary --run-dir .trace_lab_demo
python -m trace_lab.cli environment-summary --run-dir .trace_lab_demo --write
```

The persisted summary is `runtime_environment_summary.json`.
