# Review gate

TraceLab v0.1 treats review as a human-required trace checkpoint.

The generated `review_record.json` must stay in this bounded state:

```text
decision = review_required
review_status = pending_human_trace_review
review_scope = operator_trace_review_only
human_review_required = true
human_review_completed = false
agent_reviewed = false
automatic_promotion_allowed = false
claims_promoted = []
state_promoted = false
```

This checkpoint exists so later tools can show that a run needs human review before any durable scientific claim is promoted. It does not complete human review, approve hardware execution, validate scientific truth, or promote claims.

`review-summary` is an operator-facing view over that record. It may write `review_summary.json`, but that file is still only evidence metadata.
