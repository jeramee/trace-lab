# Verify Bundle Result Sidecar

TraceLab can persist the result of `verify-bundle` as a local sidecar JSON file.

The default sidecar path is:

```text
<bundle>.validation.json
```

This is package-integrity evidence only. It does not unpack or execute the bundle,
call hardware, call networks, validate scientific truth, or promote claims.

CLI:

```powershell
python -m trace_lab.cli verify-bundle --bundle .trace_lab_demo_export.zip --write-result
```

Use `--result-out` for an explicit result path and `--force-result` to replace an
existing sidecar intentionally.
