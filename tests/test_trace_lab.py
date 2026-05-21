from trace_lab.workflow import run_simulated_experiment
from trace_lab.validate import validate_run

def test_trace_lab_simulated_run(tmp_path):
    run_dir = run_simulated_experiment(tmp_path / "demo")
    result = validate_run(run_dir)
    assert result["validation_status"] == "passed_operational_checks"
    assert (run_dir / "lab_run_record.json").exists()
    assert (run_dir / "telemetry" / "simulated_flow_sensor_A.csv").exists()
    assert not (run_dir / "notebook_run_record.json").exists()
