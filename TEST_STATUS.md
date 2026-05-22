# Test Status

Validated local test command:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Expected v24 result:

```text
Ran 170 tests
OK
```

The CLI smoke path includes demo generation, validation, summaries, claim-summary, review-packet, report/verification, export-bundle/verify-bundle, NeuML handoff rebuild, and final validation.


## v25 Replay plan manifest

Adds a local replay checklist manifest and summary (`replay_plan_manifest.json`, `replay_plan_summary.json`) plus `trace-lab replay-plan`. The replay plan is operator-checklist evidence only and does not execute replay, retry hidden actions, call hardware, or promote claims.

## v26 audit index

Expected unittest discovery count: 190 tests. New targeted audit-index tests passed in sandbox; full local command remains `python3 -m unittest discover -s tests -v`.


## v27 validation recipe

Adds `validation-recipe`, `validation_recipe_manifest.json`, and `validation_recipe_summary.json` as a local command-checklist artifact. The recipe records validation commands without executing them and preserves the no hardware/no truth/no promotion boundary.
