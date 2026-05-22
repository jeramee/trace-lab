# Report Validation

TraceLab v0.1 includes a local Markdown report validator.

The validator checks that `trace_lab_report.md` remains an operator-facing readability artifact and preserves required boundary language:

- evidence != truth
- operational validation != scientific validity
- approval record != agent permission
- dry-run != physical execution
- NeuML handoff != claim promotion
- simulated adapter != hardware adapter

The validator also checks that report authority flags remain false for agent approval, physical execution, scientific truth validation, state promotion, claim promotion, network calls, package installation, and hardware access.

This is not scientific validation. It does not approve execution, execute hardware, call networks, install packages, or promote claims.

CLI:

```powershell
python -m trace_lab.cli verify-report --run-dir .trace_lab_demo_inspect
python -m trace_lab.cli verify-report --run-dir .trace_lab_demo_inspect --write-result
```

The sidecar path is:

```text
trace_lab_report.md.validation.json
```
