#!/usr/bin/env python3
"""Check the installed course tutor, Jupyter AI, extensions, and kernel."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path


def main() -> int:
    failures: list[str] = []
    opencode = shutil.which("opencode")
    if not opencode:
        failures.append("OpenCode CLI is not on PATH")
    else:
        result = subprocess.run([opencode, "--version"], capture_output=True, text=True, check=False)
        print(f"OpenCode: {(result.stdout or result.stderr).strip()}")
        if result.returncode:
            failures.append("OpenCode CLI did not report its version")

    config = Path("/opt/course/opencode/opencode.json")
    try:
        data = json.loads(config.read_text(encoding="utf-8"))
        if data.get("default_agent") != "sysml-design-coach":
            failures.append("OpenCode default agent is not sysml-design-coach")
        if not Path("/opt/course/.opencode/agents/sysml-design-coach.md").is_file():
            failures.append("SysML Design Coach agent prompt is missing")
        for skill in ("concept-design", "poc-realization", "feasibility-assessment"):
            skill_path = Path(f"/opt/course/.opencode/skills/{skill}/SKILL.md")
            if not skill_path.is_file():
                failures.append(f"Methodology skill is missing: {skill}")
        print(f"OpenCode course config: {config}")
    except (OSError, json.JSONDecodeError) as error:
        failures.append(f"Cannot read OpenCode course config: {error}")

    result = subprocess.run([sys.executable, "-m", "jupyter", "kernelspec", "list", "--json"], capture_output=True, text=True, check=False)
    try:
        specs = json.loads(result.stdout).get("kernelspecs", {})
    except json.JSONDecodeError:
        specs = {}
    if result.returncode or "sysml" not in specs:
        failures.append("OpenSysML (sysml) Jupyter kernel is not installed")
    else:
        print("OpenSysML kernel: installed")

    result = subprocess.run([sys.executable, "-m", "jupyter", "labextension", "list"], capture_output=True, text=True, check=False)
    output = result.stdout + result.stderr
    if result.returncode or "@keio/classroom-status" not in output or "enabled" not in output:
        failures.append("Keio classroom status extension is missing or disabled")
    else:
        print("Course status extension: enabled")

    if failures:
        for failure in failures:
            print(f"ERROR: {failure}", file=sys.stderr)
        return 1
    print("Course tutor runtime is ready. Provider sign-in is configured separately with `make opencode-auth`.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
