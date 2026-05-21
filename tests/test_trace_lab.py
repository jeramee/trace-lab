import io
import json
import unittest
from contextlib import redirect_stderr

from trace_lab.adapters import SimulatedAdapter
from trace_lab.neuml_handoff import write_neuml_handoff_manifest
from trace_lab.validate import validate_run
from trace_lab.cli import main as cli_main
from trace_lab.workflow import run_simulated_experiment


REQUIRED_DEMO_FILES = {
    "experiment_request.json",
    "run_plan.json",
    "adapter_capability_manifest.json",
    "approval_record.json",
    "dry_run_record.json",
    "adapter_action_record.json",
    "telemetry_manifest.json",
    "validation_record.json",
    "lab_run_record.json",
    "evidence_packet_manifest.json",
    "review_record.json",
    "neuml_handoff_manifest.json",
}


class TraceLabSimulationTests(unittest.TestCase):
    def test_demo_run_creates_required_records(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_records"))

        for name in REQUIRED_DEMO_FILES:
            self.assertTrue((run_dir / name).exists(), name)
        self.assertTrue((run_dir / "telemetry" / "simulated_flow_sensor_A.csv").exists())
        self.assertFalse((run_dir / "notebook_run_record.json").exists())

    def test_validation_passes_for_complete_demo_run(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_valid"))
        result = validate_run(run_dir)

        self.assertEqual(result["validation_status"], "passed_operational_checks")
        self.assertEqual(result["missing"], [])
        self.assertEqual(result["unsafe"], [])


    def test_demo_run_refuses_to_overwrite_existing_run_directory(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_no_overwrite"))

        with self.assertRaises(FileExistsError):
            run_simulated_experiment(run_dir)

    def test_cli_run_demo_returns_failure_for_existing_run_directory(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_cli_no_overwrite"))

        stderr = io.StringIO()
        with redirect_stderr(stderr):
            result = cli_main(["run-demo", "--out", str(run_dir)])

        self.assertEqual(result, 1)
        self.assertIn("refuses to write", stderr.getvalue())

    def test_records_do_not_imply_physical_execution_or_promotion(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_authority"))

        action = self.read_json(run_dir / "adapter_action_record.json")
        lab_run = self.read_json(run_dir / "lab_run_record.json")
        review = self.read_json(run_dir / "review_record.json")
        validation = self.read_json(run_dir / "validation_record.json")
        handoff = self.read_json(run_dir / "neuml_handoff_manifest.json")

        self.assertFalse(action["physical_execution_completed"])
        self.assertEqual(action["execution_mode"], "simulated")
        self.assertFalse(lab_run["physical_execution_completed"])
        self.assertFalse(review["state_promoted"])
        self.assertFalse(validation["scientific_truth_validated"])
        self.assertFalse(handoff["authority_flags"]["agent_approved"])
        self.assertFalse(handoff["authority_flags"]["state_promoted"])

    def test_validation_catches_missing_required_records(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_missing"))
        (run_dir / "approval_record.json").unlink()

        result = validate_run(run_dir)

        self.assertEqual(result["validation_status"], "failed_operational_checks")
        self.assertIn("approval_record.json", result["missing"])

    def test_validation_catches_unsafe_physical_execution_claim(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_unsafe"))
        action_path = run_dir / "adapter_action_record.json"
        action = self.read_json(action_path)
        action["physical_execution_completed"] = True
        action_path.write_text(json.dumps(action, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        result = validate_run(run_dir)

        self.assertEqual(result["validation_status"], "failed_operational_checks")
        self.assertTrue(any("Physical execution" in item for item in result["unsafe"]))


    def test_validation_catches_missing_telemetry_file_referenced_by_manifest(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_missing_telemetry"))
        (run_dir / "telemetry" / "simulated_flow_sensor_A.csv").unlink()

        result = validate_run(run_dir)

        self.assertEqual(result["validation_status"], "failed_operational_checks")
        self.assertTrue(any("Telemetry file missing" in item for item in result["telemetry_errors"]))

    def test_validation_catches_telemetry_hash_mismatch(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_hash_mismatch"))
        telemetry_file = run_dir / "telemetry" / "simulated_flow_sensor_A.csv"
        telemetry_file.write_text("t,flow\n0,999.0\n", encoding="utf-8")

        result = validate_run(run_dir)

        self.assertEqual(result["validation_status"], "failed_operational_checks")
        self.assertTrue(any("Telemetry file hash mismatch" in item for item in result["telemetry_errors"]))

    def test_neuml_handoff_references_evidence_packet_outputs(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_handoff"))
        handoff_path = write_neuml_handoff_manifest(run_dir)
        handoff = self.read_json(handoff_path)

        self.assertEqual(handoff["evidence_packet_path"], "evidence_packet_manifest.json")
        self.assertIn("evidence_packet_manifest.json", handoff["records_included"])
        self.assertIn("telemetry/simulated_flow_sensor_A.csv", handoff["telemetry_data_candidates"])
        self.assertIn("txtai", handoff["recommended_ingestion_hints"])
        self.assertIn("paperai", handoff["recommended_ingestion_hints"])

    def test_handoff_language_does_not_claim_approval_truth_or_promotion(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_handoff_authority"))
        handoff = self.read_json(run_dir / "neuml_handoff_manifest.json")

        self.assertEqual(handoff["handoff_status"], "prepared_for_future_ingestion_only")
        self.assertFalse(handoff["authority_flags"]["agent_approved"])
        self.assertFalse(handoff["authority_flags"]["scientific_truth_validated"])
        self.assertFalse(handoff["authority_flags"]["physical_execution_completed"])
        self.assertFalse(handoff["authority_flags"]["state_promoted"])
        self.assertFalse(handoff["authority_flags"]["handoff_promotes_claims"])

    def test_simulated_adapter_cannot_represent_real_hardware_execution(self):
        adapter = SimulatedAdapter()
        capability = adapter.capability_manifest()
        dry_run = adapter.dry_run("capture_simulated_flow", {"duration_seconds": 3})
        action = adapter.simulate_action("action_test", "capture_simulated_flow", {"duration_seconds": 3})

        self.assertEqual(capability["mode"], "simulation_only")
        self.assertFalse(capability["can_execute_physical_actions"])
        self.assertFalse(dry_run["physical_execution_completed"])
        self.assertEqual(action["execution_mode"], "simulated")
        self.assertFalse(action["physical_execution_completed"])

    def tmp_path(self, name):
        from tempfile import TemporaryDirectory
        from pathlib import Path

        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        return Path(temp.name) / name

    @staticmethod
    def read_json(path):
        return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
