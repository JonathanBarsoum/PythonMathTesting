#!/usr/bin/env python3
"""Unified local validation entrypoint for Stage 1 and Stage 2."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"


def run(cmd: list[str]) -> int:
    print("Running:", " ".join(cmd))
    return subprocess.call(cmd, cwd=str(ROOT))


def main() -> int:
    ap = argparse.ArgumentParser(description="Local validation helper")
    sub = ap.add_subparsers(dest="stage", required=True)

    sub.add_parser("stage1", help="Validate Stage 1 artifacts and export JFLAP batch/manual files")

    p_stage2 = sub.add_parser("stage2", help="Validate Stage 2 implementation against public/student tests")
    p_stage2.add_argument("--public", default="tests/public.expected.tsv")
    p_stage2.add_argument("--student", default="tests/student.expected.tsv")
    p_stage2.add_argument("--allow-missing-student", action="store_true")

    args = ap.parse_args()

    if args.stage == "stage1":
        return run([sys.executable, str(TOOLS / "check_stage1_artifacts.py")])

    cmd = [
        sys.executable,
        str(TOOLS / "check_stage2_impl.py"),
        "--public",
        args.public,
        "--student",
        args.student,
    ]
    if args.allow_missing_student:
        cmd.append("--allow-missing-student")
    return run(cmd)


if __name__ == "__main__":
    raise SystemExit(main())
