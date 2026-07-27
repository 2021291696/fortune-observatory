"""Release gate for the currently verified v1 slice."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def check(command: list[str], cwd: Path) -> None:
    subprocess.run(command, cwd=cwd, check=True)


def verify_json() -> None:
    for path in (ROOT / "data").rglob("*.json"):
        if "vendor" in path.parts:
            continue
        json.loads(path.read_text(encoding="utf-8"))


def verify_file_sizes() -> None:
    excluded = {
        "node_modules",
        "vendor",
        ".venv",
        "dist",
        "ephemeris",
        "__pycache__",
        ".pytest_cache",
    }
    oversized = [
        path for path in ROOT.rglob("*")
        if path.is_file() and path.name not in {"package-lock.json", "uv.lock"}
        and not (set(path.parts) & excluded)
        and len(path.read_text(encoding="utf-8", errors="ignore").splitlines()) > 500
    ]
    if oversized:
        raise SystemExit(f"first-party files exceed 500 lines: {oversized}")


def main() -> None:
    verify_json()
    verify_file_sizes()
    check(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/verified",
            "tests/golden",
            "tests/differential/test_iztro_palace_parity.py",
            "-q",
        ],
        ROOT,
    )
    check(["npm.cmd", "run", "build"], ROOT / "apps" / "observatory")
    print("verified v1 release gate passed")


if __name__ == "__main__":
    main()
