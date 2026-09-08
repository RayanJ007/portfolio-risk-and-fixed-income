"""Launch the workbook builder with the bundled artifact runtime, or configured equivalents."""

import os
from pathlib import Path
import subprocess

from src.database.connection import ROOT


def export_excel(report_path, output_path="models/risk_reporting_model.xlsx", render=False):
    runtime = Path.home() / ".cache/codex-runtimes/codex-primary-runtime/dependencies/node"
    node = Path(
        os.environ.get(
            "ARTIFACT_NODE",
            str(runtime / "bin/node.exe" if os.name == "nt" else runtime / "bin/node"),
        )
    )
    modules = Path(os.environ.get("ARTIFACT_MODULES", str(runtime / "node_modules")))
    if not node.exists() or not (modules / "@oai/artifact-tool").exists():
        raise RuntimeError(
            "Excel export needs the artifact runtime. Set ARTIFACT_NODE and ARTIFACT_MODULES; the generated workbook is included in models/."
        )
    output = Path(output_path).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, ARTIFACT_MODULES=str(modules))
    command = [
        str(node),
        str(ROOT / "scripts/export_excel.mjs"),
        str(Path(report_path).resolve()),
        str(output),
    ]
    if render:
        command.append("--render")
    subprocess.run(command, env=env, check=True, cwd=ROOT)
    return output
