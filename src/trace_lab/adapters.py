from __future__ import annotations

class SimulatedAdapter:
    """Simulation-only adapter. It never controls hardware."""

    adapter_id = "simulated_adapter_v0_1"

    def capability_manifest(self) -> dict:
        return {
            "record_type": "adapter_capability_manifest",
            "adapter_id": self.adapter_id,
            "mode": "simulation_only",
            "can_observe": True,
            "can_dry_run": True,
            "can_execute_physical_actions": False,
            "requires_human_approval": True,
            "authority_note": "Capability is not permission.",
        }

    def dry_run(self, action_type: str, parameters: dict) -> dict:
        return {
            "record_type": "dry_run_record",
            "adapter_id": self.adapter_id,
            "action_type": action_type,
            "parameters": parameters,
            "dry_run_status": "passed",
            "physical_execution_completed": False,
        }

    def simulate_action(self, action_id: str, action_type: str, parameters: dict) -> dict:
        return {
            "record_type": "adapter_action_record",
            "action_id": action_id,
            "adapter_id": self.adapter_id,
            "action_type": action_type,
            "parameters": parameters,
            "execution_mode": "simulated",
            "execution_status": "completed_simulated",
            "physical_execution_completed": False,
            "authority_note": "Simulated action is not physical execution or scientific validation.",
        }
