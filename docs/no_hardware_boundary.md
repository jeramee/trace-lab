# No-Hardware Boundary

TraceLab v0.1 is simulation-only.

It must not:

- execute real hardware;
- call real device APIs;
- perform GUI automation;
- silently retry physical actions;
- let agents approve runs;
- let agents validate scientific truth;
- promote durable claims.

The simulated adapter reports `mode: simulation_only` and `can_execute_physical_actions: false`.

Any future hardware-capable adapter must be a separate, explicit implementation with stronger policy checks, explicit human approval, and hardware-specific validation outside this v0.1 scaffold.
