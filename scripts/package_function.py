"""Assemble the CloudBase HTTP cloud-function package for the calculation API.

Layout produced under .deploy-stage/cloudfunctions/destiny-api/:
    scf_bootstrap        # LF-only startup script, uvicorn on :9000
    third_party/         # linux cp310 wheels (HTTP functions install nothing)
    site/src/            # fortune_core, keeps parents[3] ephemeris resolution
    site/apps/api/       # FastAPI entrypoints
    site/data/ephemeris  # pinned de440s.bsp

Run from the project root:
    .venv/Scripts/python.exe scripts/package_function.py
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / ".deploy-stage" / "cloudfunctions" / "destiny-api"
DIAG_FLAG = ROOT / ".deploy-stage" / "diag-mode"

CODE_DIRS = ("src/fortune_core", "apps/api", "data/ephemeris")

BOOTSTRAP = (
    "#!/bin/sh\n"
    'cd "$(dirname "$0")"\n'
    'export PYTHONPATH="$PWD/third_party:$PWD/site/src:$PWD/site/apps/api"\n'
    'export FORTUNE_TRUST_PROXY="${FORTUNE_TRUST_PROXY:-true}"\n'
    "export FORTUNE_AI_BUDGET_SCOPE=single_worker\n"
    "exec /var/lang/python310/bin/python3.10 -m uvicorn app:app --host 0.0.0.0 --port 9000\n"
)

DEPS = [
    "fastapi==0.139.2",
    "starlette==1.3.1",
    "pydantic==2.13.4",
    "uvicorn==0.51.0",
    "httpx==0.28.1",
    "lunar-python==1.4.8",
    "skyfield==1.54",
    "tzdata==2026.3",
]

DIAG_SERVER = '''"""Temporary cold-start diagnostic server: returns the app import traceback."""

from http.server import BaseHTTPRequestHandler, HTTPServer
import traceback


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        try:
            import app  # noqa: F401  full API import chain
            body = b"IMPORT_OK"
        except BaseException:
            body = traceback.format_exc().encode("utf-8", "replace")
        self.send_response(200)
        self.send_header("content-type", "text/plain; charset=utf-8")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args) -> None:
        pass


HTTPServer(("0.0.0.0", 9000), Handler).serve_forever()
'''


def resolve_diag_mode() -> bool:
    """The diag server answers anyone with the full import traceback; packaging it must be deliberate."""
    if not DIAG_FLAG.exists():
        return False
    if os.environ.get("FORTUNE_ALLOW_DIAG_PACKAGE") == "1":
        print("WARNING: diag-mode package requested (FORTUNE_ALLOW_DIAG_PACKAGE=1) — do not deploy this to production.", file=sys.stderr)
        return True
    sys.exit(
        "refusing to package: .deploy-stage/diag-mode is present.\n"
        "The diag server would return the full import traceback to anyone who reaches the function.\n"
        "Delete the flag file, or set FORTUNE_ALLOW_DIAG_PACKAGE=1 to package it deliberately."
    )


def main() -> None:
    if STAGE.exists():
        shutil.rmtree(STAGE)
    (STAGE / "site" / "src").mkdir(parents=True)
    (STAGE / "site" / "apps").mkdir(parents=True)
    (STAGE / "site" / "data").mkdir(parents=True)

    shutil.copytree(ROOT / "src" / "fortune_core", STAGE / "site" / "src" / "fortune_core")
    shutil.copytree(ROOT / "apps" / "api", STAGE / "site" / "apps" / "api")
    shutil.copytree(ROOT / "data" / "ephemeris", STAGE / "site" / "data" / "ephemeris")
    for cache in STAGE.rglob("__pycache__"):
        shutil.rmtree(cache)
    for junk in STAGE.rglob("*.pyc"):
        junk.unlink()

    bootstrap = STAGE / "scf_bootstrap"
    if resolve_diag_mode():
        (STAGE / "diag.py").write_text(DIAG_SERVER, encoding="ascii")
        bootstrap.write_bytes(
            (
                "#!/bin/sh\n"
                'cd "$(dirname "$0")"\n'
                'export PYTHONPATH="$PWD/third_party:$PWD/site/src:$PWD/site/apps/api"\n'
                "exec /var/lang/python310/bin/python3.10 diag.py\n"
            ).encode("ascii")
        )
    else:
        bootstrap.write_bytes(BOOTSTRAP.encode("ascii"))

    subprocess.run(
        [
            "uv",
            "pip",
            "install",
            "--target",
            str(STAGE / "third_party"),
            "--python-platform",
            "x86_64-unknown-linux-gnu",
            "--python-version",
            "3.10",
            "--index-url",
            "https://pypi.tuna.tsinghua.edu.cn/simple",
            *DEPS,
        ],
        check=True,
    )

    py_files = sum(1 for path in STAGE.rglob("*.py"))
    size_mb = sum(path.stat().st_size for path in STAGE.rglob("*") if path.is_file()) / 1e6
    print(f"packaged: {py_files} py files, {size_mb:.1f} MB total -> {STAGE}")


if __name__ == "__main__":
    main()
