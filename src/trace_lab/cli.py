from __future__ import annotations
import argparse, json, sys
from .workflow import run_simulated_experiment
from .validate import validate_run
from .neuml_handoff import write_neuml_handoff_manifest

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="trace-lab")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("run-demo")
    p.add_argument("--out", default=".trace_lab_demo")

    p = sub.add_parser("validate")
    p.add_argument("--run-dir", required=True)

    p = sub.add_parser("build-neuml-handoff")
    p.add_argument("--run-dir", required=True)

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
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["validation_status"] == "passed_operational_checks" else 1
    if args.command == "build-neuml-handoff":
        print(write_neuml_handoff_manifest(args.run_dir))
        return 0
    return 2

if __name__ == "__main__":
    raise SystemExit(main())
