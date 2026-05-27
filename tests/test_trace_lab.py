import io
import json
import unittest
import zipfile
from contextlib import redirect_stderr, redirect_stdout

from trace_lab.adapters import SimulatedAdapter
from trace_lab.neuml_handoff import write_neuml_handoff_manifest
from trace_lab.run_manifest import build_run_manifest, write_run_manifest
from trace_lab.validation_result import build_validation_result_record, write_validation_result_record
from trace_lab.validate import validate_run
from trace_lab.cli import main as cli_main
from trace_lab.workflow import run_simulated_experiment
from trace_lab.run_state import ALLOWED_RUN_STATE_SEQUENCE, build_run_state_summary
from trace_lab.review import REVIEW_STATUS_PENDING, build_review_summary
from trace_lab.adapter_policy import build_adapter_boundary_summary
from trace_lab.runtime_environment import build_runtime_environment_summary
from trace_lab.export_bundle import build_export_manifest, write_export_bundle, validate_export_bundle, write_export_bundle_validation_result, default_export_bundle_validation_result_path, EXPORT_MANIFEST_NAME
from trace_lab.report import REPORT_FILE, build_markdown_report, default_report_validation_result_path, validate_markdown_report, write_markdown_report, write_markdown_report_validation_result
from trace_lab.execution_policy import build_execution_policy_summary, validate_execution_policy_manifest
from trace_lab.telemetry_profile import build_telemetry_profile_manifest, build_telemetry_profile_summary, write_telemetry_profile_summary, write_telemetry_profile_manifest
from trace_lab.ingestion_preview import build_ingestion_preview_manifest, build_ingestion_preview_summary, write_ingestion_preview_summary, write_ingestion_preview_manifest
from trace_lab.provenance import build_provenance_manifest, build_provenance_summary, validate_provenance_manifest, write_provenance_summary, write_provenance_manifest
from trace_lab.closeout import build_run_closeout_manifest, build_run_closeout_summary, validate_run_closeout_manifest, write_run_closeout_summary, write_run_closeout_manifest
from trace_lab.claim_ledger import build_claim_ledger_manifest, build_claim_ledger_summary, validate_claim_ledger_manifest, write_claim_ledger_summary, write_claim_ledger_manifest
from trace_lab.operator_review_packet import build_operator_review_packet_manifest, build_operator_review_packet_summary, validate_operator_review_packet_manifest, write_operator_review_packet_summary, write_operator_review_packet_manifest
from trace_lab.replay_plan import build_replay_plan_manifest, build_replay_plan_summary, validate_replay_plan_manifest, write_replay_plan_summary, write_replay_plan_manifest
from trace_lab.audit_index import build_audit_index_manifest, build_audit_index_summary, validate_audit_index_manifest, write_audit_index_summary, write_audit_index_manifest
from trace_lab.validation_recipe import build_validation_recipe_manifest, build_validation_recipe_summary, validate_validation_recipe_manifest, write_validation_recipe_summary, write_validation_recipe_manifest


