from pathlib import Path
from src.orchestration.pipeline import PipelinePaths, PipelineOrchestrator


def test_command_order_and_dependencies(tmp_path):
    backend = tmp_path / "backend"
    backend.mkdir()
    minute = backend / "minute.csv"
    samples = backend / "samples.csv"
    minute.write_text("timestamp,pm2_5\n")
    samples.write_text("timestamp,pm2_5\n")
    paths = PipelinePaths(backend, "dataset-x", backend / "run", minute, samples)
    orchestrator = PipelineOrchestrator(paths)
    commands = orchestrator.build_commands()
    scripts = [Path(command[1]).name for command in commands]
    assert scripts == [
        "run_parameter_intelligence.py",
        "run_analytics.py",
        "run_warning_engine.py",
        "run_advisory_engine.py",
        "run_report.py",
    ]
    assert "--features" in commands[1]
    assert "--warnings" in commands[3]


def test_optional_layers_can_be_skipped(tmp_path):
    backend = tmp_path / "backend"
    backend.mkdir()
    minute = backend / "minute.csv"
    samples = backend / "samples.csv"
    minute.write_text("timestamp,pm2_5\n")
    samples.write_text("timestamp,pm2_5\n")
    paths = PipelinePaths(backend, "dataset-x", backend / "run", minute, samples)
    commands = PipelineOrchestrator(
        paths, run_advisories=False, run_reports=False
    ).build_commands()
    assert len(commands) == 3


def test_dry_run_checks_input_files_without_executing(tmp_path, capsys):
    backend = tmp_path / "backend"
    backend.mkdir()
    minute = backend / "minute.csv"
    samples = backend / "samples.csv"
    minute.write_text("timestamp,pm2_5\n")
    samples.write_text("timestamp,pm2_5\n")
    paths = PipelinePaths(backend, "dataset-x", backend / "run", minute, samples)
    PipelineOrchestrator(paths, dry_run=True).run()
    assert "Dry run completed" in capsys.readouterr().out