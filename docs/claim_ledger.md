# TraceLab Claim Ledger

TraceLab v0.1 writes `claim_ledger_manifest.json` as a local claim-boundary record for a simulated run.

The claim ledger separates **operational trace evidence** from claims that are still not proven:

- scientific truth
- physical safety validation
- hardware readiness
- human review completion
- durable claim promotion

The claim ledger does not approve actions, execute hardware, validate scientific truth, complete human review, run external ingestion, or promote durable claims.

`claim-summary` is an operator-facing JSON summary of that boundary.