REQUIRED_DEMO_FILES = {
    "experiment_request.json",
    "run_plan.json",
    "adapter_capability_manifest.json",
    "approval_record.json",
    "dry_run_record.json",
    "adapter_action_record.json",
    "telemetry_manifest.json",
    "telemetry_profile_manifest.json",
    "ingestion_preview_manifest.json",
    "provenance_manifest.json",
    "run_closeout_manifest.json",
    "claim_ledger_manifest.json",
    "operator_review_packet_manifest.json",
    "replay_plan_manifest.json",
    "audit_index_manifest.json",
    "validation_recipe_manifest.json",
    "validation_record.json",
    "lab_run_record.json",
    "evidence_packet_manifest.json",
    "review_record.json",
    "run_state_chain.json",
    "runtime_environment_manifest.json",
    "execution_policy_manifest.json",
    "neuml_handoff_manifest.json",
    "run_manifest.json",
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



    def test_validation_result_record_preserves_authority_boundary(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_validation_result_authority"))
        result = validate_run(run_dir)
        record = build_validation_result_record(run_dir, result)

        self.assertEqual(record["record_type"], "trace_lab_validation_result_record")
        self.assertEqual(record["validation_scope"], "operational_simulation_only")
        self.assertEqual(record["validation_status"], "passed_operational_checks")
        self.assertFalse(record["authority_flags"]["agent_approved"])
        self.assertFalse(record["authority_flags"]["physical_execution_completed"])
        self.assertFalse(record["authority_flags"]["scientific_truth_validated"])
        self.assertFalse(record["authority_flags"]["state_promoted"])
        self.assertFalse(record["authority_flags"]["automatic_retry_performed"])
        self.assertIn("operational validation != scientific validity", record["boundary_notes"])

    def test_review_record_preserves_human_required_gate(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_review_gate"))
        review = self.read_json(run_dir / "review_record.json")

        self.assertEqual(review["record_type"], "review_record")
        self.assertEqual(review["decision"], "review_required")
        self.assertEqual(review["review_status"], REVIEW_STATUS_PENDING)
        self.assertEqual(review["review_scope"], "operator_trace_review_only")
        self.assertTrue(review["human_review_required"])
        self.assertFalse(review["human_review_completed"])
        self.assertFalse(review["agent_reviewed"])
        self.assertFalse(review["automatic_promotion_allowed"])
        self.assertFalse(review["authority_flags"]["agent_approved"])
        self.assertFalse(review["authority_flags"]["scientific_truth_validated"])
        self.assertIn("evidence != truth", review["boundary_notes"])

    def test_validation_catches_missing_human_review_required_gate(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_review_missing_human_gate"))
        review_path = run_dir / "review_record.json"
        review = self.read_json(review_path)
        review["human_review_required"] = False
        self.write_json(review_path, review)

        result = validate_run(run_dir)

        self.assertEqual(result["validation_status"], "failed_operational_checks")
        self.assertTrue(any("human_review_required=true" in item for item in result["review_errors"]))

    def test_validation_catches_agent_review_or_auto_promotion_claim(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_review_agent_promotion"))
        review_path = run_dir / "review_record.json"
        review = self.read_json(review_path)
        review["agent_reviewed"] = True
        review["automatic_promotion_allowed"] = True
        review["authority_flags"]["agent_reviewed"] = True
        self.write_json(review_path, review)

        result = validate_run(run_dir)

        self.assertEqual(result["validation_status"], "failed_operational_checks")
        self.assertTrue(any("agent_reviewed" in item for item in result["unsafe"]))
        self.assertTrue(any("automatic promotion" in item for item in result["unsafe"]))

    def test_cli_review_summary_outputs_human_required_boundary(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_cli_review_summary"))

        stdout = io.StringIO()
        with redirect_stdout(stdout):
            result = cli_main(["review-summary", "--run-dir", str(run_dir)])

        summary = json.loads(stdout.getvalue())
        self.assertEqual(result, 0)
        self.assertEqual(summary["record_type"], "review_summary")
        self.assertEqual(summary["review_summary_status"], REVIEW_STATUS_PENDING)
        self.assertTrue(summary["human_review_required"])
        self.assertFalse(summary["human_review_completed"])
        self.assertFalse(summary["agent_reviewed"])
        self.assertIn("evidence != truth", summary["boundary_notes"])

    def test_cli_review_summary_write_creates_summary_file(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_cli_review_summary_write"))

        stdout = io.StringIO()
        with redirect_stdout(stdout):
            result = cli_main(["review-summary", "--run-dir", str(run_dir), "--write"])

        self.assertEqual(result, 0)
        self.assertTrue((run_dir / "review_summary.json").exists())
        summary = build_review_summary(run_dir)
        self.assertEqual(summary["review_summary_status"], REVIEW_STATUS_PENDING)


    def test_demo_run_creates_run_manifest_with_record_hashes(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_run_manifest"))
        manifest = self.read_json(run_dir / "run_manifest.json")

        self.assertEqual(manifest["record_type"], "run_manifest")
        self.assertEqual(manifest["manifest_scope"], "operational_simulation_only")
        self.assertEqual(manifest["missing"], [])
        self.assertFalse(manifest["authority_flags"]["scientific_truth_validated"])
        self.assertFalse(manifest["authority_flags"]["physical_execution_completed"])

        record_paths = {item["path"] for item in manifest["records"]}
        self.assertIn("experiment_request.json", record_paths)
        self.assertIn("neuml_handoff_manifest.json", record_paths)
        self.assertIn("run_state_chain.json", record_paths)
        artifact_paths = {item["path"] for item in manifest["artifacts"]}
        self.assertIn("telemetry/simulated_flow_sensor_A.csv", artifact_paths)

    def test_run_manifest_writer_refuses_silent_overwrite(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_run_manifest_no_overwrite"))

        with self.assertRaises(FileExistsError):
            write_run_manifest(run_dir)

    def test_validation_catches_run_manifest_record_hash_mismatch(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_run_manifest_record_hash_mismatch"))
        request_path = run_dir / "experiment_request.json"
        request = self.read_json(request_path)
        request["research_question"] = "Changed after manifest hashing."
        self.write_json(request_path, request)

        result = validate_run(run_dir)

        self.assertEqual(result["validation_status"], "failed_operational_checks")
        self.assertTrue(any("hash mismatch: experiment_request.json" in item for item in result["manifest_errors"]))

    def test_validation_catches_run_manifest_missing_required_record_entry(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_run_manifest_missing_record_entry"))
        manifest_path = run_dir / "run_manifest.json"
        manifest = self.read_json(manifest_path)
        manifest["records"] = [item for item in manifest["records"] if item["path"] != "run_plan.json"]
        self.write_json(manifest_path, manifest)

        result = validate_run(run_dir)

        self.assertEqual(result["validation_status"], "failed_operational_checks")
        self.assertTrue(any("records missing required record: run_plan.json" in item for item in result["manifest_errors"]))

    def test_validation_catches_run_manifest_authority_escalation(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_run_manifest_authority_escalation"))
        manifest_path = run_dir / "run_manifest.json"
        manifest = self.read_json(manifest_path)
        manifest["authority_flags"]["state_promoted"] = True
        self.write_json(manifest_path, manifest)

        result = validate_run(run_dir)

        self.assertEqual(result["validation_status"], "failed_operational_checks")
        self.assertTrue(any("state_promoted=true" in item for item in result["manifest_errors"]))

    def test_validation_result_writer_refuses_silent_overwrite(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_validation_result_no_overwrite"))
        first_path = write_validation_result_record(run_dir)

        self.assertTrue(first_path.exists())
        with self.assertRaises(FileExistsError):
            write_validation_result_record(run_dir)

    def test_cli_validate_write_result_creates_persisted_result(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_cli_validate_write_result"))

        stdout = io.StringIO()
        with redirect_stdout(stdout):
            result = cli_main(["validate", "--run-dir", str(run_dir), "--write-result"])

        cli_result = json.loads(stdout.getvalue())
        persisted = self.read_json(run_dir / "validation_result.json")
        self.assertEqual(result, 0)
        self.assertEqual(cli_result["validation_status"], "passed_operational_checks")
        self.assertTrue((run_dir / "validation_result.json").exists())
        self.assertEqual(persisted["record_type"], "trace_lab_validation_result_record")
        self.assertEqual(persisted["validation_status"], "passed_operational_checks")
        self.assertFalse(persisted["authority_flags"]["scientific_truth_validated"])

    def test_cli_validate_write_result_refuses_silent_overwrite(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_cli_validate_result_no_overwrite"))
        write_validation_result_record(run_dir)

        stderr = io.StringIO()
        with redirect_stderr(stderr):
            result = cli_main(["validate", "--run-dir", str(run_dir), "--write-result"])

        self.assertEqual(result, 1)
        self.assertIn("refuses to overwrite validation_result.json", stderr.getvalue())

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


    def test_validation_catches_approval_plan_mismatch(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_approval_mismatch"))
        approval_path = run_dir / "approval_record.json"
        approval = self.read_json(approval_path)
        approval["run_plan_id"] = "plan_wrong_999"
        approval_path.write_text(json.dumps(approval, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        result = validate_run(run_dir)

        self.assertEqual(result["validation_status"], "failed_operational_checks")
        self.assertTrue(any("approval_record.json run_plan_id" in item for item in result["record_errors"]))

    def test_validation_catches_physical_approval_scope(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_physical_approval"))
        approval_path = run_dir / "approval_record.json"
        approval = self.read_json(approval_path)
        approval["decision"] = "approved_for_physical_execution"
        approval["approval_scope"] = "physical_execution"
        approval["physical_execution_allowed"] = True
        approval_path.write_text(json.dumps(approval, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        result = validate_run(run_dir)

        self.assertEqual(result["validation_status"], "failed_operational_checks")
        self.assertTrue(any("approve simulation only" in item for item in result["record_errors"]))
        self.assertTrue(any("physical execution" in item for item in result["unsafe"]))

    def test_validation_catches_lab_run_missing_record_refs(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_missing_refs"))
        lab_run_path = run_dir / "lab_run_record.json"
        lab_run = self.read_json(lab_run_path)
        lab_run["action_record_refs"] = []
        lab_run["telemetry_manifest_refs"] = []
        lab_run_path.write_text(json.dumps(lab_run, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        result = validate_run(run_dir)

        self.assertEqual(result["validation_status"], "failed_operational_checks")
        self.assertTrue(any("adapter_action_record.json" in item for item in result["record_errors"]))
        self.assertTrue(any("telemetry_manifest.json" in item for item in result["record_errors"]))

    def test_validation_catches_evidence_artifact_hash_mismatch(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_evidence_hash_mismatch"))
        telemetry_file = run_dir / "telemetry" / "simulated_flow_sensor_A.csv"
        telemetry_file.write_text("t,flow\n0,777.0\n", encoding="utf-8")

        result = validate_run(run_dir)

        self.assertEqual(result["validation_status"], "failed_operational_checks")
        self.assertTrue(any("Evidence artifact hash mismatch" in item for item in result["evidence_errors"]))

    def test_neuml_handoff_references_evidence_packet_outputs(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_handoff"))
        handoff_path = write_neuml_handoff_manifest(run_dir)
        handoff = self.read_json(handoff_path)

        self.assertEqual(handoff["evidence_packet_path"], "evidence_packet_manifest.json")
        self.assertIn("evidence_packet_manifest.json", handoff["records_included"])
        self.assertIn("telemetry/simulated_flow_sensor_A.csv", handoff["telemetry_data_candidates"])
        self.assertIn("txtai", handoff["recommended_ingestion_hints"])
        self.assertIn("paperai", handoff["recommended_ingestion_hints"])


    def test_handoff_writer_refuses_missing_precondition_record(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_handoff_missing_precondition"))
        (run_dir / "review_record.json").unlink()

        with self.assertRaises(ValueError) as context:
            write_neuml_handoff_manifest(run_dir)

        self.assertIn("refuses to prepare NeuML handoff", str(context.exception))
        self.assertIn("review_record.json", str(context.exception))

    def test_cli_build_neuml_handoff_returns_failure_for_incomplete_run(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_cli_handoff_incomplete"))
        (run_dir / "review_record.json").unlink()
        (run_dir / "neuml_handoff_manifest.json").unlink()

        stderr = io.StringIO()
        with redirect_stderr(stderr):
            result = cli_main(["build-neuml-handoff", "--run-dir", str(run_dir)])

        self.assertEqual(result, 1)
        self.assertIn("refuses to prepare NeuML handoff", stderr.getvalue())
        self.assertFalse((run_dir / "neuml_handoff_manifest.json").exists())

    def test_cli_build_neuml_handoff_refreshes_run_manifest_hashes(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_cli_handoff_refreshes_run_manifest"))
        handoff_path = run_dir / "neuml_handoff_manifest.json"
        stale_handoff = self.read_json(handoff_path)
        stale_handoff["known_gaps"].append("temporary stale handoff edit")
        self.write_json(handoff_path, stale_handoff)

        stale_validation = validate_run(run_dir)
        self.assertTrue(any("hash mismatch: neuml_handoff_manifest.json" in item for item in stale_validation["manifest_errors"]))

        stdout = io.StringIO()
        with redirect_stdout(stdout):
            result = cli_main(["build-neuml-handoff", "--run-dir", str(run_dir)])

        validation = validate_run(run_dir)

        self.assertEqual(result, 0)
        self.assertEqual(validation["manifest_errors"], [])
        self.assertEqual(validation["validation_status"], "passed_operational_checks")

    def test_validation_catches_handoff_missing_required_record_reference(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_handoff_missing_record_ref"))
        handoff_path = run_dir / "neuml_handoff_manifest.json"
        handoff = self.read_json(handoff_path)
        handoff["records_included"] = [
            name for name in handoff["records_included"] if name != "review_record.json"
        ]
        self.write_json(handoff_path, handoff)

        result = validate_run(run_dir)

        self.assertEqual(result["validation_status"], "failed_operational_checks")
        self.assertTrue(any("records_included missing required record: review_record.json" in item for item in result["handoff_errors"]))

    def test_validation_catches_handoff_wrong_evidence_packet_path(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_handoff_wrong_evidence_path"))
        handoff_path = run_dir / "neuml_handoff_manifest.json"
        handoff = self.read_json(handoff_path)
        handoff["evidence_packet_path"] = "wrong_manifest.json"
        self.write_json(handoff_path, handoff)

        result = validate_run(run_dir)

        self.assertEqual(result["validation_status"], "failed_operational_checks")
        self.assertTrue(any("evidence_packet_path" in item for item in result["handoff_errors"]))

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


    def test_run_state_chain_records_required_sequence(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_state_sequence"))
        chain = self.read_json(run_dir / "run_state_chain.json")

        self.assertEqual(chain["record_type"], "run_state_chain")
        self.assertEqual(chain["lifecycle_scope"], "operational_simulation_only")
        self.assertEqual([item["state"] for item in chain["states"]], ALLOWED_RUN_STATE_SEQUENCE)
        self.assertEqual(chain["terminal_state"], "handoff_prepared")

        result = validate_run(run_dir)
        self.assertEqual(result["state_errors"], [])

    def test_validation_catches_missing_run_state(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_state_missing"))
        chain_path = run_dir / "run_state_chain.json"
        chain = self.read_json(chain_path)
        chain["states"] = [item for item in chain["states"] if item["state"] != "telemetry_recorded"]
        self.write_json(chain_path, chain)

        result = validate_run(run_dir)

        self.assertEqual(result["validation_status"], "failed_operational_checks")
        self.assertTrue(any("missing required state: telemetry_recorded" in item for item in result["state_errors"]))

    def test_validation_catches_unknown_run_state(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_state_unknown"))
        chain_path = run_dir / "run_state_chain.json"
        chain = self.read_json(chain_path)
        chain["states"].insert(1, {"state_index": 999, "state": "mystery_state", "supported_by": "run_plan.json"})
        self.write_json(chain_path, chain)

        result = validate_run(run_dir)

        self.assertEqual(result["validation_status"], "failed_operational_checks")
        self.assertTrue(any("unknown state: mystery_state" in item for item in result["state_errors"]))

    def test_validation_catches_duplicate_run_state(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_state_duplicate"))
        chain_path = run_dir / "run_state_chain.json"
        chain = self.read_json(chain_path)
        chain["states"].insert(2, dict(chain["states"][1]))
        self.write_json(chain_path, chain)

        result = validate_run(run_dir)

        self.assertEqual(result["validation_status"], "failed_operational_checks")
        self.assertTrue(any("duplicate state: planned" in item for item in result["state_errors"]))

    def test_validation_catches_skipped_run_state_transition(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_state_skipped"))
        chain_path = run_dir / "run_state_chain.json"
        chain = self.read_json(chain_path)
        chain["states"] = [item for item in chain["states"] if item["state"] != "dry_run_checked"]
        self.write_json(chain_path, chain)

        result = validate_run(run_dir)

        self.assertEqual(result["validation_status"], "failed_operational_checks")
        self.assertTrue(any("skipped state transition" in item for item in result["state_errors"]))

    def test_validation_catches_backward_run_state_transition(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_state_backward"))
        chain_path = run_dir / "run_state_chain.json"
        chain = self.read_json(chain_path)
        chain["states"][3], chain["states"][4] = chain["states"][4], chain["states"][3]
        self.write_json(chain_path, chain)

        result = validate_run(run_dir)

        self.assertEqual(result["validation_status"], "failed_operational_checks")
        self.assertTrue(any("backward transition" in item for item in result["state_errors"]))

    def test_validation_catches_handoff_before_review(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_state_handoff_before_review"))
        chain_path = run_dir / "run_state_chain.json"
        chain = self.read_json(chain_path)
        handoff = next(item for item in chain["states"] if item["state"] == "handoff_prepared")
        chain["states"] = [item for item in chain["states"] if item["state"] != "handoff_prepared"]
        chain["states"].insert(8, handoff)
        self.write_json(chain_path, chain)

        result = validate_run(run_dir)

        self.assertEqual(result["validation_status"], "failed_operational_checks")
        self.assertTrue(any("cannot prepare handoff before review_required" in item for item in result["state_errors"]))

    def test_validation_catches_operational_validation_before_evidence_packet(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_state_validation_before_evidence"))
        chain_path = run_dir / "run_state_chain.json"
        chain = self.read_json(chain_path)
        operational = next(item for item in chain["states"] if item["state"] == "operationally_validated")
        chain["states"] = [item for item in chain["states"] if item["state"] != "operationally_validated"]
        chain["states"].insert(6, operational)
        self.write_json(chain_path, chain)

        result = validate_run(run_dir)

        self.assertEqual(result["validation_status"], "failed_operational_checks")
        self.assertTrue(any("cannot validate operationally before evidence_packet_built" in item for item in result["state_errors"]))

    def test_validation_catches_state_text_implying_physical_execution_truth_or_promotion(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_state_forbidden_text"))
        chain_path = run_dir / "run_state_chain.json"
        chain = self.read_json(chain_path)
        chain["states"].append({"state_index": 10, "state": "physical_execution_completed", "supported_by": "lab_run_record.json"})
        chain["states"].append({"state_index": 11, "state": "scientific_truth_validated", "supported_by": "validation_record.json"})
        chain["states"].append({"state_index": 12, "state": "claim_promoted", "supported_by": "review_record.json"})
        self.write_json(chain_path, chain)

        result = validate_run(run_dir)

        self.assertEqual(result["validation_status"], "failed_operational_checks")
        forbidden_errors = [item for item in result["state_errors"] if "forbidden authority or physical execution" in item]
        self.assertGreaterEqual(len(forbidden_errors), 3)

    def test_state_to_record_alignment_requires_expected_support_record(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_state_alignment"))
        chain_path = run_dir / "run_state_chain.json"
        chain = self.read_json(chain_path)
        for item in chain["states"]:
            if item["state"] == "telemetry_recorded":
                item["supported_by"] = "evidence_packet_manifest.json"
        self.write_json(chain_path, chain)

        result = validate_run(run_dir)

        self.assertEqual(result["validation_status"], "failed_operational_checks")
        self.assertTrue(any("state telemetry_recorded must be supported_by telemetry_manifest.json" in item for item in result["state_errors"]))

    def test_state_to_record_alignment_checks_record_semantics(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_state_record_semantics"))
        telemetry_path = run_dir / "telemetry_manifest.json"
        telemetry = self.read_json(telemetry_path)
        telemetry["telemetry_status"] = "missing_for_simulation"
        self.write_json(telemetry_path, telemetry)

        result = validate_run(run_dir)

        self.assertEqual(result["validation_status"], "failed_operational_checks")
        self.assertTrue(any("State telemetry_recorded requires telemetry_manifest.json" in item for item in result["state_errors"]))

    def test_cli_state_summary_outputs_simulation_only_state_chain(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_cli_state_summary"))

        stdout = io.StringIO()
        with redirect_stdout(stdout):
            result = cli_main(["state-summary", "--run-dir", str(run_dir)])

        summary = json.loads(stdout.getvalue())
        self.assertEqual(result, 0)
        self.assertEqual(summary["state_summary_status"], "complete_simulation_only")
        self.assertEqual(summary["states"], ALLOWED_RUN_STATE_SEQUENCE)
        self.assertEqual(summary["terminal_state"], "handoff_prepared")
        self.assertIn("simulated adapter != hardware adapter", summary["boundary_notes"])

    def test_cli_state_summary_write_creates_summary_file(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_cli_state_summary_write"))

        stdout = io.StringIO()
        with redirect_stdout(stdout):
            result = cli_main(["state-summary", "--run-dir", str(run_dir), "--write"])

        self.assertEqual(result, 0)
        self.assertTrue((run_dir / "run_state_summary.json").exists())
        summary = build_run_state_summary(run_dir)
        self.assertEqual(summary["state_summary_status"], "complete_simulation_only")


    def test_adapter_summary_outputs_simulation_only_boundary(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_adapter_summary"))

        summary = build_adapter_boundary_summary(run_dir)

        self.assertEqual(summary["record_type"], "adapter_boundary_summary")
        self.assertEqual(summary["adapter_boundary_status"], "simulation_only_boundary_intact")
        self.assertEqual(summary["adapter_id"], "simulated_adapter_v0_1")
        self.assertEqual(summary["adapter_mode"], "simulation_only")
        self.assertFalse(summary["can_execute_physical_actions"])
        self.assertEqual(summary["execution_mode"], "simulated")
        self.assertFalse(summary["physical_execution_completed"])
        self.assertEqual(summary["adapter_errors"], [])
        self.assertEqual(summary["unsafe"], [])
        self.assertIn("simulated adapter != hardware adapter", summary["boundary_notes"])

    def test_cli_adapter_summary_write_creates_summary_file(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_cli_adapter_summary_write"))

        stdout = io.StringIO()
        with redirect_stdout(stdout):
            result = cli_main(["adapter-summary", "--run-dir", str(run_dir), "--write"])

        self.assertEqual(result, 0)
        self.assertTrue((run_dir / "adapter_boundary_summary.json").exists())
        summary = self.read_json(run_dir / "adapter_boundary_summary.json")
        self.assertEqual(summary["adapter_boundary_status"], "simulation_only_boundary_intact")

    def test_validation_catches_adapter_capability_mode_drift(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_adapter_mode_drift"))
        capability_path = run_dir / "adapter_capability_manifest.json"
        capability = self.read_json(capability_path)
        capability["mode"] = "hardware_enabled"
        self.write_json(capability_path, capability)

        result = validate_run(run_dir)

        self.assertEqual(result["validation_status"], "failed_operational_checks")
        self.assertTrue(any("mode must be simulation_only" in item for item in result["unsafe"]))

    def test_validation_catches_adapter_id_mismatch(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_adapter_id_mismatch"))
        action_path = run_dir / "adapter_action_record.json"
        action = self.read_json(action_path)
        action["adapter_id"] = "unapproved_adapter"
        self.write_json(action_path, action)

        result = validate_run(run_dir)

        self.assertEqual(result["validation_status"], "failed_operational_checks")
        self.assertTrue(any("adapter_id must match" in item for item in result["adapter_errors"]))

    def test_validation_catches_forbidden_hardware_adapter_fields(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_forbidden_adapter_field"))
        capability_path = run_dir / "adapter_capability_manifest.json"
        capability = self.read_json(capability_path)
        capability["serial_port"] = "COM3"
        self.write_json(capability_path, capability)

        result = validate_run(run_dir)

        self.assertEqual(result["validation_status"], "failed_operational_checks")
        self.assertTrue(any("serial_port" in item for item in result["unsafe"]))

    def test_validation_catches_dry_run_action_parameter_mismatch(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_adapter_param_mismatch"))
        dry_path = run_dir / "dry_run_record.json"
        dry_run = self.read_json(dry_path)
        dry_run["parameters"] = {"duration_seconds": 999}
        self.write_json(dry_path, dry_run)

        result = validate_run(run_dir)

        self.assertEqual(result["validation_status"], "failed_operational_checks")
        self.assertTrue(any("parameters must match" in item for item in result["adapter_errors"]))


    def test_runtime_environment_manifest_preserves_simulation_boundary(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_runtime_environment"))
        manifest = self.read_json(run_dir / "runtime_environment_manifest.json")

        self.assertEqual(manifest["record_type"], "runtime_environment_manifest")
        self.assertEqual(manifest["environment_scope"], "operational_simulation_only")
        self.assertEqual(manifest["implementation_language"], "Python")
        self.assertEqual(manifest["package_name"], "trace_lab")
        self.assertFalse(manifest["package_installation_performed"])
        self.assertFalse(manifest["network_calls_performed"])
        self.assertFalse(manifest["hardware_access_performed"])
        self.assertFalse(manifest["authority_flags"]["hardware_access_performed"])
        self.assertIn("simulated adapter != hardware adapter", manifest["boundary_notes"])

    def test_cli_environment_summary_outputs_runtime_boundary(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_environment_summary"))
        stdout = io.StringIO()

        with redirect_stdout(stdout):
            code = cli_main(["environment-summary", "--run-dir", str(run_dir)])

        self.assertEqual(code, 0)
        summary = json.loads(stdout.getvalue())
        self.assertEqual(summary["record_type"], "runtime_environment_summary")
        self.assertEqual(summary["environment_summary_status"], "runtime_context_recorded")
        self.assertEqual(summary["environment_scope"], "operational_simulation_only")
        self.assertFalse(summary["package_installation_performed"])
        self.assertFalse(summary["network_calls_performed"])
        self.assertFalse(summary["hardware_access_performed"])
        self.assertEqual(summary["environment_errors"], [])

    def test_cli_environment_summary_write_creates_summary_file(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_environment_summary_write"))
        stdout = io.StringIO()

        with redirect_stdout(stdout):
            code = cli_main(["environment-summary", "--run-dir", str(run_dir), "--write"])

        self.assertEqual(code, 0)
        self.assertTrue((run_dir / "runtime_environment_summary.json").exists())
        summary = self.read_json(run_dir / "runtime_environment_summary.json")
        self.assertEqual(summary["environment_summary_status"], "runtime_context_recorded")

    def test_validation_catches_missing_runtime_environment_manifest(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_missing_runtime_environment"))
        (run_dir / "runtime_environment_manifest.json").unlink()

        result = validate_run(run_dir)

        self.assertEqual(result["validation_status"], "failed_operational_checks")
        self.assertIn("runtime_environment_manifest.json", result["missing"])

    def test_validation_catches_runtime_environment_hardware_access_claim(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_runtime_hardware_access"))
        env_path = run_dir / "runtime_environment_manifest.json"
        manifest = self.read_json(env_path)
        manifest["hardware_access_performed"] = True
        self.write_json(env_path, manifest)

        result = validate_run(run_dir)

        self.assertEqual(result["validation_status"], "failed_operational_checks")
        self.assertTrue(any("hardware_access_performed" in item for item in result["unsafe"]))

    def test_validation_catches_runtime_environment_missing_python_version(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_runtime_missing_python"))
        env_path = run_dir / "runtime_environment_manifest.json"
        manifest = self.read_json(env_path)
        manifest["python_version"] = ""
        self.write_json(env_path, manifest)

        result = validate_run(run_dir)

        self.assertEqual(result["validation_status"], "failed_operational_checks")
        self.assertTrue(any("python_version" in item for item in result["environment_errors"]))



    def test_export_bundle_manifest_includes_default_profile_metadata(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_export_default_profile"))
        manifest = build_export_manifest(run_dir)

        self.assertEqual(manifest["selected_profile"], "simulated_lab_bundle")
        self.assertEqual(
            manifest["profile_evidence_meaning"],
            "Simulated lab/research evidence bundle provenance and verification status",
        )
        self.assertIn("no real hardware control", manifest["profile_stop_lines"])
        self.assertIn("no scientific truth validation", manifest["profile_stop_lines"])
        self.assertIn("no ncoder requirement", manifest["profile_stop_lines"])

    def test_export_bundle_manifest_preserves_authority_boundary(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_export_manifest"))
        manifest = build_export_manifest(run_dir)

        self.assertEqual(manifest["record_type"], "trace_lab_export_manifest")
        self.assertEqual(manifest["export_scope"], "operational_simulation_only")
        self.assertEqual(manifest["export_status"], "ready_for_local_zip_export")
        self.assertFalse(manifest["authority_flags"]["physical_execution_completed"])
        self.assertFalse(manifest["authority_flags"]["scientific_truth_validated"])
        self.assertFalse(manifest["authority_flags"]["state_promoted"])
        self.assertFalse(manifest["authority_flags"]["network_calls_performed"])
        self.assertFalse(manifest["authority_flags"]["package_installation_performed"])
        self.assertFalse(manifest["authority_flags"]["hardware_access_performed"])
        self.assertIn("operational validation != scientific validity", manifest["boundary_notes"])

    def test_export_bundle_includes_required_trace_files(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_export_required_files"))
        bundle_path = run_dir.parent / "trace_lab_export.zip"

        write_export_bundle(run_dir, bundle_path)

        self.assertTrue(bundle_path.exists())
        with zipfile.ZipFile(bundle_path) as bundle:
            names = set(bundle.namelist())

        self.assertIn(EXPORT_MANIFEST_NAME, names)
        self.assertIn("run_manifest.json", names)
        self.assertIn("runtime_environment_manifest.json", names)
        self.assertIn("neuml_handoff_manifest.json", names)
        self.assertIn("telemetry/simulated_flow_sensor_A.csv", names)

    def test_cli_export_bundle_dry_run_outputs_manifest_without_zip(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_export_dry_run"))
        bundle_path = run_dir.parent / "trace_lab_export.zip"
        stdout = io.StringIO()

        with redirect_stdout(stdout):
            code = cli_main(["export-bundle", "--run-dir", str(run_dir), "--out", str(bundle_path), "--dry-run"])

        self.assertEqual(code, 0)
        self.assertFalse(bundle_path.exists())
        manifest = json.loads(stdout.getvalue())
        self.assertEqual(manifest["record_type"], "trace_lab_export_manifest")
        self.assertEqual(manifest["export_status"], "ready_for_local_zip_export")

    def test_cli_export_bundle_creates_zip_with_manifest(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_cli_export"))
        bundle_path = run_dir.parent / "trace_lab_export.zip"
        stdout = io.StringIO()

        with redirect_stdout(stdout):
            code = cli_main(["export-bundle", "--run-dir", str(run_dir), "--out", str(bundle_path)])

        self.assertEqual(code, 0)
        self.assertTrue(bundle_path.exists())
        self.assertIn(str(bundle_path), stdout.getvalue())
        with zipfile.ZipFile(bundle_path) as bundle:
            manifest = json.loads(bundle.read(EXPORT_MANIFEST_NAME).decode("utf-8"))

        self.assertEqual(manifest["record_type"], "trace_lab_export_manifest")
        self.assertEqual(manifest["source_validation_status"], "passed_operational_checks")

    def test_export_bundle_refuses_silent_overwrite(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_export_overwrite"))
        bundle_path = run_dir.parent / "trace_lab_export.zip"

        write_export_bundle(run_dir, bundle_path)

        with self.assertRaises(FileExistsError):
            write_export_bundle(run_dir, bundle_path)

    def test_export_bundle_refuses_failed_operational_validation(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_export_invalid"))
        (run_dir / "telemetry" / "simulated_flow_sensor_A.csv").unlink()
        bundle_path = run_dir.parent / "trace_lab_export.zip"

        with self.assertRaises(ValueError):
            write_export_bundle(run_dir, bundle_path)

        self.assertFalse(bundle_path.exists())

    def test_cli_export_bundle_returns_failure_for_invalid_run(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_cli_export_invalid"))
        (run_dir / "runtime_environment_manifest.json").unlink()
        bundle_path = run_dir.parent / "trace_lab_export.zip"
        stderr = io.StringIO()

        with redirect_stderr(stderr):
            code = cli_main(["export-bundle", "--run-dir", str(run_dir), "--out", str(bundle_path)])

        self.assertEqual(code, 1)
        self.assertFalse(bundle_path.exists())
        self.assertIn("failed operational validation", stderr.getvalue())


    def test_verify_export_bundle_passes_for_complete_bundle(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_verify_export"))
        bundle_path = run_dir.parent / "trace_lab_export.zip"
        write_export_bundle(run_dir, bundle_path)

        result = validate_export_bundle(bundle_path)

        self.assertEqual(result["record_type"], "trace_lab_export_bundle_validation")
        self.assertEqual(result["bundle_validation_status"], "passed_export_bundle_checks")
        self.assertEqual(result["export_bundle_errors"], [])
        self.assertFalse(result["authority_flags"]["scientific_truth_validated"])
        self.assertFalse(result["authority_flags"]["physical_execution_completed"])
        self.assertIn("operational validation != scientific validity", result["boundary_notes"])

    def test_cli_verify_bundle_outputs_passed_status(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_cli_verify_export"))
        bundle_path = run_dir.parent / "trace_lab_export.zip"
        write_export_bundle(run_dir, bundle_path)
        stdout = io.StringIO()

        with redirect_stdout(stdout):
            code = cli_main(["verify-bundle", "--bundle", str(bundle_path)])

        result = json.loads(stdout.getvalue())
        self.assertEqual(code, 0)
        self.assertEqual(result["bundle_validation_status"], "passed_export_bundle_checks")
        self.assertEqual(result["export_bundle_errors"], [])

    def test_verify_export_bundle_catches_missing_manifest(self):
        bundle_path = self.tmp_path("broken_missing_manifest.zip")
        with zipfile.ZipFile(bundle_path, "w") as bundle:
            bundle.writestr("experiment_request.json", "{}")

        result = validate_export_bundle(bundle_path)

        self.assertEqual(result["bundle_validation_status"], "failed_export_bundle_checks")
        self.assertIn("Missing export manifest", "\n".join(result["export_bundle_errors"]))

    def test_verify_export_bundle_catches_hash_mismatch(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_verify_hash_mismatch"))
        bundle_path = run_dir.parent / "trace_lab_export.zip"
        write_export_bundle(run_dir, bundle_path)

        broken_path = run_dir.parent / "trace_lab_export_broken.zip"
        self.rewrite_zip_member(
            bundle_path,
            broken_path,
            "experiment_request.json",
            b'{"record_type":"experiment_request","tampered":true}\n',
        )

        result = validate_export_bundle(broken_path)

        self.assertEqual(result["bundle_validation_status"], "failed_export_bundle_checks")
        self.assertIn("hash mismatch", "\n".join(result["export_bundle_errors"]))

    def test_verify_export_bundle_catches_unsafe_manifest_path(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_verify_unsafe_path"))
        bundle_path = run_dir.parent / "trace_lab_export.zip"
        write_export_bundle(run_dir, bundle_path)

        broken_path = run_dir.parent / "trace_lab_export_unsafe.zip"
        with zipfile.ZipFile(bundle_path) as source:
            manifest = json.loads(source.read(EXPORT_MANIFEST_NAME).decode("utf-8"))
            manifest["bundle_files"][0]["path"] = "../outside.json"
            with zipfile.ZipFile(broken_path, "w", compression=zipfile.ZIP_DEFLATED) as target:
                for name in source.namelist():
                    if name == EXPORT_MANIFEST_NAME:
                        target.writestr(name, json.dumps(manifest, indent=2, sort_keys=True) + "\n")
                    else:
                        target.writestr(name, source.read(name))

        result = validate_export_bundle(broken_path)

        self.assertEqual(result["bundle_validation_status"], "failed_export_bundle_checks")
        self.assertIn("unsafe path", "\n".join(result["export_bundle_errors"]))

    def test_verify_export_bundle_catches_authority_escalation(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_verify_authority"))
        bundle_path = run_dir.parent / "trace_lab_export.zip"
        write_export_bundle(run_dir, bundle_path)

        broken_path = run_dir.parent / "trace_lab_export_authority.zip"
        with zipfile.ZipFile(bundle_path) as source:
            manifest = json.loads(source.read(EXPORT_MANIFEST_NAME).decode("utf-8"))
            manifest["authority_flags"]["scientific_truth_validated"] = True
            with zipfile.ZipFile(broken_path, "w", compression=zipfile.ZIP_DEFLATED) as target:
                for name in source.namelist():
                    if name == EXPORT_MANIFEST_NAME:
                        target.writestr(name, json.dumps(manifest, indent=2, sort_keys=True) + "\n")
                    else:
                        target.writestr(name, source.read(name))

        result = validate_export_bundle(broken_path)

        self.assertEqual(result["bundle_validation_status"], "failed_export_bundle_checks")
        self.assertIn("authority flag", "\n".join(result["export_bundle_errors"]))

    def test_cli_verify_bundle_returns_failure_for_broken_bundle(self):
        bundle_path = self.tmp_path("broken_cli_bundle.zip")
        with zipfile.ZipFile(bundle_path, "w") as bundle:
            bundle.writestr("not_manifest.json", "{}")
        stdout = io.StringIO()

        with redirect_stdout(stdout):
            code = cli_main(["verify-bundle", "--bundle", str(bundle_path)])

        result = json.loads(stdout.getvalue())
        self.assertEqual(code, 1)
        self.assertEqual(result["bundle_validation_status"], "failed_export_bundle_checks")


    def test_verify_export_bundle_validation_result_writer_creates_sidecar(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_verify_sidecar"))
        bundle_path = run_dir.parent / "trace_lab_export.zip"
        write_export_bundle(run_dir, bundle_path)

        result_path = write_export_bundle_validation_result(bundle_path)

        self.assertEqual(result_path, default_export_bundle_validation_result_path(bundle_path))
        self.assertTrue(result_path.exists())
        result = self.read_json(result_path)
        self.assertEqual(result["record_type"], "trace_lab_export_bundle_validation")
        self.assertEqual(result["bundle_validation_status"], "passed_export_bundle_checks")
        self.assertEqual(result["result_scope"], "local_export_bundle_integrity_only")
        self.assertFalse(result["package_execution_performed"])
        self.assertFalse(result["bundle_unpacked"])
        self.assertFalse(result["network_calls_performed"])
        self.assertFalse(result["hardware_access_performed"])
        self.assertFalse(result["scientific_truth_validated"])
        self.assertFalse(result["claims_promoted"])

    def test_verify_export_bundle_validation_result_writer_refuses_silent_overwrite(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_verify_sidecar_overwrite"))
        bundle_path = run_dir.parent / "trace_lab_export.zip"
        write_export_bundle(run_dir, bundle_path)
        write_export_bundle_validation_result(bundle_path)

        with self.assertRaises(FileExistsError):
            write_export_bundle_validation_result(bundle_path)

    def test_cli_verify_bundle_write_result_creates_sidecar(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_cli_verify_sidecar"))
        bundle_path = run_dir.parent / "trace_lab_export.zip"
        write_export_bundle(run_dir, bundle_path)
        stdout = io.StringIO()

        with redirect_stdout(stdout):
            code = cli_main(["verify-bundle", "--bundle", str(bundle_path), "--write-result"])

        result = json.loads(stdout.getvalue())
        self.assertEqual(code, 0)
        self.assertEqual(result["bundle_validation_status"], "passed_export_bundle_checks")
        self.assertIn("validation_result_path", result)
        self.assertTrue(default_export_bundle_validation_result_path(bundle_path).exists())

    def test_cli_verify_bundle_write_result_refuses_silent_overwrite(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_cli_verify_sidecar_overwrite"))
        bundle_path = run_dir.parent / "trace_lab_export.zip"
        write_export_bundle(run_dir, bundle_path)
        write_export_bundle_validation_result(bundle_path)
        stderr = io.StringIO()

        with redirect_stderr(stderr):
            code = cli_main(["verify-bundle", "--bundle", str(bundle_path), "--write-result"])

        self.assertEqual(code, 1)
        self.assertIn("refuses to overwrite", stderr.getvalue())

    def test_cli_verify_bundle_write_result_can_use_explicit_result_out(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_cli_verify_sidecar_explicit"))
        bundle_path = run_dir.parent / "trace_lab_export.zip"
        result_path = run_dir.parent / "custom_bundle_validation.json"
        write_export_bundle(run_dir, bundle_path)
        stdout = io.StringIO()

        with redirect_stdout(stdout):
            code = cli_main([
                "verify-bundle",
                "--bundle",
                str(bundle_path),
                "--write-result",
                "--result-out",
                str(result_path),
            ])

        result = json.loads(stdout.getvalue())
        self.assertEqual(code, 0)
        self.assertEqual(result["validation_result_path"], str(result_path))
        self.assertTrue(result_path.exists())

    def test_verify_bundle_write_result_persists_failed_bundle_result(self):
        bundle_path = self.tmp_path("broken_sidecar_bundle.zip")
        result_path = bundle_path.with_name("broken_sidecar_bundle.validation.json")
        with zipfile.ZipFile(bundle_path, "w") as bundle:
            bundle.writestr("not_manifest.json", "{}")

        written = write_export_bundle_validation_result(bundle_path, out_path=result_path)

        result = self.read_json(written)
        self.assertEqual(result["bundle_validation_status"], "failed_export_bundle_checks")
        self.assertTrue(result["export_bundle_errors"])
        self.assertFalse(result["scientific_truth_validated"])
        self.assertFalse(result["claims_promoted"])


    def test_markdown_report_preserves_authority_boundary(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_report_boundary"))

        report = build_markdown_report(run_dir)

        self.assertIn("# TraceLab Local Evidence Report", report)
        self.assertIn("operational_simulation_only", report)
        self.assertIn("evidence != truth", report)
        self.assertIn("does not validate scientific truth", report)
        self.assertIn("`scientific_truth_validated`: `false`", report)
        self.assertIn("`physical_execution_completed`: `false`", report)
        self.assertIn("`claims_promoted`: `false`", report)

    def test_markdown_report_writer_creates_report_file(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_report_write"))

        report_path = write_markdown_report(run_dir)

        self.assertEqual(report_path, run_dir / REPORT_FILE)
        self.assertTrue(report_path.exists())
        self.assertIn("TraceLab Local Evidence Report", report_path.read_text(encoding="utf-8"))

    def test_markdown_report_writer_refuses_silent_overwrite(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_report_overwrite"))
        write_markdown_report(run_dir)

        with self.assertRaises(FileExistsError):
            write_markdown_report(run_dir)

    def test_cli_report_outputs_markdown_boundary(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_cli_report"))
        stdout = io.StringIO()

        with redirect_stdout(stdout):
            code = cli_main(["report", "--run-dir", str(run_dir)])

        report = stdout.getvalue()
        self.assertEqual(code, 0)
        self.assertIn("TraceLab Local Evidence Report", report)
        self.assertIn("evidence != truth", report)
        self.assertIn("does not validate scientific truth", report)

    def test_cli_report_write_creates_report_file(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_cli_report_write"))
        stdout = io.StringIO()

        with redirect_stdout(stdout):
            code = cli_main(["report", "--run-dir", str(run_dir), "--write"])

        self.assertEqual(code, 0)
        self.assertTrue((run_dir / REPORT_FILE).exists())
        self.assertIn(str(run_dir / REPORT_FILE), stdout.getvalue())

    def test_cli_report_write_refuses_silent_overwrite(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_cli_report_overwrite"))
        write_markdown_report(run_dir)
        stderr = io.StringIO()

        with redirect_stderr(stderr):
            code = cli_main(["report", "--run-dir", str(run_dir), "--write"])

        self.assertEqual(code, 1)
        self.assertIn("refuses to overwrite", stderr.getvalue())

    def test_export_bundle_includes_report_when_written(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_report_export"))
        write_markdown_report(run_dir)
        bundle_path = run_dir.parent / "trace_lab_export.zip"

        write_export_bundle(run_dir, bundle_path)

        with zipfile.ZipFile(bundle_path) as bundle:
            self.assertIn(REPORT_FILE, bundle.namelist())

    def test_neuml_handoff_includes_report_candidate_when_written(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_report_handoff"))
        write_markdown_report(run_dir)

        handoff_path = write_neuml_handoff_manifest(run_dir)
        handoff = self.read_json(handoff_path)

        self.assertIn(REPORT_FILE, handoff["report_candidates"])




    def test_verify_markdown_report_passes_for_written_report(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_report_verify_pass"))
        write_markdown_report(run_dir)

        result = validate_markdown_report(run_dir)

        self.assertEqual(result["record_type"], "trace_lab_report_validation")
        self.assertEqual(result["report_validation_status"], "passed_report_boundary_checks")
        self.assertEqual(result["report_errors"], [])
        self.assertEqual(result["unsafe"], [])
        self.assertFalse(result["authority_flags"]["scientific_truth_validated"])

    def test_verify_markdown_report_catches_missing_report(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_report_verify_missing"))

        result = validate_markdown_report(run_dir)

        self.assertEqual(result["report_validation_status"], "failed_report_boundary_checks")
        self.assertTrue(result["report_errors"])

    def test_verify_markdown_report_catches_missing_boundary_note(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_report_verify_boundary"))
        report_path = write_markdown_report(run_dir)
        text = report_path.read_text(encoding="utf-8").replace("- evidence != truth\n", "")
        report_path.write_text(text, encoding="utf-8")

        result = validate_markdown_report(run_dir)

        self.assertEqual(result["report_validation_status"], "failed_report_boundary_checks")
        self.assertIn("Markdown report missing boundary note: evidence != truth", result["report_errors"])

    def test_validation_catches_optional_report_authority_drift(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_report_drift"))
        report_path = write_markdown_report(run_dir)
        text = report_path.read_text(encoding="utf-8").replace(
            "`scientific_truth_validated`: `false`",
            "`scientific_truth_validated`: `true`",
        )
        report_path.write_text(text, encoding="utf-8")

        result = validate_run(run_dir)

        self.assertEqual(result["validation_status"], "failed_operational_checks")
        self.assertTrue(result["report_errors"])
        self.assertTrue(result["unsafe"])

    def test_report_validation_result_writer_creates_sidecar(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_report_validation_sidecar"))
        report_path = write_markdown_report(run_dir)

        result_path = write_markdown_report_validation_result(run_dir)

        self.assertEqual(result_path, default_report_validation_result_path(report_path))
        record = self.read_json(result_path)
        self.assertEqual(record["record_type"], "trace_lab_report_validation")
        self.assertEqual(record["report_validation_status"], "passed_report_boundary_checks")
        self.assertFalse(record["scientific_truth_validated"])
        self.assertFalse(record["claims_promoted"])

    def test_report_validation_result_writer_refuses_silent_overwrite(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_report_validation_overwrite"))
        write_markdown_report(run_dir)
        write_markdown_report_validation_result(run_dir)

        with self.assertRaises(FileExistsError):
            write_markdown_report_validation_result(run_dir)

    def test_cli_verify_report_outputs_passed_status(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_cli_verify_report"))
        write_markdown_report(run_dir)
        stdout = io.StringIO()

        with redirect_stdout(stdout):
            code = cli_main(["verify-report", "--run-dir", str(run_dir)])

        result = json.loads(stdout.getvalue())
        self.assertEqual(code, 0)
        self.assertEqual(result["report_validation_status"], "passed_report_boundary_checks")
        self.assertEqual(result["report_errors"], [])

    def test_cli_verify_report_returns_failure_for_broken_report(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_cli_verify_report_broken"))
        report_path = write_markdown_report(run_dir)
        report_path.write_text("# Broken report\n", encoding="utf-8")
        stdout = io.StringIO()

        with redirect_stdout(stdout):
            code = cli_main(["verify-report", "--run-dir", str(run_dir)])

        result = json.loads(stdout.getvalue())
        self.assertEqual(code, 1)
        self.assertEqual(result["report_validation_status"], "failed_report_boundary_checks")
        self.assertTrue(result["report_errors"])

    def test_cli_verify_report_write_result_creates_sidecar(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_cli_verify_report_sidecar"))
        report_path = write_markdown_report(run_dir)
        stdout = io.StringIO()

        with redirect_stdout(stdout):
            code = cli_main(["verify-report", "--run-dir", str(run_dir), "--write-result"])

        result = json.loads(stdout.getvalue())
        result_path = default_report_validation_result_path(report_path)
        self.assertEqual(code, 0)
        self.assertTrue(result_path.exists())
        self.assertEqual(result["validation_result_path"], str(result_path))

    def test_cli_verify_report_write_result_refuses_silent_overwrite(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_cli_verify_report_overwrite"))
        write_markdown_report(run_dir)
        write_markdown_report_validation_result(run_dir)
        stderr = io.StringIO()

        with redirect_stderr(stderr):
            code = cli_main(["verify-report", "--run-dir", str(run_dir), "--write-result"])

        self.assertEqual(code, 1)
        self.assertIn("refuses to overwrite", stderr.getvalue())

    def test_export_bundle_includes_report_validation_sidecar_when_written(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_report_validation_export"))
        write_markdown_report(run_dir)
        write_markdown_report_validation_result(run_dir)
        bundle_path = run_dir.parent / "trace_lab_export.zip"

        write_export_bundle(run_dir, bundle_path)

        with zipfile.ZipFile(bundle_path) as bundle:
            self.assertIn("trace_lab_report.md.validation.json", bundle.namelist())


    def test_execution_policy_manifest_preserves_no_hidden_retry_boundary(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_execution_policy"))
        policy = self.read_json(run_dir / "execution_policy_manifest.json")

        self.assertEqual(policy["record_type"], "execution_policy_manifest")
        self.assertEqual(policy["policy_scope"], "operational_simulation_only")
        self.assertEqual(policy["execution_mode"], "simulated")
        self.assertFalse(policy["physical_execution_allowed"])
        self.assertFalse(policy["automatic_retry_allowed"])
        self.assertFalse(policy["automatic_retry_performed"])
        self.assertFalse(policy["hidden_retry_allowed"])
        self.assertEqual(policy["retry_attempt_count"], 0)
        self.assertTrue(policy["human_approval_required_for_retry"])
        self.assertFalse(policy["agent_can_approve_retry"])
        self.assertIn("silent_retry", policy["blocked_actions"])
        self.assertIn("dry-run != physical execution", policy["boundary_notes"])

    def test_execution_policy_summary_outputs_simulation_policy_boundary(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_execution_policy_summary"))

        summary = build_execution_policy_summary(run_dir)

        self.assertEqual(summary["record_type"], "execution_policy_summary")
        self.assertEqual(summary["policy_summary_status"], "simulation_policy_intact")
        self.assertEqual(summary["execution_mode"], "simulated")
        self.assertFalse(summary["automatic_retry_allowed"])
        self.assertFalse(summary["automatic_retry_performed"])
        self.assertEqual(summary["retry_attempt_count"], 0)
        self.assertEqual(summary["policy_errors"], [])
        self.assertEqual(summary["unsafe"], [])

    def test_validation_catches_execution_policy_retry_claim(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_execution_policy_retry_drift"))
        policy_path = run_dir / "execution_policy_manifest.json"
        policy = self.read_json(policy_path)
        policy["automatic_retry_performed"] = True
        policy["retry_attempt_count"] = 1
        self.write_json(policy_path, policy)
        write_run_manifest(run_dir, force=True)

        result = validate_run(run_dir)

        self.assertEqual(result["validation_status"], "failed_operational_checks")
        self.assertTrue(result["unsafe"])
        self.assertTrue(any("automatic_retry_performed" in item for item in result["unsafe"]))

    def test_validation_catches_execution_policy_missing_blocked_action(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_execution_policy_blocked_action"))
        policy_path = run_dir / "execution_policy_manifest.json"
        policy = self.read_json(policy_path)
        policy["blocked_actions"].remove("silent_retry")
        self.write_json(policy_path, policy)
        write_run_manifest(run_dir, force=True)

        result = validate_run(run_dir)

        self.assertEqual(result["validation_status"], "failed_operational_checks")
        self.assertTrue(result["policy_errors"])
        self.assertTrue(any("silent_retry" in item for item in result["policy_errors"]))

    def test_cli_policy_summary_outputs_no_retry_boundary(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_cli_policy_summary"))
        stdout = io.StringIO()

        with redirect_stdout(stdout):
            code = cli_main(["policy-summary", "--run-dir", str(run_dir)])

        result = json.loads(stdout.getvalue())
        self.assertEqual(code, 0)
        self.assertEqual(result["policy_summary_status"], "simulation_policy_intact")
        self.assertFalse(result["automatic_retry_allowed"])

    def test_cli_policy_summary_write_creates_summary_file(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_cli_policy_summary_write"))
        stdout = io.StringIO()

        with redirect_stdout(stdout):
            code = cli_main(["policy-summary", "--run-dir", str(run_dir), "--write"])

        self.assertEqual(code, 0)
        path = run_dir / "execution_policy_summary.json"
        self.assertTrue(path.exists())
        self.assertIn(str(path), stdout.getvalue())

    def test_neuml_handoff_includes_execution_policy_record(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_handoff_execution_policy"))
        handoff = self.read_json(run_dir / "neuml_handoff_manifest.json")

        self.assertIn("execution_policy_manifest.json", handoff["records_included"])
        self.assertIn("execution_policy_manifest.json", handoff["text_index_candidates"])
        self.assertIn("execution_policy_manifest.json", handoff["report_candidates"])

    def test_export_bundle_includes_policy_summary_when_written(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_export_policy_summary"))
        from trace_lab.execution_policy import write_execution_policy_summary

        write_execution_policy_summary(run_dir)
        bundle_path = run_dir.parent / "trace_lab_export.zip"

        write_export_bundle(run_dir, bundle_path)

        with zipfile.ZipFile(bundle_path) as bundle:
            self.assertIn("execution_policy_summary.json", bundle.namelist())



    def test_telemetry_profile_manifest_records_data_shape_only(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_telemetry_profile_manifest"))
        profile = self.read_json(run_dir / "telemetry_profile_manifest.json")

        self.assertEqual(profile["record_type"], "telemetry_profile_manifest")
        self.assertEqual(profile["profile_scope"], "operational_data_shape_only")
        self.assertEqual(profile["profile_status"], "profiled_simulated_telemetry")
        self.assertEqual(profile["data_file_count"], 1)
        self.assertFalse(profile["authority_flags"]["scientific_truth_validated"])
        self.assertFalse(profile["authority_flags"]["physical_execution_completed"])
        self.assertFalse(profile["authority_flags"]["claims_promoted"])
        self.assertIn("evidence != truth", profile["boundary_notes"])

        data_profile = profile["data_profiles"][0]
        self.assertEqual(data_profile["path"], "telemetry/simulated_flow_sensor_A.csv")
        self.assertEqual(data_profile["column_names"], ["t", "flow"])
        self.assertEqual(data_profile["row_count"], 3)
        self.assertTrue(data_profile["hash_matches_telemetry_manifest"])
        self.assertTrue(data_profile["data_shape_only"])

    def test_validation_catches_missing_telemetry_profile_manifest(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_missing_telemetry_profile"))
        (run_dir / "telemetry_profile_manifest.json").unlink()
        result = validate_run(run_dir)

        self.assertEqual(result["validation_status"], "failed_operational_checks")
        self.assertIn("telemetry_profile_manifest.json", result["missing"])

    def test_validation_catches_telemetry_profile_row_count_drift(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_telemetry_profile_row_drift"))
        profile_path = run_dir / "telemetry_profile_manifest.json"
        profile = self.read_json(profile_path)
        profile["data_profiles"][0]["row_count"] = 999
        self.write_json(profile_path, profile)

        result = validate_run(run_dir)

        self.assertEqual(result["validation_status"], "failed_operational_checks")
        self.assertTrue(
            any("row_count mismatch" in error for error in result["telemetry_profile_errors"]),
            result["telemetry_profile_errors"],
        )

    def test_validation_catches_telemetry_profile_authority_escalation(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_telemetry_profile_authority"))
        profile_path = run_dir / "telemetry_profile_manifest.json"
        profile = self.read_json(profile_path)
        profile["authority_flags"]["scientific_truth_validated"] = True
        self.write_json(profile_path, profile)

        result = validate_run(run_dir)

        self.assertEqual(result["validation_status"], "failed_operational_checks")
        self.assertTrue(
            any("scientific_truth_validated" in item for item in result["unsafe"]),
            result["unsafe"],
        )

    def test_cli_telemetry_profile_outputs_data_shape_boundary(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_cli_telemetry_profile"))
        stdout = io.StringIO()

        with redirect_stdout(stdout):
            code = cli_main(["telemetry-profile", "--run-dir", str(run_dir)])

        result = json.loads(stdout.getvalue())
        self.assertEqual(code, 0)
        self.assertEqual(result["record_type"], "telemetry_profile_summary")
        self.assertEqual(result["telemetry_profile_validation_status"], "passed_telemetry_profile_checks")
        self.assertEqual(result["total_row_count"], 3)
        self.assertIn("evidence != truth", result["boundary_notes"])

    def test_cli_telemetry_profile_write_creates_summary_file(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_cli_telemetry_profile_write"))
        stdout = io.StringIO()

        with redirect_stdout(stdout):
            code = cli_main(["telemetry-profile", "--run-dir", str(run_dir), "--write"])

        self.assertEqual(code, 0)
        path = run_dir / "telemetry_profile_summary.json"
        self.assertTrue(path.exists())
        self.assertIn(str(path), stdout.getvalue())

    def test_cli_telemetry_profile_write_manifest_refuses_silent_overwrite(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_cli_telemetry_profile_manifest_overwrite"))
        stderr = io.StringIO()

        with redirect_stderr(stderr):
            code = cli_main(["telemetry-profile", "--run-dir", str(run_dir), "--write-manifest"])

        self.assertEqual(code, 1)
        self.assertIn("refuses to overwrite", stderr.getvalue())

    def test_export_bundle_includes_telemetry_profile_summary_when_written(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_export_telemetry_profile_summary"))
        write_telemetry_profile_summary(run_dir)
        bundle_path = run_dir.parent / "trace_lab_export.zip"

        write_export_bundle(run_dir, bundle_path)

        with zipfile.ZipFile(bundle_path) as bundle:
            self.assertIn("telemetry_profile_summary.json", bundle.namelist())

    def test_neuml_handoff_includes_telemetry_profile_record(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_handoff_telemetry_profile"))
        handoff = self.read_json(run_dir / "neuml_handoff_manifest.json")

        self.assertIn("telemetry_profile_manifest.json", handoff["records_included"])
        self.assertIn("telemetry_profile_manifest.json", handoff["text_index_candidates"])
        self.assertIn("telemetry_profile_manifest.json", handoff["report_candidates"])

    def test_markdown_report_includes_telemetry_profile_section(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_report_telemetry_profile"))
        report = build_markdown_report(run_dir)

        self.assertIn("## Telemetry profile", report)
        self.assertIn("Profile status", report)
        self.assertIn("Total row count", report)


    def test_ingestion_preview_manifest_records_local_preview_only(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_ingestion_preview_manifest"))
        manifest = self.read_json(run_dir / "ingestion_preview_manifest.json")

        self.assertEqual(manifest["record_type"], "ingestion_preview_manifest")
        self.assertEqual(manifest["preview_scope"], "local_index_preview_only")
        self.assertFalse(manifest["authority_flags"]["network_calls_performed"])
        self.assertFalse(manifest["authority_flags"]["model_calls_performed"])
        self.assertFalse(manifest["authority_flags"]["external_ingestion_performed"])
        self.assertFalse(manifest["authority_flags"]["scientific_truth_validated"])
        self.assertFalse(manifest["authority_flags"]["claims_promoted"])
        self.assertIn("evidence != truth", manifest["boundary_notes"])

    def test_validation_catches_missing_ingestion_preview_manifest(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_missing_ingestion_preview"))
        (run_dir / "ingestion_preview_manifest.json").unlink()
        write_run_manifest(run_dir, force=True)

        result = validate_run(run_dir)

        self.assertEqual(result["validation_status"], "failed_operational_checks")
        self.assertIn("ingestion_preview_manifest.json", result["missing"])

    def test_validation_catches_ingestion_preview_authority_escalation(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_ingestion_preview_authority"))
        manifest_path = run_dir / "ingestion_preview_manifest.json"
        manifest = self.read_json(manifest_path)
        manifest["authority_flags"]["external_ingestion_performed"] = True
        self.write_json(manifest_path, manifest)
        write_run_manifest(run_dir, force=True)

        result = validate_run(run_dir)

        self.assertEqual(result["validation_status"], "failed_operational_checks")
        self.assertTrue(any("external_ingestion_performed" in item for item in result["ingestion_errors"]))

    def test_validation_catches_ingestion_preview_unsafe_candidate_path(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_ingestion_preview_path"))
        manifest_path = run_dir / "ingestion_preview_manifest.json"
        manifest = self.read_json(manifest_path)
        manifest["text_index_candidates"].append({"path": "../outside.json", "exists": True})
        manifest["candidate_count"] += 1
        self.write_json(manifest_path, manifest)
        write_run_manifest(run_dir, force=True)

        result = validate_run(run_dir)

        self.assertEqual(result["validation_status"], "failed_operational_checks")
        self.assertTrue(any("must stay inside run directory" in item for item in result["ingestion_errors"]))

    def test_validation_catches_ingestion_preview_candidate_count_drift(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_ingestion_preview_count"))
        manifest_path = run_dir / "ingestion_preview_manifest.json"
        manifest = self.read_json(manifest_path)
        manifest["candidate_count"] = 1
        self.write_json(manifest_path, manifest)
        write_run_manifest(run_dir, force=True)

        result = validate_run(run_dir)

        self.assertEqual(result["validation_status"], "failed_operational_checks")
        self.assertTrue(any("candidate_count" in item for item in result["ingestion_errors"]))

    def test_cli_ingestion_preview_outputs_local_index_boundary(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_cli_ingestion_preview"))
        stdout = io.StringIO()

        with redirect_stdout(stdout):
            code = cli_main(["ingestion-preview", "--run-dir", str(run_dir)])

        result = json.loads(stdout.getvalue())
        self.assertEqual(code, 0)
        self.assertEqual(result["record_type"], "ingestion_preview_summary")
        self.assertEqual(result["ingestion_preview_status"], "ready_for_future_local_indexing")
        self.assertFalse(result["authority_flags"]["external_ingestion_performed"])
        self.assertIn("evidence != truth", result["boundary_notes"])

    def test_cli_ingestion_preview_write_creates_summary_file(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_cli_ingestion_preview_write"))
        stdout = io.StringIO()

        with redirect_stdout(stdout):
            code = cli_main(["ingestion-preview", "--run-dir", str(run_dir), "--write"])

        self.assertEqual(code, 0)
        path = run_dir / "ingestion_preview_summary.json"
        self.assertTrue(path.exists())
        self.assertIn(str(path), stdout.getvalue())

    def test_cli_ingestion_preview_write_manifest_refuses_silent_overwrite(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_cli_ingestion_preview_manifest_overwrite"))
        stderr = io.StringIO()

        with redirect_stderr(stderr):
            code = cli_main(["ingestion-preview", "--run-dir", str(run_dir), "--write-manifest"])

        self.assertEqual(code, 1)
        self.assertIn("refuses to overwrite", stderr.getvalue())

    def test_export_bundle_includes_ingestion_preview_summary_when_written(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_export_ingestion_preview_summary"))
        write_ingestion_preview_summary(run_dir)
        bundle_path = run_dir.parent / "trace_lab_export.zip"

        write_export_bundle(run_dir, bundle_path)

        with zipfile.ZipFile(bundle_path) as bundle:
            self.assertIn("ingestion_preview_summary.json", bundle.namelist())

    def test_neuml_handoff_includes_ingestion_preview_record_after_rebuild(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_handoff_ingestion_preview"))
        write_neuml_handoff_manifest(run_dir)
        handoff = self.read_json(run_dir / "neuml_handoff_manifest.json")

        self.assertIn("ingestion_preview_manifest.json", handoff["records_included"])
        self.assertIn("ingestion_preview_manifest.json", handoff["text_index_candidates"])
        self.assertIn("ingestion_preview_manifest.json", handoff["report_candidates"])

    def test_markdown_report_includes_ingestion_preview_section(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_report_ingestion_preview"))
        report = build_markdown_report(run_dir)

        self.assertIn("## Ingestion preview", report)
        self.assertIn("Preview status", report)
        self.assertIn("Text candidates", report)


    def test_provenance_manifest_records_local_origin_boundary(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_provenance_manifest"))
        manifest = self.read_json(run_dir / "provenance_manifest.json")

        self.assertEqual(manifest["record_type"], "provenance_manifest")
        self.assertEqual(manifest["provenance_scope"], "operational_trace_provenance_only")
        self.assertEqual(manifest["source_system"], "trace_lab_v0_1_simulated_scaffold")
        self.assertFalse(manifest["authority_flags"]["agent_approved"])
        self.assertFalse(manifest["authority_flags"]["scientific_truth_validated"])
        self.assertFalse(manifest["authority_flags"]["physical_execution_completed"])
        self.assertFalse(manifest["authority_flags"]["state_promoted"])
        self.assertIn("simulated adapter != hardware adapter", manifest["boundary_notes"])
        self.assertTrue(any(item["path"] == "experiment_request.json" for item in manifest["records"]))

    def test_cli_provenance_summary_outputs_local_origin_boundary(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_cli_provenance_summary"))
        stdout = io.StringIO()

        with redirect_stdout(stdout):
            code = cli_main(["provenance-summary", "--run-dir", str(run_dir)])

        output = stdout.getvalue()
        self.assertEqual(code, 0)
        self.assertIn("provenance_recorded", output)
        self.assertIn("operational_trace_provenance_only", output)
        self.assertIn("does not validate scientific truth", output)

    def test_cli_provenance_summary_write_creates_summary_file(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_cli_provenance_write"))
        stdout = io.StringIO()

        with redirect_stdout(stdout):
            code = cli_main(["provenance-summary", "--run-dir", str(run_dir), "--write"])

        self.assertEqual(code, 0)
        path = run_dir / "provenance_summary.json"
        self.assertTrue(path.exists())
        self.assertIn(str(path), stdout.getvalue())

    def test_cli_provenance_summary_write_manifest_refuses_silent_overwrite(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_cli_provenance_manifest_overwrite"))
        stderr = io.StringIO()

        with redirect_stderr(stderr):
            code = cli_main(["provenance-summary", "--run-dir", str(run_dir), "--write-manifest"])

        self.assertEqual(code, 1)
        self.assertIn("refuses to overwrite", stderr.getvalue())

    def test_validation_catches_missing_provenance_manifest(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_missing_provenance"))
        (run_dir / "provenance_manifest.json").unlink()

        result = validate_run(run_dir)

        self.assertEqual(result["validation_status"], "failed_operational_checks")
        self.assertIn("provenance_manifest.json", result["missing"])
        self.assertTrue(result["provenance_errors"])

    def test_validation_catches_provenance_authority_escalation(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_provenance_authority"))
        path = run_dir / "provenance_manifest.json"
        manifest = self.read_json(path)
        manifest["authority_flags"]["scientific_truth_validated"] = True
        self.write_json(path, manifest)

        result = validate_run(run_dir)

        self.assertEqual(result["validation_status"], "failed_operational_checks")
        self.assertTrue(any("scientific_truth_validated" in item for item in result["unsafe"]))

    def test_validation_catches_provenance_hash_mismatch(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_provenance_hash"))
        request_path = run_dir / "experiment_request.json"
        request = self.read_json(request_path)
        request["status"] = "changed_after_provenance"
        self.write_json(request_path, request)

        result = validate_run(run_dir)

        self.assertEqual(result["validation_status"], "failed_operational_checks")
        self.assertTrue(any("hash mismatch" in item for item in result["provenance_errors"]))

    def test_export_bundle_includes_provenance_summary_when_written(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_export_provenance_summary"))
        write_provenance_summary(run_dir)
        bundle_path = run_dir.parent / "trace_lab_export.zip"

        write_export_bundle(run_dir, bundle_path)

        with zipfile.ZipFile(bundle_path) as bundle:
            self.assertIn("provenance_summary.json", bundle.namelist())

    def test_neuml_handoff_includes_provenance_record(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_handoff_provenance"))
        write_neuml_handoff_manifest(run_dir)
        handoff = self.read_json(run_dir / "neuml_handoff_manifest.json")

        self.assertIn("provenance_manifest.json", handoff["records_included"])
        self.assertIn("provenance_manifest.json", handoff["text_index_candidates"])
        self.assertIn("provenance_manifest.json", handoff["report_candidates"])

    def test_markdown_report_includes_provenance_section(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_report_provenance"))
        report = build_markdown_report(run_dir)

        self.assertIn("## Provenance", report)
        self.assertIn("Provenance status", report)
        self.assertIn("Source system", report)



    def test_closeout_manifest_records_operational_stop_line_only(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_closeout_manifest"))
        closeout = self.read_json(run_dir / "run_closeout_manifest.json")

        self.assertEqual(closeout["record_type"], "run_closeout_manifest")
        self.assertEqual(closeout["closeout_scope"], "operational_trace_closeout_only")
        self.assertEqual(closeout["closeout_status"], "ready_for_operator_review_and_local_export")
        self.assertFalse(closeout["authority_flags"]["agent_approved"])
        self.assertFalse(closeout["authority_flags"]["human_review_completed"])
        self.assertFalse(closeout["authority_flags"]["scientific_truth_validated"])
        self.assertFalse(closeout["authority_flags"]["state_promoted"])
        self.assertIn("evidence != truth", closeout["boundary_notes"])

    def test_cli_closeout_summary_outputs_stop_line_boundary(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_cli_closeout"))
        stdout = io.StringIO()

        with redirect_stdout(stdout):
            exit_code = cli_main(["closeout-summary", "--run-dir", str(run_dir)])

        self.assertEqual(exit_code, 0)
        summary = json.loads(stdout.getvalue())
        self.assertEqual(summary["record_type"], "run_closeout_summary")
        self.assertEqual(summary["closeout_summary_status"], "ready_for_operator_review_and_local_export")
        self.assertFalse(summary["authority_flags"]["agent_approved"])
        self.assertFalse(summary["authority_flags"]["human_review_completed"])
        self.assertIn("operator-facing stop-line", summary["authority_note"])

    def test_cli_closeout_summary_write_creates_summary_file(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_cli_closeout_write"))

        exit_code = cli_main(["closeout-summary", "--run-dir", str(run_dir), "--write"])

        self.assertEqual(exit_code, 0)
        self.assertTrue((run_dir / "run_closeout_summary.json").exists())

    def test_cli_closeout_summary_write_manifest_refuses_silent_overwrite(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_cli_closeout_overwrite"))
        stderr = io.StringIO()

        with redirect_stderr(stderr):
            exit_code = cli_main(["closeout-summary", "--run-dir", str(run_dir), "--write-manifest"])

        self.assertEqual(exit_code, 1)
        self.assertIn("refuses to overwrite run_closeout_manifest.json", stderr.getvalue())

    def test_validation_catches_missing_closeout_manifest(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_missing_closeout"))
        (run_dir / "run_closeout_manifest.json").unlink()

        result = validate_run(run_dir)

        self.assertEqual(result["validation_status"], "failed_operational_checks")
        self.assertIn("run_closeout_manifest.json", result["missing"])
        self.assertTrue(any("Missing run closeout manifest" in item for item in result["closeout_errors"]))

    def test_validation_catches_closeout_authority_escalation(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_closeout_authority"))
        path = run_dir / "run_closeout_manifest.json"
        closeout = self.read_json(path)
        closeout["authority_flags"]["claims_promoted"] = True
        self.write_json(path, closeout)

        result = validate_run(run_dir)

        self.assertEqual(result["validation_status"], "failed_operational_checks")
        self.assertTrue(any("claims_promoted" in item for item in result["unsafe"]))

    def test_validation_catches_closeout_hash_mismatch(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_closeout_hash"))
        request_path = run_dir / "experiment_request.json"
        request = self.read_json(request_path)
        request["status"] = "changed_after_closeout"
        self.write_json(request_path, request)

        result = validate_run(run_dir)

        self.assertEqual(result["validation_status"], "failed_operational_checks")
        self.assertTrue(any("hash mismatch" in item for item in result["closeout_errors"]))

    def test_export_bundle_includes_closeout_summary_when_written(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_export_closeout_summary"))
        write_run_closeout_summary(run_dir)
        bundle_path = run_dir.parent / "trace_lab_export.zip"

        write_export_bundle(run_dir, bundle_path)

        with zipfile.ZipFile(bundle_path) as bundle:
            self.assertIn("run_closeout_summary.json", bundle.namelist())

    def test_neuml_handoff_includes_closeout_record(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_handoff_closeout"))
        write_neuml_handoff_manifest(run_dir)
        handoff = self.read_json(run_dir / "neuml_handoff_manifest.json")

        self.assertIn("run_closeout_manifest.json", handoff["records_included"])
        self.assertIn("run_closeout_manifest.json", handoff["text_index_candidates"])
        self.assertIn("run_closeout_manifest.json", handoff["report_candidates"])

    def test_markdown_report_includes_closeout_section(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_report_closeout"))
        report = build_markdown_report(run_dir)

        self.assertIn("## Run closeout", report)
        self.assertIn("Closeout status", report)
        self.assertIn("Required next actions", report)

    def test_claim_ledger_manifest_records_claim_boundary_only(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_claim_ledger"))
        ledger = self.read_json(run_dir / "claim_ledger_manifest.json")

        self.assertEqual(ledger["record_type"], "claim_ledger_manifest")
        self.assertEqual(ledger["claim_ledger_scope"], "operational_trace_claim_boundary_only")
        self.assertEqual(ledger["claim_ledger_status"], "claim_boundaries_recorded")
        self.assertIn("scientific truth", ledger["not_proven_claims"])
        self.assertFalse(ledger["authority_flags"]["scientific_truth_validated"])
        self.assertFalse(ledger["authority_flags"]["claims_promoted"])

    def test_cli_claim_summary_outputs_claim_boundary(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_cli_claim_summary"))
        stdout = io.StringIO()

        with redirect_stdout(stdout):
            exit_code = cli_main(["claim-summary", "--run-dir", str(run_dir)])

        self.assertEqual(exit_code, 0)
        summary = json.loads(stdout.getvalue())
        self.assertEqual(summary["record_type"], "claim_ledger_summary")
        self.assertEqual(summary["claim_summary_status"], "claim_boundaries_recorded")
        self.assertFalse(summary["authority_flags"]["claims_promoted"])
        self.assertIn("claim-boundary", summary["authority_note"])

    def test_cli_claim_summary_write_creates_summary_file(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_cli_claim_write"))

        exit_code = cli_main(["claim-summary", "--run-dir", str(run_dir), "--write"])

        self.assertEqual(exit_code, 0)
        self.assertTrue((run_dir / "claim_ledger_summary.json").exists())

    def test_cli_claim_summary_write_manifest_refuses_silent_overwrite(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_cli_claim_overwrite"))
        stderr = io.StringIO()

        with redirect_stderr(stderr):
            exit_code = cli_main(["claim-summary", "--run-dir", str(run_dir), "--write-manifest"])

        self.assertEqual(exit_code, 1)
        self.assertIn("refuses to overwrite claim_ledger_manifest.json", stderr.getvalue())

    def test_validation_catches_missing_claim_ledger_manifest(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_missing_claim_ledger"))
        (run_dir / "claim_ledger_manifest.json").unlink()

        result = validate_run(run_dir)

        self.assertEqual(result["validation_status"], "failed_operational_checks")
        self.assertIn("claim_ledger_manifest.json", result["missing"])
        self.assertTrue(any("Missing claim ledger manifest" in item for item in result["claim_errors"]))

    def test_validation_catches_claim_ledger_authority_escalation(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_claim_authority"))
        path = run_dir / "claim_ledger_manifest.json"
        ledger = self.read_json(path)
        ledger["authority_flags"]["scientific_truth_validated"] = True
        self.write_json(path, ledger)

        result = validate_run(run_dir)

        self.assertEqual(result["validation_status"], "failed_operational_checks")
        self.assertTrue(any("scientific_truth_validated" in item for item in result["unsafe"]))

    def test_validation_catches_claim_ledger_promoted_claim(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_claim_promoted"))
        path = run_dir / "claim_ledger_manifest.json"
        ledger = self.read_json(path)
        ledger["prohibited_claims"][0]["claimed"] = True
        self.write_json(path, ledger)

        result = validate_run(run_dir)

        self.assertEqual(result["validation_status"], "failed_operational_checks")
        self.assertTrue(any("prohibited claims" in item for item in result["unsafe"]))

    def test_validation_catches_claim_ledger_hash_mismatch(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_claim_hash"))
        request_path = run_dir / "evidence_packet_manifest.json"
        evidence = self.read_json(request_path)
        evidence["known_gaps"].append("changed_after_claim_ledger")
        self.write_json(request_path, evidence)

        result = validate_run(run_dir)

        self.assertEqual(result["validation_status"], "failed_operational_checks")
        self.assertTrue(any("hash mismatch" in item for item in result["claim_errors"]))

    def test_export_bundle_includes_claim_summary_when_written(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_export_claim_summary"))
        write_claim_ledger_summary(run_dir)
        bundle_path = run_dir.parent / "trace_lab_export.zip"

        write_export_bundle(run_dir, bundle_path)

        with zipfile.ZipFile(bundle_path) as bundle:
            self.assertIn("claim_ledger_summary.json", bundle.namelist())

    def test_neuml_handoff_includes_claim_ledger_record_after_rebuild(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_handoff_claim"))
        write_neuml_handoff_manifest(run_dir)
        handoff = self.read_json(run_dir / "neuml_handoff_manifest.json")

        self.assertIn("claim_ledger_manifest.json", handoff["records_included"])
        self.assertIn("claim_ledger_manifest.json", handoff["text_index_candidates"])
        self.assertIn("claim_ledger_manifest.json", handoff["report_candidates"])

    def test_markdown_report_includes_claim_ledger_section(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_report_claim"))
        report = build_markdown_report(run_dir)

        self.assertIn("## Claim ledger", report)
        self.assertIn("Claim status", report)
        self.assertIn("Not-proven claims", report)



    def test_operator_review_packet_manifest_records_human_review_queue_only(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_review_packet_manifest"))
        packet = self.read_json(run_dir / "operator_review_packet_manifest.json")

        self.assertEqual(packet["record_type"], "operator_review_packet_manifest")
        self.assertEqual(packet["packet_scope"], "human_operator_review_packet_only")
        self.assertEqual(packet["packet_status"], "ready_for_human_review_queue")
        self.assertTrue(packet["human_review_required"])
        self.assertFalse(packet["human_review_completed"])
        self.assertFalse(packet["agent_reviewed"])
        self.assertFalse(packet["automatic_promotion_allowed"])
        self.assertFalse(packet["authority_flags"]["scientific_truth_validated"])
        self.assertFalse(packet["authority_flags"]["state_promoted"])
        self.assertIn("review_record.json", {item["path"] for item in packet["packet_items"]})

    def test_cli_review_packet_outputs_human_queue_boundary(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_cli_review_packet"))
        stdout = io.StringIO()

        with redirect_stdout(stdout):
            exit_code = cli_main(["review-packet", "--run-dir", str(run_dir)])

        self.assertEqual(exit_code, 0)
        summary = json.loads(stdout.getvalue())
        self.assertEqual(summary["record_type"], "operator_review_packet_summary")
        self.assertEqual(summary["packet_summary_status"], "ready_for_human_review_queue")
        self.assertTrue(summary["human_review_required"])
        self.assertFalse(summary["human_review_completed"])
        self.assertFalse(summary["agent_reviewed"])
        self.assertIn("does not complete review", summary["authority_note"])

    def test_cli_review_packet_write_creates_summary_file(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_cli_review_packet_write"))

        exit_code = cli_main(["review-packet", "--run-dir", str(run_dir), "--write"])

        self.assertEqual(exit_code, 0)
        summary = self.read_json(run_dir / "operator_review_packet_summary.json")
        self.assertEqual(summary["packet_summary_status"], "ready_for_human_review_queue")

    def test_cli_review_packet_write_manifest_refuses_silent_overwrite(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_cli_review_packet_overwrite"))
        stderr = io.StringIO()

        with redirect_stderr(stderr):
            exit_code = cli_main(["review-packet", "--run-dir", str(run_dir), "--write-manifest"])

        self.assertEqual(exit_code, 1)
        self.assertIn("refuses to overwrite operator_review_packet_manifest.json", stderr.getvalue())

    def test_validation_catches_missing_operator_review_packet_manifest(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_missing_review_packet"))
        (run_dir / "operator_review_packet_manifest.json").unlink()

        result = validate_run(run_dir)

        self.assertEqual(result["validation_status"], "failed_operational_checks")
        self.assertIn("operator_review_packet_manifest.json", result["missing"])
        self.assertTrue(any("Missing operator review packet manifest" in item for item in result["review_packet_errors"]))

    def test_validation_catches_operator_review_packet_authority_escalation(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_review_packet_authority"))
        path = run_dir / "operator_review_packet_manifest.json"
        packet = self.read_json(path)
        packet["authority_flags"]["scientific_truth_validated"] = True
        self.write_json(path, packet)

        result = validate_run(run_dir)

        self.assertEqual(result["validation_status"], "failed_operational_checks")
        self.assertTrue(any("scientific_truth_validated" in item for item in result["unsafe"]))

    def test_validation_catches_operator_review_packet_completed_review_claim(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_review_packet_completed"))
        path = run_dir / "operator_review_packet_manifest.json"
        packet = self.read_json(path)
        packet["human_review_completed"] = True
        self.write_json(path, packet)

        result = validate_run(run_dir)

        self.assertEqual(result["validation_status"], "failed_operational_checks")
        self.assertTrue(any("human_review_completed" in item for item in result["unsafe"]))

    def test_validation_catches_operator_review_packet_hash_mismatch(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_review_packet_hash"))
        path = run_dir / "review_record.json"
        review = self.read_json(path)
        review["review_status"] = "changed_after_packet"
        self.write_json(path, review)

        result = validate_run(run_dir)

        self.assertEqual(result["validation_status"], "failed_operational_checks")
        self.assertTrue(any("hash mismatch" in item for item in result["review_packet_errors"]))

    def test_export_bundle_includes_operator_review_packet_summary_when_written(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_export_review_packet_summary"))
        write_operator_review_packet_summary(run_dir)
        bundle_path = run_dir.parent / "trace_lab_export.zip"

        write_export_bundle(run_dir, bundle_path)

        with zipfile.ZipFile(bundle_path) as bundle:
            self.assertIn("operator_review_packet_summary.json", bundle.namelist())

    def test_neuml_handoff_includes_operator_review_packet_record_after_rebuild(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_handoff_review_packet"))
        write_neuml_handoff_manifest(run_dir)
        handoff = self.read_json(run_dir / "neuml_handoff_manifest.json")

        self.assertIn("operator_review_packet_manifest.json", handoff["records_included"])
        self.assertIn("operator_review_packet_manifest.json", handoff["text_index_candidates"])
        self.assertIn("operator_review_packet_manifest.json", handoff["report_candidates"])

    def test_markdown_report_includes_operator_review_packet_section(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_report_review_packet"))
        report = build_markdown_report(run_dir)

        self.assertIn("## Operator review packet", report)
        self.assertIn("Packet status", report)
        self.assertIn("Human review completed", report)


    def test_replay_plan_manifest_records_checklist_only(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_replay_plan_boundary"))
        manifest = self.read_json(run_dir / "replay_plan_manifest.json")

        self.assertEqual(manifest["record_type"], "replay_plan_manifest")
        self.assertEqual(manifest["replay_plan_scope"], "local_operator_replay_checklist_only")
        self.assertEqual(manifest["replay_execution_status"], "not_executed")
        self.assertFalse(manifest["replay_performed"])
        self.assertFalse(manifest["automatic_retry_performed"])
        self.assertFalse(manifest["hardware_access_performed"])
        self.assertFalse(manifest["scientific_truth_validated"])
        self.assertTrue(manifest["replay_steps"])

    def test_cli_replay_plan_outputs_checklist_boundary(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_cli_replay_plan"))
        stdout = io.StringIO()

        with redirect_stdout(stdout):
            exit_code = cli_main(["replay-plan", "--run-dir", str(run_dir)])

        self.assertEqual(exit_code, 0)
        data = json.loads(stdout.getvalue())
        self.assertEqual(data["replay_plan_summary_status"], "ready_for_local_operator_replay")
        self.assertEqual(data["replay_execution_status"], "not_executed")
        self.assertFalse(data["replay_performed"])

    def test_cli_replay_plan_write_creates_summary_file(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_cli_replay_write"))
        exit_code = cli_main(["replay-plan", "--run-dir", str(run_dir), "--write"])

        self.assertEqual(exit_code, 0)
        summary = self.read_json(run_dir / "replay_plan_summary.json")
        self.assertEqual(summary["replay_plan_summary_status"], "ready_for_local_operator_replay")

    def test_cli_replay_plan_write_manifest_refuses_silent_overwrite(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_cli_replay_overwrite"))
        stderr = io.StringIO()

        with redirect_stderr(stderr):
            exit_code = cli_main(["replay-plan", "--run-dir", str(run_dir), "--write-manifest"])

        self.assertEqual(exit_code, 1)
        self.assertIn("refuses to overwrite replay_plan_manifest.json", stderr.getvalue())

    def test_validation_catches_missing_replay_plan_manifest(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_missing_replay_plan"))
        (run_dir / "replay_plan_manifest.json").unlink()

        result = validate_run(run_dir)

        self.assertEqual(result["validation_status"], "failed_operational_checks")
        self.assertIn("replay_plan_manifest.json", result["missing"])
        self.assertTrue(any("Missing replay plan manifest" in item for item in result["replay_errors"]))

    def test_validation_catches_replay_plan_authority_escalation(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_replay_authority"))
        path = run_dir / "replay_plan_manifest.json"
        plan = self.read_json(path)
        plan["replay_performed"] = True
        self.write_json(path, plan)

        result = validate_run(run_dir)

        self.assertEqual(result["validation_status"], "failed_operational_checks")
        self.assertTrue(any("replay_performed" in item for item in result["unsafe"]))

    def test_validation_catches_replay_plan_hash_mismatch(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_replay_hash"))
        path = run_dir / "run_plan.json"
        plan = self.read_json(path)
        plan["status"] = "changed_after_replay_plan"
        self.write_json(path, plan)

        result = validate_run(run_dir)

        self.assertEqual(result["validation_status"], "failed_operational_checks")
        self.assertTrue(any("hash mismatch" in item for item in result["replay_errors"]))

    def test_export_bundle_includes_replay_plan_summary_when_written(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_export_replay_summary"))
        write_replay_plan_summary(run_dir)
        bundle_path = run_dir.parent / "trace_lab_export.zip"

        write_export_bundle(run_dir, bundle_path)

        with zipfile.ZipFile(bundle_path) as bundle:
            self.assertIn("replay_plan_summary.json", bundle.namelist())

    def test_neuml_handoff_includes_replay_plan_record_after_rebuild(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_handoff_replay_plan"))
        write_neuml_handoff_manifest(run_dir)
        handoff = self.read_json(run_dir / "neuml_handoff_manifest.json")

        self.assertIn("replay_plan_manifest.json", handoff["records_included"])
        self.assertIn("replay_plan_manifest.json", handoff["text_index_candidates"])
        self.assertIn("replay_plan_manifest.json", handoff["report_candidates"])

    def test_markdown_report_includes_replay_plan_section(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_report_replay_plan"))
        report = build_markdown_report(run_dir)

        self.assertIn("## Replay plan", report)
        self.assertIn("Replay execution status", report)
        self.assertIn("Replay performed", report)


    def test_audit_index_manifest_records_local_navigation_only(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_audit_index_manifest"))
        manifest = build_audit_index_manifest(run_dir)

        self.assertEqual(manifest["record_type"], "audit_index_manifest")
        self.assertEqual(manifest["audit_index_scope"], "operational_simulation_only")
        self.assertEqual(manifest["audit_index_status"], "local_artifact_index_recorded")
        self.assertFalse(manifest["authority_flags"]["scientific_truth_validated"])
        self.assertFalse(manifest["authority_flags"]["physical_execution_completed"])
        self.assertFalse(manifest["authority_flags"]["replay_executed"])
        self.assertIn("evidence != truth", manifest["boundary_notes"])
        self.assertTrue(any(item["path"] == "replay_plan_manifest.json" for item in manifest["items"]))

    def test_cli_audit_index_outputs_navigation_boundary(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_cli_audit_index"))
        stdout = io.StringIO()

        with redirect_stdout(stdout):
            code = cli_main(["audit-index", "--run-dir", str(run_dir)])

        self.assertEqual(code, 0)
        summary = json.loads(stdout.getvalue())
        self.assertEqual(summary["record_type"], "audit_index_summary")
        self.assertEqual(summary["audit_index_summary_status"], "local_artifact_index_ready")
        self.assertEqual(summary["audit_index_scope"], "operator_navigation_only")
        self.assertFalse(summary["authority_flags"]["scientific_truth_validated"])

    def test_cli_audit_index_write_creates_summary_file(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_cli_audit_write"))

        code = cli_main(["audit-index", "--run-dir", str(run_dir), "--write"])

        self.assertEqual(code, 0)
        self.assertTrue((run_dir / "audit_index_summary.json").exists())
        summary = self.read_json(run_dir / "audit_index_summary.json")
        self.assertEqual(summary["audit_index_summary_status"], "local_artifact_index_ready")

    def test_cli_audit_index_write_manifest_refuses_silent_overwrite(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_cli_audit_overwrite"))

        stderr = io.StringIO()
        with redirect_stderr(stderr):
            code = cli_main(["audit-index", "--run-dir", str(run_dir), "--write-manifest"])

        self.assertEqual(code, 1)
        self.assertIn("refuses to overwrite audit_index_manifest.json", stderr.getvalue())

    def test_validation_catches_missing_audit_index_manifest(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_missing_audit_index"))
        (run_dir / "audit_index_manifest.json").unlink()

        result = validate_run(run_dir)

        self.assertEqual(result["validation_status"], "failed_operational_checks")
        self.assertTrue(any("audit_index_manifest.json is missing" in item for item in result["audit_errors"]))

    def test_validation_catches_audit_index_authority_escalation(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_audit_authority"))
        manifest = self.read_json(run_dir / "audit_index_manifest.json")
        manifest["authority_flags"]["scientific_truth_validated"] = True
        self.write_json(run_dir / "audit_index_manifest.json", manifest)
        write_run_manifest(run_dir, force=True)

        result = validate_run(run_dir)

        self.assertEqual(result["validation_status"], "failed_operational_checks")
        self.assertTrue(any("scientific_truth_validated" in item for item in result["unsafe"]))

    def test_validation_catches_audit_index_hash_mismatch(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_audit_hash_mismatch"))
        manifest = self.read_json(run_dir / "audit_index_manifest.json")
        for item in manifest["items"]:
            if item["path"] == "experiment_request.json":
                item["hash"] = "not-the-real-hash"
                break
        self.write_json(run_dir / "audit_index_manifest.json", manifest)
        write_run_manifest(run_dir, force=True)

        result = validate_run(run_dir)

        self.assertEqual(result["validation_status"], "failed_operational_checks")
        self.assertTrue(any("hash mismatch" in item for item in result["audit_errors"]))

    def test_export_bundle_includes_audit_index_summary_when_written(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_export_audit_summary"))
        write_audit_index_summary(run_dir, force=True)
        bundle_path = run_dir.parent / "trace_lab_export.zip"

        write_export_bundle(run_dir, bundle_path)

        with zipfile.ZipFile(bundle_path) as bundle:
            self.assertIn("audit_index_summary.json", bundle.namelist())

    def test_neuml_handoff_includes_audit_index_record_after_rebuild(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_handoff_audit_index"))
        write_neuml_handoff_manifest(run_dir)
        handoff = self.read_json(run_dir / "neuml_handoff_manifest.json")

        self.assertIn("audit_index_manifest.json", handoff["records_included"])
        self.assertIn("audit_index_manifest.json", handoff["text_index_candidates"])
        self.assertIn("audit_index_manifest.json", handoff["report_candidates"])

    def test_markdown_report_includes_audit_index_section(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_report_audit_index"))
        report = build_markdown_report(run_dir)

        self.assertIn("## Audit index", report)
        self.assertIn("Audit index status", report)
        self.assertIn("Indexed items", report)




    def test_validation_recipe_manifest_records_command_checklist_only(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_validation_recipe_manifest"))
        manifest = build_validation_recipe_manifest(run_dir)

        self.assertEqual(manifest["record_type"], "validation_recipe_manifest")
        self.assertEqual(manifest["validation_recipe_scope"], "local_validation_checklist_only")
        self.assertEqual(manifest["validation_recipe_status"], "ready_for_local_operator_validation")
        self.assertFalse(manifest["recipe_performed"])
        self.assertFalse(manifest["commands_executed"])
        self.assertFalse(manifest["authority_flags"]["scientific_truth_validated"])
        self.assertFalse(manifest["authority_flags"]["hardware_access_performed"])
        self.assertIn("validate_run", manifest["required_command_ids"])
        self.assertTrue(any(command["command_id"] == "verify_bundle" for command in manifest["validation_commands"]))

    def test_cli_validation_recipe_outputs_checklist_boundary(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_cli_recipe_output"))
        stdout = io.StringIO()

        with redirect_stdout(stdout):
            exit_code = cli_main(["validation-recipe", "--run-dir", str(run_dir)])

        self.assertEqual(exit_code, 0)
        output = json.loads(stdout.getvalue())
        self.assertEqual(output["record_type"], "validation_recipe_summary")
        self.assertEqual(output["validation_recipe_summary_status"], "ready_for_local_operator_validation")
        self.assertEqual(output["validation_recipe_scope"], "local_validation_checklist_only")
        self.assertEqual(output["unsafe"], [])

    def test_cli_validation_recipe_write_creates_summary_file(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_cli_recipe_write"))

        exit_code = cli_main(["validation-recipe", "--run-dir", str(run_dir), "--write"])

        self.assertEqual(exit_code, 0)
        summary = self.read_json(run_dir / "validation_recipe_summary.json")
        self.assertEqual(summary["record_type"], "validation_recipe_summary")
        self.assertEqual(summary["validation_recipe_summary_status"], "ready_for_local_operator_validation")

    def test_cli_validation_recipe_write_manifest_refuses_silent_overwrite(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_cli_recipe_overwrite"))
        stderr = io.StringIO()

        with redirect_stderr(stderr):
            exit_code = cli_main([
                "validation-recipe",
                "--run-dir",
                str(run_dir),
                "--write-manifest",
            ])

        self.assertEqual(exit_code, 1)
        self.assertIn("refuses to overwrite validation_recipe_manifest.json", stderr.getvalue())

    def test_validation_catches_missing_validation_recipe_manifest(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_missing_validation_recipe"))
        (run_dir / "validation_recipe_manifest.json").unlink()
        write_run_manifest(run_dir, force=True)

        result = validate_run(run_dir)

        self.assertEqual(result["validation_status"], "failed_operational_checks")
        self.assertTrue(any("validation_recipe_manifest.json" in item for item in result["missing"]))
        self.assertTrue(any("validation_recipe_manifest.json is missing" in item for item in result["recipe_errors"]))

    def test_validation_catches_validation_recipe_authority_escalation(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_recipe_authority"))
        manifest = self.read_json(run_dir / "validation_recipe_manifest.json")
        manifest["scientific_truth_validated"] = True
        manifest["authority_flags"]["hardware_access_performed"] = True
        self.write_json(run_dir / "validation_recipe_manifest.json", manifest)
        write_run_manifest(run_dir, force=True)

        result = validate_run(run_dir)

        self.assertEqual(result["validation_status"], "failed_operational_checks")
        self.assertTrue(any("scientific_truth_validated" in item for item in result["unsafe"]))
        self.assertTrue(any("hardware_access_performed" in item for item in result["unsafe"]))

    def test_validation_catches_validation_recipe_executed_command_claim(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_recipe_command_executed"))
        manifest = self.read_json(run_dir / "validation_recipe_manifest.json")
        manifest["validation_commands"][0]["command_executed"] = True
        self.write_json(run_dir / "validation_recipe_manifest.json", manifest)
        write_run_manifest(run_dir, force=True)

        result = validate_run(run_dir)

        self.assertEqual(result["validation_status"], "failed_operational_checks")
        self.assertTrue(any("command_executed" in item for item in result["unsafe"]))

    def test_validation_catches_validation_recipe_hash_mismatch(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_recipe_hash_mismatch"))
        manifest = self.read_json(run_dir / "validation_recipe_manifest.json")
        for item in manifest["recipe_inputs"]:
            if item["path"] == "experiment_request.json":
                item["hash"] = "not-the-real-hash"
                break
        self.write_json(run_dir / "validation_recipe_manifest.json", manifest)
        write_run_manifest(run_dir, force=True)

        result = validate_run(run_dir)

        self.assertEqual(result["validation_status"], "failed_operational_checks")
        self.assertTrue(any("hash mismatch" in item for item in result["recipe_errors"]))

    def test_export_bundle_includes_validation_recipe_summary_when_written(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_export_recipe_summary"))
        write_validation_recipe_summary(run_dir, force=True)
        bundle_path = run_dir.parent / "trace_lab_export.zip"

        write_export_bundle(run_dir, bundle_path)

        with zipfile.ZipFile(bundle_path) as bundle:
            self.assertIn("validation_recipe_summary.json", bundle.namelist())

    def test_neuml_handoff_includes_validation_recipe_record_after_rebuild(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_handoff_validation_recipe"))
        write_validation_recipe_manifest(run_dir, force=True)
        write_neuml_handoff_manifest(run_dir)
        handoff = self.read_json(run_dir / "neuml_handoff_manifest.json")

        self.assertIn("validation_recipe_manifest.json", handoff["records_included"])
        self.assertIn("validation_recipe_manifest.json", handoff["text_index_candidates"])
        self.assertIn("validation_recipe_manifest.json", handoff["report_candidates"])

    def test_markdown_report_includes_validation_recipe_section(self):
        run_dir = run_simulated_experiment(self.tmp_path("demo_report_validation_recipe"))
        report = build_markdown_report(run_dir)

        self.assertIn("## Validation recipe", report)
        self.assertIn("Recipe status", report)
        self.assertIn("Command count", report)




    def tmp_path(self, name):
        from tempfile import TemporaryDirectory
        from pathlib import Path

        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        return Path(temp.name) / name


    @staticmethod
    def rewrite_zip_member(source_path, target_path, member_name, replacement_bytes):
        with zipfile.ZipFile(source_path) as source:
            with zipfile.ZipFile(target_path, "w", compression=zipfile.ZIP_DEFLATED) as target:
                for name in source.namelist():
                    if name == member_name:
                        target.writestr(name, replacement_bytes)
                    else:
                        target.writestr(name, source.read(name))

    @staticmethod
    def read_json(path):
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def write_json(path, data):
        path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
