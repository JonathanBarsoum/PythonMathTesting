#!/usr/bin/env python3
"""Protected Python JSON adapter for Stage 2.

This script owns stdin/stdout JSON transport for Python teams. Students should
only edit src/numeric_literal_classifier.py.
"""
from __future__ import annotations

import contextlib
import importlib
import io
import json
import sys

REQUEST_VERSION = 1


def main() -> int:
    request = json.load(sys.stdin)
    if request.get("version") != REQUEST_VERSION:
        raise RuntimeError(
            f"Unsupported request version {request.get('version')!r}. Expected {REQUEST_VERSION}."
        )
    cases = request.get("cases")
    if not isinstance(cases, list):
        raise RuntimeError("Request JSON must contain a list under 'cases'.")

    captured = io.StringIO()
    with contextlib.redirect_stdout(captured):
        try:
            student_module = importlib.import_module("numeric_literal_classifier")
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "Python mode selected but src/numeric_literal_classifier.py is missing. Copy "
                "src/numeric_literal_classifier.py.template to src/numeric_literal_classifier.py first."
            ) from exc
        classify_num_lit = getattr(student_module, "classify_num_lit", None)
        if not callable(classify_num_lit):
            raise RuntimeError(
                "src/numeric_literal_classifier.py must define classify_num_lit(input_text)."
            )
        results = []
        for case in cases:
            decision = classify_num_lit(case.get("input", ""))
            if not isinstance(decision, (tuple, list)) or len(decision) != 2:
                raise RuntimeError(
                    "classify_num_lit(input_text) must return a 2-item tuple/list: "
                    "(actual, actual_kind)."
                )
            actual, actual_kind = decision
            if not isinstance(actual, str) or not isinstance(actual_kind, str):
                raise RuntimeError(
                    "classify_num_lit(input_text) must return strings for both actual and actual_kind."
                )
            results.append(
                {
                    "case_id": case.get("case_id", ""),
                    "actual": actual,
                    "actual_kind": actual_kind if actual == "Accept" else "-",
                }
            )

    suppressed = captured.getvalue().strip()
    if suppressed:
        print(
            "WARNING: stdout generated inside src/numeric_literal_classifier.py was suppressed. "
            "Use stderr for debugging output.",
            file=sys.stderr,
        )
        print(suppressed, file=sys.stderr)

    json.dump({"version": REQUEST_VERSION, "results": results}, sys.stdout, ensure_ascii=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())