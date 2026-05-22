# TraceLab Run Manifest

`run_manifest.json` is a v0.1 simulation-only hash index for generated run evidence.

It records:

- core JSON records
- telemetry artifacts
- SHA-256 hashes
- missing evidence paths, if any
- authority flags that must remain false

The manifest is used to detect mechanical drift after run generation. It does not validate scientific truth, approve hardware execution, perform retries, or promote claims.

Validator failures appear under `manifest_errors`.
