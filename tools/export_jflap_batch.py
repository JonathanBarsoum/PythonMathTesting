#!/usr/bin/env python3
"""Export JFLAP batch test files from canonical expected TSV.

Input: tests/*.expected.tsv (5 columns, delimiter: \t+)
Outputs:
- *.jflap.batch.txt : input + spaces + Accept/Reject (no comments, no case_id, no <EPS>)
- *.jflap.manual.txt: checklist for <EPS> rows from expected TSV (manual verification)
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

TAB_SPLIT = re.compile(r"\t+")


def parse_expected_tsv(path: Path):
    cases = []
    with path.open("r", encoding="utf-8", newline="") as f:
        for raw in f:
            line = raw.rstrip("\r\n")
            if not line or line.startswith("#"):
                continue
            parts = TAB_SPLIT.split(line)
            if len(parts) < 4:
                raise ValueError(f"Bad line (need >=4 columns): {path}: {line!r}")
            while len(parts) < 5:
                parts.append("")
            inp, expected, kind, case_id, note = parts[:5]
            cases.append((inp, expected, kind, case_id, note))
    return cases


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--expected", required=True, help="Canonical expected TSV path")
    ap.add_argument("--out", required=True, help="Output JFLAP batch file path")
    ap.add_argument("--manual-out", required=True, help="Output epsilon checklist path")
    ap.add_argument("--min-gap", type=int, default=2, help="Minimum spaces between input and Accept/Reject")
    args = ap.parse_args()

    expected_path = Path(args.expected)
    out_path = Path(args.out)
    manual_path = Path(args.manual_out)

    cases = parse_expected_tsv(expected_path)

    non_eps = [(inp, exp, cid) for (inp, exp, kind, cid, note) in cases if inp != "<EPS>"]
    eps = [(cid, exp, kind, note) for (inp, exp, kind, cid, note) in cases if inp == "<EPS>"]

    max_len = max((len(inp) for (inp, _, _) in non_eps), default=0)

    lines = []
    for inp, exp, cid in non_eps:
        pad = max(args.min_gap, max_len - len(inp) + args.min_gap)
        lines.append(f"{inp}{' ' * pad}{exp}")

    out_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8", newline="\n")

    manual = []
    manual.append("How to verify <EPS> (empty input) cases with JFLAP Batch mode:\n\n")
    manual.append("This checklist is generated from <EPS> rows in the expected TSV passed to --expected.\n")
    manual.append("For public testing, tests/public.expected.tsv includes <EPS>, so this manual checklist must be included in your public-test verification.\n\n")
    manual.append("JFLAP flow (per official Batch tutorial: https://jflap.org/tutorial/batch/batch.htm):\n")
    manual.append("1) From the JFLAP main menu, choose Batch mode.\n")
    manual.append("2) Select your automaton file (for this project: nfa/num_lit.jff).\n")
    manual.append("3) Select your batch text file (for example: tests/public.jflap.batch.txt) and run inputs for non-empty rows.\n")
    manual.append("4) Then manually verify each <EPS> row listed below using empty input entry (epsilon or lambda depending on your JFLAP preference).\n\n")
    manual.append("case_id\texpected\tkind\tnote\n")
    for cid, exp, kind, note in eps:
        manual.append(f"{cid}\t{exp}\t{kind}\t{note}\n")

    manual_path.write_text("".join(manual), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
