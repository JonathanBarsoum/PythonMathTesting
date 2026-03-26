#!/usr/bin/env python3
"""Validate Stage 2 implementation outputs against expected test suites.

Runs the protected src/run_impl.py bridge on required test files and verifies
the generated actual TSV reports all rows as OK.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

TAB_SPLIT = re.compile(r"\t+")
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
TESTS = ROOT / "tests"
BUILD = ROOT / "build"


def require_exists(path: Path, label: str) -> bool:
    if path.exists():
        print(f"OK: {label} -> {path.relative_to(ROOT)}")
        return True
    print(f"MISSING: {label} -> {path.relative_to(ROOT)}")
    return False


def detect_student_impl() -> bool:
    python_impl = SRC / "numeric_literal_classifier.py"
    java_impl = SRC / "NumericLiteralClassifier.java"
    if python_impl.exists() and java_impl.exists():
        print(
            "FAIL: choose exactly one Stage 2 implementation path: "
            "src/numeric_literal_classifier.py or src/NumericLiteralClassifier.java"
        )
        return False
    if python_impl.exists():
        print(f"OK: Python Stage 2 implementation -> {python_impl.relative_to(ROOT)}")
        return True
    if java_impl.exists():
        print(f"OK: Java Stage 2 implementation -> {java_impl.relative_to(ROOT)}")
        return True
    print(
        "MISSING: Stage 2 implementation -> create src/numeric_literal_classifier.py or "
        "src/NumericLiteralClassifier.java from the provided template"
    )
    return False


def count_expected_rows(path: Path) -> int:
    total = 0
    with path.open("r", encoding="utf-8", newline="") as f:
        for raw in f:
            line = raw.rstrip("\r\n")
            if not line or line.startswith("#"):
                continue
            total += 1
    return total


def load_actual_rows(path: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        for raw in f:
            line = raw.rstrip("\r\n")
            if not line or line.startswith("#"):
                continue
            parts = TAB_SPLIT.split(line)
            while len(parts) < 7:
                parts.append("")
            rows.append(
                {
                    "input": parts[0],
                    "actual": parts[1],
                    "actual_kind": parts[2],
                    "case_id": parts[3],
                    "expected": parts[4],
                    "expected_kind": parts[5],
                    "match": parts[6],
                }
            )
    return rows


def run_suite(expected_path: Path, out_path: Path) -> tuple[bool, int, int, int]:
    cmd = [
        sys.executable,
        str(SRC / "run_impl.py"),
        "--input",
        str(expected_path),
        "--out",
        str(out_path),
    ]
    print("Running:", " ".join(cmd))
    result = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    if result.returncode != 0:
        if result.stderr.strip():
            print(result.stderr.strip())
        return False, 0, 0, 0

    if not out_path.exists():
        print(f"MISSING: output TSV -> {out_path.relative_to(ROOT)}")
        return False, 0, 0, 0

    expected_rows = count_expected_rows(expected_path)
    actual_rows = load_actual_rows(out_path)
    fails = sum(1 for r in actual_rows if r.get("match") != "OK")
    total = len(actual_rows)

    ok = True
    if total != expected_rows:
        print(
            "FAIL: row-count mismatch "
            f"({total} actual vs {expected_rows} expected) for {expected_path.name}"
        )
        ok = False
    if fails > 0:
        ok = False

    return ok, total - fails, fails, total


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--public", default="tests/public.expected.tsv", help="Public expected TSV path")
    ap.add_argument("--student", default="tests/student.expected.tsv", help="Student expected TSV path")
    ap.add_argument(
        "--allow-missing-student",
        action="store_true",
        help="Do not fail if tests/student.expected.tsv is missing",
    )
    args = ap.parse_args()

    print("== CS3110 Stage 2 Implementation Checks ==")

    ok = True
    ok &= require_exists(SRC / "run_impl.py", "Protected Stage 2 runner")
    ok &= detect_student_impl()

    public_path = (ROOT / args.public).resolve() if not Path(args.public).is_absolute() else Path(args.public)
    student_path = (ROOT / args.student).resolve() if not Path(args.student).is_absolute() else Path(args.student)

    ok &= require_exists(public_path, "Public tests")

    if not student_path.exists() and args.allow_missing_student:
        print(f"SKIP: Student tests not found -> {student_path.relative_to(ROOT)}")
    else:
        ok &= require_exists(student_path, "Student tests")

    if not ok:
        print("FAIL: missing required files for Stage 2 checks")
        return 1

    BUILD.mkdir(parents=True, exist_ok=True)

    suites: list[tuple[str, Path, Path]] = [
        ("public", public_path, BUILD / "public.actual.tsv"),
    ]
    if student_path.exists():
        suites.append(("student", student_path, BUILD / "student.actual.tsv"))

    overall_ok = True
    for label, expected_path, out_path in suites:
        print(f"\n-- Suite: {label} --")
        suite_ok, passed, failed, total = run_suite(expected_path, out_path)
        print(f"Result: {passed}/{total} OK, {failed} FAIL")
        overall_ok &= suite_ok

    if overall_ok:
        print("\nPASS: Stage 2 implementation checks completed")
        return 0

    print("\nFAIL: fix Stage 2 implementation mismatches before tagging `code`")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
