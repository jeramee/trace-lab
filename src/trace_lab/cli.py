from __future__ import annotations
import argparse, json, sys
from .workflow import run_simulated_experiment
from .validate import validate_run
from .validation_result import write_validation_result_record
from .neuml_handoff import write_neuml_handoff_manifest
from .run_manifest import write_run_manifest
from .run_state import build_run_state_summary, write_run_state_summary
from .review import REVIEW_STATUS_PENDING, build_review_summary, write_review_summary
from .adapter_policy import build_adapter_boundary_summary, write_adapter_boundary_summary
from .runtime_environment import build_runtime_environment_summary, write_runtime_environment_summary
from .export_bundle import build_export_manifest, write_export_bundle, validate_export_bundle, write_export_bundle_validation_result
from .report import build_markdown_report, validate_markdown_report, write_markdown_report, write_markdown_report_validation_result
from .execution_policy import build_execution_policy_summary, write_execution_policy_summary
from .telemetry_profile import build_telemetry_profile_summary, write_telemetry_profile_summary, write_telemetry_profile_manifest
from .ingestion_preview import build_ingestion_preview_summary, write_ingestion_preview_summary, write_ingestion_preview_manifest
from .provenance import build_provenance_summary, write_provenance_summary, write_provenance_manifest
from .closeout import build_run_closeout_summary, write_run_closeout_summary, write_run_closeout_manifest
from .claim_ledger import build_claim_ledger_summary, write_claim_ledger_summary, write_claim_ledger_manifest
from .operator_review_packet import build_operator_review_packet_summary, write_operator_review_packet_summary, write_operator_review_packet_manifest
from .replay_plan import build_replay_plan_summary, write_replay_plan_summary, write_replay_plan_manifest
from .audit_index import build_audit_index_summary, write_audit_index_summary, write_audit_index_manifest
from .validation_recipe import build_validation_recipe_summary, write_validation_recipe_summary, write_validation_recipe_manifest

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="trace-lab")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("run-demo")
    p.add_argument("--out", default=".trace_lab_demo")

    p = sub.add_parser("validate")
    p.add_argument("--run-dir", required=True)
    p.add_argument("--write-result", action="store_true")
    p.add_argument("--force-result", action="store_true")

    p = sub.add_parser("build-neuml-handoff")
    p.add_argument("--run-dir", required=True)

    p = sub.add_parser("state-summary")
    p.add_argument("--run-dir", required=True)
    p.add_argument("--write", action="store_true")

    p = sub.add_parser("review-summary")
    p.add_argument("--run-dir", required=True)
    p.add_argument("--write", action="store_true")

    p = sub.add_parser("adapter-summary")
    p.add_argument("--run-dir", required=True)
    p.add_argument("--write", action="store_true")

    p = sub.add_parser("environment-summary")
    p.add_argument("--run-dir", required=True)
    p.add_argument("--write", action="store_true")

    p = sub.add_parser("policy-summary")
    p.add_argument("--run-dir", required=True)
    p.add_argument("--write", action="store_true")

    p = sub.add_parser("telemetry-profile")
    p.add_argument("--run-dir", required=True)
    p.add_argument("--write", action="store_true")
    p.add_argument("--write-manifest", action="store_true")
    p.add_argument("--force", action="store_true")

    p = sub.add_parser("ingestion-preview")
    p.add_argument("--run-dir", required=True)
    p.add_argument("--write", action="store_true")
    p.add_argument("--write-manifest", action="store_true")
    p.add_argument("--force", action="store_true")

    p = sub.add_parser("provenance-summary")
    p.add_argument("--run-dir", required=True)
    p.add_argument("--write", action="store_true")
    p.add_argument("--write-manifest", action="store_true")
    p.add_argument("--force", action="store_true")

    p = sub.add_parser("closeout-summary")
    p.add_argument("--run-dir", required=True)
    p.add_argument("--write", action="store_true")
    p.add_argument("--write-manifest", action="store_true")
    p.add_argument("--force", action="store_true")

    p = sub.add_parser("claim-summary")
    p.add_argument("--run-dir", required=True)
    p.add_argument("--write", action="store_true")
    p.add_argument("--write-manifest", action="store_true")
    p.add_argument("--force", action="store_true")

    p = sub.add_parser("review-packet")
    p.add_argument("--run-dir", required=True)
    p.add_argument("--write", action="store_true")
    p.add_argument("--write-manifest", action="store_true")
    p.add_argument("--force", action="store_true")

    p = sub.add_parser("replay-plan")
    p.add_argument("--run-dir", required=True)
    p.add_argument("--write", action="store_true")
    p.add_argument("--write-manifest", action="store_true")
    p.add_argument("--force", action="store_true")

    p = sub.add_parser("audit-index")
    p.add_argument("--run-dir", required=True)
    p.add_argument("--write", action="store_true")
    p.add_argument("--write-manifest", action="store_true")
    p.add_argument("--force", action="store_true")

    p = sub.add_parser("validation-recipe")
    p.add_argument("--run-dir", required=True)
    p.add_argument("--write", action="store_true")
    p.add_argument("--write-manifest", action="store_true")
    p.add_argument("--force", action="store_true")

    p = sub.add_parser("export-bundle")
    p.add_argument("--run-dir", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--force", action="store_true")
    p.add_argument("--profile", default="simulated_lab_bundle")
    p.add_argument("--dry-run", action="store_true")

    p = sub.add_parser("verify-bundle")
    p.add_argument("--bundle", required=True)
    p.add_argument("--write-result", action="store_true")
    p.add_argument("--result-out")
    p.add_argument("--force-result", action="store_true")

    p = sub.add_parser("report")
    p.add_argument("--run-dir", required=True)
    p.add_argument("--write", action="store_true")
    p.add_argument("--out")
    p.add_argument("--force", action="store_true")

    p = sub.add_parser("verify-report")
    p.add_argument("--run-dir", required=True)
    p.add_argument("--report-path")
    p.add_argument("--write-result", action="store_true")
    p.add_argument("--result-out")
    p.add_argument("--force-result", action="store_true")

    args = parser.parse_args(argv)
    if args.command == "run-demo":
        try:
            print(run_simulated_experiment(args.out))
            return 0
        except FileExistsError as exc:
            print(str(exc), file=sys.stderr)
            return 1
    if args.command == "validate":
        result = validate_run(args.run_dir)
        if args.write_result:
            try:
                result_path = write_validation_result_record(
                    args.run_dir,
                    result,
                    force=args.force_result,
                )
                result["validation_result_path"] = str(result_path)
            except FileExistsError as exc:
                print(str(exc), file=sys.stderr)
                return 1
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["validation_status"] == "passed_operational_checks" else 1
    if args.command == "build-neuml-handoff":
        try:
            handoff_path = write_neuml_handoff_manifest(args.run_dir)
            write_run_closeout_manifest(args.run_dir, force=True)
            write_claim_ledger_manifest(args.run_dir, force=True)
            write_operator_review_packet_manifest(args.run_dir, force=True)
            write_replay_plan_manifest(args.run_dir, force=True)
            write_audit_index_manifest(args.run_dir, force=True)
            write_validation_recipe_manifest(args.run_dir, force=True)
            write_run_manifest(args.run_dir, force=True)
            print(handoff_path)
            return 0
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 1
    if args.command == "state-summary":
        summary = build_run_state_summary(args.run_dir)
        if args.write:
            print(write_run_state_summary(args.run_dir))
        else:
            print(json.dumps(summary, indent=2, sort_keys=True))
        return 0 if summary["state_summary_status"] == "complete_simulation_only" else 1
    if args.command == "review-summary":
        summary = build_review_summary(args.run_dir)
        if args.write:
            print(write_review_summary(args.run_dir))
        else:
            print(json.dumps(summary, indent=2, sort_keys=True))
        return 0 if summary["review_summary_status"] == REVIEW_STATUS_PENDING else 1
    if args.command == "adapter-summary":
        summary = build_adapter_boundary_summary(args.run_dir)
        if args.write:
            print(write_adapter_boundary_summary(args.run_dir))
        else:
            print(json.dumps(summary, indent=2, sort_keys=True))
        return 0 if summary["adapter_boundary_status"] == "simulation_only_boundary_intact" else 1
    if args.command == "environment-summary":
        summary = build_runtime_environment_summary(args.run_dir)
        if args.write:
            print(write_runtime_environment_summary(args.run_dir))
        else:
            print(json.dumps(summary, indent=2, sort_keys=True))
        return 0 if summary["environment_summary_status"] == "runtime_context_recorded" else 1
    if args.command == "policy-summary":
        summary = build_execution_policy_summary(args.run_dir)
        if args.write:
            print(write_execution_policy_summary(args.run_dir))
        else:
            print(json.dumps(summary, indent=2, sort_keys=True))
        return 0 if summary["policy_summary_status"] == "simulation_policy_intact" else 1
    if args.command == "telemetry-profile":
        try:
            if args.write_manifest:
                write_telemetry_profile_manifest(args.run_dir, force=args.force)
            summary = build_telemetry_profile_summary(args.run_dir)
            if args.write:
                print(write_telemetry_profile_summary(args.run_dir, force=args.force))
            else:
                print(json.dumps(summary, indent=2, sort_keys=True))
            return 0 if summary["telemetry_profile_validation_status"] == "passed_telemetry_profile_checks" else 1
        except FileExistsError as exc:
            print(str(exc), file=sys.stderr)
            return 1
    if args.command == "ingestion-preview":
        try:
            if args.write_manifest:
                write_ingestion_preview_manifest(args.run_dir, force=args.force)
            summary = build_ingestion_preview_summary(args.run_dir)
            if args.write:
                print(write_ingestion_preview_summary(args.run_dir, force=args.force))
            else:
                print(json.dumps(summary, indent=2, sort_keys=True))
            return 0 if summary["ingestion_preview_status"] == "ready_for_future_local_indexing" else 1
        except FileExistsError as exc:
            print(str(exc), file=sys.stderr)
            return 1
    if args.command == "provenance-summary":
        try:
            if args.write_manifest:
                write_provenance_manifest(args.run_dir, force=args.force)
            summary = build_provenance_summary(args.run_dir)
            if args.write:
                print(write_provenance_summary(args.run_dir, force=args.force))
            else:
                print(json.dumps(summary, indent=2, sort_keys=True))
            return 0 if summary["provenance_summary_status"] == "provenance_recorded" else 1
        except FileExistsError as exc:
            print(str(exc), file=sys.stderr)
            return 1
    if args.command == "closeout-summary":
        try:
            if args.write_manifest:
                write_run_closeout_manifest(args.run_dir, force=args.force)
            summary = build_run_closeout_summary(args.run_dir)
            if args.write:
                print(write_run_closeout_summary(args.run_dir, force=args.force))
            else:
                print(json.dumps(summary, indent=2, sort_keys=True))
            return 0 if summary["closeout_summary_status"] == "ready_for_operator_review_and_local_export" else 1
        except FileExistsError as exc:
            print(str(exc), file=sys.stderr)
            return 1
    if args.command == "claim-summary":
        try:
            if args.write_manifest:
                write_claim_ledger_manifest(args.run_dir, force=args.force)
            summary = build_claim_ledger_summary(args.run_dir)
            if args.write:
                print(write_claim_ledger_summary(args.run_dir, force=args.force))
            else:
                print(json.dumps(summary, indent=2, sort_keys=True))
            return 0 if summary["claim_summary_status"] == "claim_boundaries_recorded" else 1
        except FileExistsError as exc:
            print(str(exc), file=sys.stderr)
            return 1
    if args.command == "review-packet":
        try:
            if args.write_manifest:
                write_operator_review_packet_manifest(args.run_dir, force=args.force)
            summary = build_operator_review_packet_summary(args.run_dir)
            if args.write:
                print(write_operator_review_packet_summary(args.run_dir, force=args.force))
            else:
                print(json.dumps(summary, indent=2, sort_keys=True))
            return 0 if summary["packet_summary_status"] == "ready_for_human_review_queue" else 1
        except FileExistsError as exc:
            print(str(exc), file=sys.stderr)
            return 1
    if args.command == "replay-plan":
        try:
            if args.write_manifest:
                write_replay_plan_manifest(args.run_dir, force=args.force)
            summary = build_replay_plan_summary(args.run_dir)
            if args.write:
                print(write_replay_plan_summary(args.run_dir, force=args.force))
            else:
                print(json.dumps(summary, indent=2, sort_keys=True))
            return 0 if summary["replay_plan_summary_status"] == "ready_for_local_operator_replay" else 1
        except FileExistsError as exc:
            print(str(exc), file=sys.stderr)
            return 1
    if args.command == "audit-index":
        try:
            if args.write_manifest:
                write_audit_index_manifest(args.run_dir, force=args.force)
            summary = build_audit_index_summary(args.run_dir)
            if args.write:
                print(write_audit_index_summary(args.run_dir, force=args.force))
            else:
                print(json.dumps(summary, indent=2, sort_keys=True))
            return 0 if summary["audit_index_summary_status"] == "local_artifact_index_ready" else 1
        except FileExistsError as exc:
            print(str(exc), file=sys.stderr)
            return 1
    if args.command == "validation-recipe":
        try:
            if args.write_manifest:
                write_validation_recipe_manifest(args.run_dir, force=args.force)
            summary = build_validation_recipe_summary(args.run_dir)
            if args.write:
                print(write_validation_recipe_summary(args.run_dir, force=args.force))
            else:
                print(json.dumps(summary, indent=2, sort_keys=True))
            return 0 if summary["validation_recipe_summary_status"] == "ready_for_local_operator_validation" else 1
        except FileExistsError as exc:
            print(str(exc), file=sys.stderr)
            return 1
    if args.command == "export-bundle":
        try:
            if args.dry_run:
                manifest = build_export_manifest(args.run_dir, selected_profile_name=args.profile)
                print(json.dumps(manifest, indent=2, sort_keys=True))
                return 0 if manifest["export_status"] == "ready_for_local_zip_export" else 1
            print(write_export_bundle(args.run_dir, args.out, force=args.force, selected_profile_name=args.profile))
            return 0
        except (FileExistsError, ValueError) as exc:
            print(str(exc), file=sys.stderr)
            return 1
    if args.command == "verify-bundle":
        result = validate_export_bundle(args.bundle)
        if args.write_result:
            try:
                result_path = write_export_bundle_validation_result(
                    args.bundle,
                    out_path=args.result_out,
                    force=args.force_result,
                )
                result["validation_result_path"] = str(result_path)
            except FileExistsError as exc:
                print(str(exc), file=sys.stderr)
                return 1
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["bundle_validation_status"] == "passed_export_bundle_checks" else 1
    if args.command == "report":
        try:
            if args.write:
                print(write_markdown_report(args.run_dir, out_path=args.out, force=args.force))
            else:
                print(build_markdown_report(args.run_dir))
            return 0
        except (FileExistsError, ValueError) as exc:
            print(str(exc), file=sys.stderr)
            return 1
    if args.command == "verify-report":
        try:
            result = validate_markdown_report(args.run_dir, report_path=args.report_path)
            if args.write_result:
                result_path = write_markdown_report_validation_result(
                    args.run_dir,
                    report_path=args.report_path,
                    out_path=args.result_out,
                    force=args.force_result,
                )
                result["validation_result_path"] = str(result_path)
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0 if result["report_validation_status"] == "passed_report_boundary_checks" else 1
        except FileExistsError as exc:
            print(str(exc), file=sys.stderr)
            return 1
    return 2

if __name__ == "__main__":
    raise SystemExit(main())
