#!/usr/bin/env python3
"""Protected Stage 2 entrypoint.

Validator and grader code always call this file:
  python src/run_impl.py --input INPUT_TSV --out OUTPUT_TSV

Students should not modify this file. Put Stage 2 logic in either:
- src/numeric_literal_classifier.py (Python teams)
- src/NumericLiteralClassifier.java (Java teams)
"""
from __future__ import annotations

try:
  from json_bridge import main
except ModuleNotFoundError:
  from .json_bridge import main


if __name__ == "__main__":
    raise SystemExit(main())