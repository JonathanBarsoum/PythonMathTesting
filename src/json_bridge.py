#!/usr/bin/env python3
"""Protected Stage 2 JSON bridge.

This module owns the stable CLI contract, canonical TSV parsing/writing, and the
JSON bridge to the protected Python or Java adapter.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

TAB_SPLIT = re.compile(r"\t+")
REQUEST_VERSION = 1
TIMEOUT_SECONDS = 60
VALID_ACCEPT_KINDS = {
    "BIN_INT",
    "OCT_INT",
    "DEC_INT",
    "ZERO_INT",
    "HEX_INT",
    "FLOAT",
    "IMAG",
}
VALID_ACTUAL = {"Accept", "Reject"}

ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "src"
OUT_DIR = SRC_DIR / "out"


def load_expected(path: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    with path.open(encoding="utf-8") as handle:
        for raw in handle:
            line = raw.rstrip("\r\n")
            if not line or line.startswith("#"):
                continue
            parts = TAB_SPLIT.split(line)
            while len(parts) < 5:
                parts.append("")
            input_raw, expected, kind, case_id, _note = parts[:5]
            rows.append(
                {
                    "input_raw": input_raw,
                    "input": "" if input_raw == "<EPS>" else input_raw,
                    "expected": expected,
                    "kind": kind,
                    "case_id": case_id,
                }
            )
    return rows


def write_actual(path: Path, rows: list[dict[str, str | bool]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# input\tactual\tactual_kind\tcase_id\texpected\texpected_kind\tmatch"]
    for row in rows:
        match = "OK" if row["match"] else "FAIL"
        lines.append(
            f"{row['input_raw']}\t{row['actual']}\t{row['actual_kind']}\t{row['case_id']}\t"
            f"{row['expected']}\t{row['kind']}\t{match}"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def detect_mode() -> str:
    python_impl = SRC_DIR / "numeric_literal_classifier.py"
    java_impl = SRC_DIR / "NumericLiteralClassifier.java"
    if python_impl.exists() and java_impl.exists():
        raise RuntimeError(
            "Found both src/numeric_literal_classifier.py and src/NumericLiteralClassifier.java. "
            "Choose exactly one Stage 2 implementation path."
        )
    if python_impl.exists():
        return "python"
    if java_impl.exists():
        return "java"
    raise RuntimeError(
        "Missing Stage 2 implementation. Copy either src/numeric_literal_classifier.py.template "
        "to src/numeric_literal_classifier.py (Python) or src/NumericLiteralClassifier.java.template "
        "to src/NumericLiteralClassifier.java (Java)."
    )


def build_request(cases: list[dict[str, str]]) -> str:
    payload = {
        "version": REQUEST_VERSION,
        "cases": [
            {
                "case_id": case["case_id"],
                "input_raw": case["input_raw"],
                "input": case["input"],
                "expected": case["expected"],
                "kind": case["kind"],
            }
            for case in cases
        ],
    }
    return json.dumps(payload, ensure_ascii=True)


def resolve_java_command(*names: str) -> str:
    for name in names:
        resolved = shutil.which(name)
        if resolved:
            return resolved
    raise RuntimeError(
        "Java mode requires a runnable Java toolchain, but none of these commands were found: "
        + ", ".join(names)
    )


def compile_java() -> None:
    java_files = [str(path) for path in SRC_DIR.glob("*.java")]
    if not java_files:
        raise RuntimeError("Java mode selected but no .java files were found in src/.")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    javac_cmd = resolve_java_command("javac", "openjdk.javac")
    result = subprocess.run(
        [javac_cmd, "-encoding", "UTF-8", "-d", str(OUT_DIR)] + java_files,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if result.returncode != 0:
        details = result.stderr.strip() or result.stdout.strip() or "javac failed"
        raise RuntimeError(f"Java compilation failed.\n{details}")


def run_child(mode: str, request_json: str) -> subprocess.CompletedProcess[str]:
    if mode == "python":
        cmd = [sys.executable, str(SRC_DIR / "run_classifier.py")]
    elif mode == "java":
        compile_java()
        java_cmd = resolve_java_command("java", "openjdk.java")
        cmd = [java_cmd, "-Dfile.encoding=UTF-8", "-cp", str(OUT_DIR), "RunClassifier"]
    else:
        raise RuntimeError(f"Unsupported Stage 2 mode: {mode}")

    try:
        return subprocess.run(
            cmd,
            cwd=str(ROOT),
            input=request_json,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            f"{mode.capitalize()} classifier timed out after {TIMEOUT_SECONDS}s. "
            "This usually means the implementation is stuck or waiting unexpectedly."
        ) from exc


def truncate(text: str, limit: int = 400) -> str:
    compact = text.strip().replace("\r", " ").replace("\n", " ")
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3] + "..."


def parse_response(mode: str, result: subprocess.CompletedProcess[str]) -> dict:
    if result.returncode != 0:
        if result.returncode < 0:
            headline = f"{mode.capitalize()} classifier was interrupted before it finished."
        else:
            headline = f"{mode.capitalize()} classifier exited with code {result.returncode}."
        details: list[str] = [headline]
        if result.stderr.strip():
            details.append("stderr:\n" + result.stderr.strip())
        if result.stdout.strip():
            details.append(
                "stdout (captured):\n" + truncate(result.stdout)
            )
        raise RuntimeError("\n\n".join(details))

    raw_stdout = result.stdout.strip()
    if not raw_stdout:
        raise RuntimeError(
            f"{mode.capitalize()} classifier produced no JSON on stdout. "
            "The protected adapter should write exactly one JSON document."
        )

    try:
        payload = json.loads(raw_stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"{mode.capitalize()} classifier wrote invalid JSON to stdout: "
            f"{exc.msg} at line {exc.lineno}, column {exc.colno}. "
            f"Captured stdout preview: {truncate(raw_stdout)!r}"
        ) from exc

    if not isinstance(payload, dict):
        raise RuntimeError("Classifier response must be a JSON object.")
    version = payload.get("version", REQUEST_VERSION)
    if version != REQUEST_VERSION:
        raise RuntimeError(
            f"Unsupported classifier response version: {version!r}. Expected {REQUEST_VERSION}."
        )
    results = payload.get("results")
    if not isinstance(results, list):
        raise RuntimeError("Classifier response must contain a JSON array under 'results'.")
    return payload


def validate_results(cases: list[dict[str, str]], payload: dict) -> list[dict[str, str | bool]]:
    results = payload["results"]
    if len(results) != len(cases):
        raise RuntimeError(
            "Classifier must return exactly one result for each input case in the same order "
            f"({len(cases)} expected, got {len(results)})."
        )

    seen_case_ids: set[str] = set()
    out_rows: list[dict[str, str | bool]] = []
    for index, (case, item) in enumerate(zip(cases, results), start=1):
        if not isinstance(item, dict):
            raise RuntimeError("Each classifier result must be a JSON object.")
        case_id = item.get("case_id")
        actual = item.get("actual")
        actual_kind = item.get("actual_kind")
        if not isinstance(case_id, str) or not case_id:
            raise RuntimeError("Each classifier result must include a non-empty string 'case_id'.")
        if case_id in seen_case_ids:
            raise RuntimeError(f"Duplicate classifier result for case_id {case_id!r}.")
        seen_case_ids.add(case_id)
        expected_case_id = case["case_id"]
        if case_id != expected_case_id:
            raise RuntimeError(
                "Classifier result ordering mismatch: "
                f"position {index} expected case_id {expected_case_id!r}, got {case_id!r}. "
                "Return results in the same order as input cases."
            )
        if not isinstance(actual, str) or actual not in VALID_ACTUAL:
            raise RuntimeError(
                f"Result for case_id {case_id!r} has invalid 'actual': {actual!r}. "
                "Expected 'Accept' or 'Reject'."
            )
        if not isinstance(actual_kind, str):
            raise RuntimeError(
                f"Result for case_id {case_id!r} must include string 'actual_kind'."
            )
        if actual == "Accept" and actual_kind not in VALID_ACCEPT_KINDS:
            raise RuntimeError(
                f"Result for case_id {case_id!r} has invalid accept kind {actual_kind!r}."
            )

        result = {
            "case_id": case_id,
            "actual": actual,
            "actual_kind": actual_kind if actual == "Accept" else "-",
        }
        if case["expected"] == "Accept":
            match = result["actual"] == "Accept" and result["actual_kind"] == case["kind"]
        else:
            match = result["actual"] == "Reject"
        out_rows.append({**case, **result, "match": match})

    return out_rows


def main() -> int:
    ap = argparse.ArgumentParser(description="Protected Stage 2 entrypoint")
    ap.add_argument("--input", required=True, help="Canonical expected TSV")
    ap.add_argument("--out", required=True, help="Actual TSV output path")
    args = ap.parse_args()

    try:
        cases = load_expected(Path(args.input))
        mode = detect_mode()
        request_json = build_request(cases)
        response = parse_response(mode, run_child(mode, request_json))
        rows = validate_results(cases, response)
        write_actual(Path(args.out), rows)
    except RuntimeError as exc:
        print(f"Stage 2 bridge error: {exc}", file=sys.stderr)
        return 1

    return 0