# TraceLab Validation Recipe

TraceLab v27 adds `validation_recipe_manifest.json` and `validation_recipe_summary.json`.

The validation recipe is a local operator checklist only. It records the commands
an operator can run to re-check a simulated evidence packet. It does not execute
those commands, install packages, call networks, call hardware, validate
scientific truth, approve execution, or promote claims.

CLI:

```bash
python -m trace_lab.cli validation-recipe --run-dir .trace_lab_demo_inspect
python -m trace_lab.cli validation-recipe --run-dir .trace_lab_demo_inspect --write
```
