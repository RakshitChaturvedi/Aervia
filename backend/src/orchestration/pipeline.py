from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


@dataclass(frozen=True)
class PipelinePaths:
    backend_dir: Path
    dataset_id: str
    run_root: Path
    minute_csv: Path
    samples_csv: Path

    @property
    def parameter_dir(self) -> Path:
        return self.run_root / "parameter_intelligence"

    @property
    def analytics_dir(self) -> Path:
        return self.run_root / "analytics"

    @property
    def warnings_dir(self) -> Path:
        return self.run_root / "warnings"

    @property
    def advisories_dir(self) -> Path:
        return self.run_root / "advisories"

    @property
    def reports_dir(self) -> Path:
        return self.run_root / "reports"


class PipelineOrchestrator:
    """Runs the existing layer CLIs in dependency order.

    This orchestrator starts from completed preprocessing outputs (minute.csv and
    samples.csv). It intentionally does not guess which ingestion/preprocessing
    scripts should run, because those commands vary by data source.
    """

    def __init__(
        self,
        paths: PipelinePaths,
        *,
        run_advisories: bool = True,
        run_reports: bool = True,
        disable_llm: bool = False,
        report_type: str = "daily",
        start_utc: str | None = None,
        end_utc: str | None = None,
        audience: str = "operator",
        dry_run: bool = False,
    ):
        self.paths = paths
        self.run_advisories = run_advisories
        self.run_reports = run_reports
        self.disable_llm = disable_llm
        self.report_type = report_type
        self.start_utc = start_utc
        self.end_utc = end_utc
        self.audience = audience
        self.dry_run = dry_run
        self.python = sys.executable
        self.commands: list[list[str]] = []

    def _command(self, *args: str) -> list[str]:
        return [self.python, *args]

    def build_commands(self) -> list[list[str]]:
        b = self.paths.backend_dir
        p = self.paths
        features = p.parameter_dir / "features.csv"
        warnings = p.warnings_dir / "warnings.json"
        advisories = p.advisories_dir / "advisories.json"

        commands = [
            self._command(
                "scripts/run_parameter_intelligence.py",
                "--minute", str(p.minute_csv),
                "--samples", str(p.samples_csv),
                "--output", str(p.parameter_dir),
            ),
            self._command(
                "scripts/run_analytics.py",
                "--features", str(features),
                "--output", str(p.analytics_dir),
                "--dataset-id", p.dataset_id,
            ),
            self._command(
                "scripts/run_warning_engine.py",
                "--analytics-dir", str(p.analytics_dir),
                "--features", str(features),
                "--output", str(p.warnings_dir),
                "--dataset-id", p.dataset_id,
            ),
        ]

        if self.run_advisories:
            advisory_cmd = self._command(
                "scripts/run_advisory_engine.py",
                "--warnings", str(warnings),
                "--analytics-dir", str(p.analytics_dir),
                "--features", str(features),
                "--output", str(p.advisories_dir)
            )
            if self.disable_llm:
                advisory_cmd.append("--disable-llm")
            commands.append(advisory_cmd)

        if self.run_reports:
            report_cmd = self._command(
                "scripts/run_report.py",
                "--analytics-dir", str(p.analytics_dir),
                "--warnings", str(warnings),
                "--features", str(features),
                "--output", str(p.reports_dir / self.report_type),
                "--dataset-id", p.dataset_id,
                "--type", self.report_type,
                "--audience", self.audience,
            )
            if self.run_advisories:
                report_cmd.extend(["--advisories", str(advisories)])
            if self.start_utc:
                report_cmd.extend(["--start-utc", self.start_utc])
            if self.end_utc:
                report_cmd.extend(["--end-utc", self.end_utc])
            commands.append(report_cmd)

        self.commands = commands
        return commands

    def run(self) -> None:
        b = self.paths.backend_dir.resolve()
        if not b.is_dir():
            raise FileNotFoundError(f"Backend directory not found: {b}")
        for required in (self.paths.minute_csv, self.paths.samples_csv):
            if not required.is_file():
                raise FileNotFoundError(f"Required preprocessing input not found: {required}")

        commands = self.build_commands()
        env = os.environ.copy()
        env["PYTHONPATH"] = str(b) + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")

        for index, command in enumerate(commands, start=1):
            relative_command = " ".join(command)
            print(f"[{index}/{len(commands)}] {relative_command}")
            if self.dry_run:
                continue
            # Paths in the command are interpreted relative to backend.
            # Resolve user-supplied relative paths against backend for predictable execution.
            normalized = [command[0]]
            for i, arg in enumerate(command[1:]):
                if i > 0 and command[i] in {"--minute", "--samples", "--output", "--features",
                                             "--analytics-dir", "--warnings", "--advisories"}:
                    value = Path(arg)
                    normalized.append(str((b / value).resolve()) if not value.is_absolute() else str(value))
                else:
                    normalized.append(arg)
            subprocess.run(normalized, cwd=b, env=env, check=True)
        print("Pipeline orchestration completed." if not self.dry_run else "Dry run completed; no layer was executed.")