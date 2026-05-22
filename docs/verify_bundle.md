# Verify Bundle

`verify-bundle` checks a local TraceLab export ZIP after it has been created.

```bash
python -m trace_lab.cli verify-bundle --bundle .trace_lab_demo_export.zip
```

The command validates:

- `trace_lab_export_manifest.json` is present and readable.
- The manifest has `record_type = trace_lab_export_manifest`.
- The export scope remains `operational_simulation_only`.
- The source validation status is `passed_operational_checks`.
- Declared files exist inside the ZIP.
- Declared SHA-256 hashes match ZIP member bytes.
- Declared sizes match ZIP member bytes.
- Manifest paths are relative and cannot traverse outside the bundle.
- Authority flags remain false.
- The ZIP does not contain unexpected files.

This is a packaging-integrity check only.

It does not:

- validate scientific truth
- execute hardware
- call NeuML, txtai, PaperAI, or paperetl
- call networks
- install packages
- approve or promote claims
