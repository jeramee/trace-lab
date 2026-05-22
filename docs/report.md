# TraceLab local Markdown report

`trace_lab_report.md` is an operator-facing readability artifact for a simulated TraceLab run. It summarizes the local evidence chain, validation status, state chain, review gate, adapter boundary, and runtime environment.

It does not validate scientific truth, execute hardware, approve actions, call networks, install packages, or promote claims.

Use:

```powershell
python -m trace_lab.cli report --run-dir .trace_lab_demo_inspect
python -m trace_lab.cli report --run-dir .trace_lab_demo_inspect --write
```

The writer refuses silent overwrite unless `--force` is supplied.
