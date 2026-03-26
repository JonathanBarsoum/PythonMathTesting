#!/usr/bin/env python3
"""Validate Stage 1 artifacts for the student template.

This script intentionally focuses on checks that are available in the starter repo:
- validates required Stage 1 files exist
- exports JFLAP batch/manual public test files
- optionally exports student test batch/manual files when present
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
TESTS = ROOT / "tests"
NFA = ROOT / "nfa"


def run(cmd: list[str]) -> int:
	print("Running:", " ".join(cmd))
	return subprocess.call(cmd, cwd=str(ROOT))


def require_exists(path: Path, label: str) -> bool:
	if path.exists():
		print(f"OK: {label} -> {path.relative_to(ROOT)}")
		return True
	print(f"MISSING: {label} -> {path.relative_to(ROOT)}")
	return False


def export_batch(expected_name: str, out_prefix: str) -> int:
	expected = TESTS / expected_name
	if not expected.exists():
		print(f"SKIP: {expected_name} not found")
		return 0
	return run(
		[
			sys.executable,
			str(TOOLS / "export_jflap_batch.py"),
			"--expected",
			str(expected),
			"--out",
			str(TESTS / f"{out_prefix}.jflap.batch.txt"),
			"--manual-out",
			str(TESTS / f"{out_prefix}.jflap.manual.txt"),
		]
	)


def main() -> int:
	print("== CS3110 Stage 1 Artifact Checks ==")
	ok = True
	ok &= require_exists(NFA / "num_lit.jff", "Combined NFA")
	ok &= require_exists(NFA / "type_map.tsv", "Type map")
	
	# Check required sub-NFAs
	sub_nfas = [
		"bin_int.jff",
		"oct_int.jff",
		"dec_int.jff",
		"zero_int.jff",
		"hex_int.jff",
		"float.jff",
		"imag_num.jff",
	]
	for sub_nfa in sub_nfas:
		ok &= require_exists(NFA / sub_nfa, f"Sub-NFA: {sub_nfa.split('.')[0].upper()}")
	
	ok &= require_exists(TESTS / "public.expected.tsv", "Public tests")
	ok &= require_exists(TESTS / "student.expected.tsv", "Student tests")

	rc = 0
	rc |= export_batch("public.expected.tsv", "public")
	rc |= export_batch("student.expected.tsv", "student")

	if ok and rc == 0:
		print("PASS: Stage 1 artifact checks completed")
		return 0
	print("FAIL: resolve missing files or export errors before submitting Stage 1")
	return 1


if __name__ == "__main__":
	raise SystemExit(main())
