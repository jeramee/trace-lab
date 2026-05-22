# TraceLab execution policy manifest

`execution_policy_manifest.json` records the v0.1 execution and retry boundary.

It exists to make the no-hidden-retry rule explicit:

- execution is simulated only
- physical execution is not allowed
- automatic retry is not allowed
- hidden retry is not allowed
- retry attempt count remains zero in the demo run
- agents cannot approve retry, execute physical actions, or promote claims

This is operational evidence only. It does not validate scientific truth, approve hardware execution, or promote durable claims.
