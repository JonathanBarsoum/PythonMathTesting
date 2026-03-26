#!/usr/bin/env python3
"""JFLAP NFA runner and classifier for Python numeric literals.

Parses a JFLAP .jff XML file and simulates the NFA on input strings.
Supports epsilon (lambda) transitions correctly via epsilon-closure.

JFLAP .jff XML structure (finite automaton):
  <structure>
    <type>fa</type>
    <automaton>
      <state id="0" name="q0">
        <x>100.0</x><y>100.0</y>
        <initial/>
      </state>
      <state id="1" name="q1">
        <x>200.0</x><y>100.0</y>
        <final/>
      </state>
      <transition>
        <from>0</from><to>1</to><read>a</read>
      </transition>
      <!-- epsilon transition: empty <read/> element -->
      <transition>
        <from>0</from><to>1</to><read/>
      </transition>
    </automaton>
  </structure>

CLI usage:
  # Single string test (print Accept/Reject + kind)
    python tools/nfa_runner.py --jff nfa/num_lit.jff --type-map nfa/type_map.tsv "0xFF"

  # Batch mode against expected TSV, write actual.tsv
    python tools/nfa_runner.py --jff nfa/num_lit.jff --type-map nfa/type_map.tsv \\
      --expected tests/public.expected.tsv --out build/public.actual.tsv
"""
from __future__ import annotations

import argparse
import re
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

TAB_SPLIT = re.compile(r"\t+")

# Maps case_id prefix (e.g. #HEX_) to scoring group name.
CASEID_PREFIX_TO_GROUP: dict[str, str] = {
    "DEC": "decimal",
    "ZRO": "decimal",
    "BIN": "binary",
    "OCT": "octal",
    "HEX": "hex",
    "FLT": "float",
    "IMG": "imaginary",
}

# Maps expected_kind to scoring group name.
KIND_TO_GROUP: dict[str, str] = {
    "DEC_INT":  "decimal",
    "ZERO_INT": "decimal",
    "BIN_INT":  "binary",
    "OCT_INT":  "octal",
    "HEX_INT":  "hex",
    "FLOAT":    "float",
    "IMAG":     "imaginary",
}

# Scoring groups: name -> (set_of_kinds, max_points)
SCORE_GROUPS: dict[str, tuple[frozenset[str], int]] = {
    "decimal": (frozenset({"DEC_INT", "ZERO_INT"}), 30),
    "binary":  (frozenset({"BIN_INT"}), 10),
    "octal":   (frozenset({"OCT_INT"}), 10),
    "hex":     (frozenset({"HEX_INT"}), 10),
    "float":     (frozenset({"FLOAT"}), 40),
    "imaginary": (frozenset({"IMAG"}), 5),
}


def case_id_to_group(case_id: str) -> str | None:
    """Map e.g. '#HEX_0012' -> 'hex', '#GEN_0001' -> None."""
    m = re.match(r"#([A-Z]{2,3})_", case_id)
    if not m:
        return None
    return CASEID_PREFIX_TO_GROUP.get(m.group(1))


def _expand_bracket_class(label: str) -> list[str]:
    """Expand bracket class syntax like [0-9A-F_] into explicit symbols.

    This supports common JFLAP shorthand where one transition arrow can
    represent many single-character transitions.
    """
    # Strip leading '[' and trailing ']'
    body = label[1:-1]
    out: set[str] = set()
    i = 0
    while i < len(body):
        ch = body[i]
        # Handle range like a-z
        if i + 2 < len(body) and body[i + 1] == "-":
            start = body[i]
            end = body[i + 2]
            if ord(start) <= ord(end):
                for code in range(ord(start), ord(end) + 1):
                    out.add(chr(code))
                i += 3
                continue
        out.add(ch)
        i += 1
    return sorted(out)


def expand_transition_label(label: str) -> list[str]:
    """Expand one JFLAP transition label into concrete symbols.

    Rules:
    - "" means epsilon and returns [""].
    - [..] classes are expanded (e.g., [0-9] -> 10 symbols).
    - Single-character labels are returned as-is.
    - Multi-character labels (without brackets) are split into symbols to
      remain permissive for compact authoring styles.
    """
    if label == "":
        return [""]
    if len(label) >= 2 and label.startswith("[") and label.endswith("]"):
        return _expand_bracket_class(label)
    if len(label) == 1:
        return [label]
    return list(label)


# ---------------------------------------------------------------------------
# NFA data model
# ---------------------------------------------------------------------------

class NFA:
    """Finite automaton loaded from a JFLAP .jff file."""

    def __init__(
        self,
        initial: str,
        accepting: frozenset[str],
        transitions: dict[str, dict[str, frozenset[str]]],
    ) -> None:
        self.initial = initial
        self.accepting = accepting
        # transitions[state][symbol] -> frozenset of target states
        # symbol == "" means epsilon
        self.transitions = transitions
        self._eps_cache: dict[frozenset[str], frozenset[str]] = {}

    def epsilon_closure(self, states: frozenset[str]) -> frozenset[str]:
        if states in self._eps_cache:
            return self._eps_cache[states]
        closure: set[str] = set(states)
        stack = list(states)
        while stack:
            s = stack.pop()
            for t in self.transitions.get(s, {}).get("", frozenset()):
                if t not in closure:
                    closure.add(t)
                    stack.append(t)
        result = frozenset(closure)
        self._eps_cache[states] = result
        return result

    def run(self, input_str: str) -> tuple[bool, frozenset[str]]:
        """Return (accepted, set_of_accepting_states_reached)."""
        current = self.epsilon_closure(frozenset({self.initial}))
        for char in input_str:
            next_states: set[str] = set()
            for s in current:
                next_states.update(
                    self.transitions.get(s, {}).get(char, frozenset())
                )
            current = self.epsilon_closure(frozenset(next_states))
        reached = current & self.accepting
        return bool(reached), reached


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def load_nfa(jff_path: str | Path) -> NFA:
    """Parse a JFLAP .jff file and return an NFA."""
    tree = ET.parse(str(jff_path))
    root = tree.getroot()
    automaton = root.find("automaton")
    if automaton is None:
        raise ValueError(f"No <automaton> element in {jff_path}")

    initial: str | None = None
    accepting: set[str] = set()
    all_states: set[str] = set()

    for state in automaton.findall("state"):
        sid = state.get("id")
        if sid is None:
            continue
        all_states.add(sid)
        if state.find("initial") is not None:
            initial = sid
        if state.find("final") is not None:
            accepting.add(sid)

    if initial is None:
        raise ValueError(f"No initial state in {jff_path}")

    raw: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    for trans in automaton.findall("transition"):
        from_el = trans.find("from")
        to_el = trans.find("to")
        read_el = trans.find("read")
        if from_el is None or to_el is None:
            continue
        from_s = (from_el.text or "").strip()
        to_s = (to_el.text or "").strip()
        # Epsilon: <read/> has None text; non-epsilon: <read>a</read>
        label = (read_el.text or "").strip() if read_el is not None else ""
        for symbol in expand_transition_label(label):
            raw[from_s][symbol].add(to_s)

    frozen: dict[str, dict[str, frozenset[str]]] = {
        s: {sym: frozenset(tgts) for sym, tgts in sym_map.items()}
        for s, sym_map in raw.items()
    }
    for s in all_states:
        if s not in frozen:
            frozen[s] = {}

    return NFA(
        initial=initial,
        accepting=frozenset(accepting),
        transitions=frozen,
    )


def load_type_map(tsv_path: str | Path) -> dict[str, str]:
    """Load nfa/type_map.tsv -> {state_id: kind}."""
    result: dict[str, str] = {}
    with open(tsv_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = TAB_SPLIT.split(line)
            if len(parts) < 2:
                continue
            kind = parts[0].strip()
            # State IDs may be space-separated within one or more columns
            state_ids = " ".join(parts[1:]).split()
            for sid in state_ids:
                if sid:
                    result[sid] = kind
    return result


def load_expected_tsv(path: str | Path) -> list[dict]:
    """Load a canonical expected.tsv into a list of case dicts."""
    cases = []
    with open(path, encoding="utf-8") as f:
        for raw in f:
            line = raw.rstrip("\n")
            if not line or line.startswith("#"):
                continue
            parts = TAB_SPLIT.split(line)
            while len(parts) < 5:
                parts.append("")
            cases.append(
                {
                    "input_raw": parts[0],
                    "input": "" if parts[0] == "<EPS>" else parts[0],
                    "expected": parts[1],
                    "kind": parts[2],
                    "case_id": parts[3],
                    "note": parts[4],
                }
            )
    return cases


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------

def classify(
    nfa: NFA, type_map: dict[str, str], input_str: str
) -> tuple[bool, str]:
    """Classify input_str. Returns (accepted: bool, kind: str)."""
    accepted, reached = nfa.run(input_str)
    if not accepted:
        return False, "-"
    kinds = {type_map[s] for s in reached if s in type_map}
    if not kinds:
        return True, "UNKNOWN"  # accepted but not in type_map — NFA design error
    if len(kinds) > 1:
        return True, "AMBIGUOUS"  # accepted by states of multiple kinds — design error
    return True, next(iter(kinds))


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def score_cases(
    results: list[dict],
    score_groups: dict[str, tuple[frozenset[str], int]] | None = None,
) -> tuple[dict[str, dict], float]:
    """
    Score a list of result dicts (each has keys: expected, kind, case_id,
    actual, actual_kind, correct).

    Returns:
        group_scores: dict[group_name -> {correct, total, max_pts, score}]
        total_score: float
    """
    if score_groups is None:
        score_groups = SCORE_GROUPS

    group_correct: dict[str, int] = defaultdict(int)
    group_total: dict[str, int] = defaultdict(int)

    for r in results:
        if r["expected"] == "Accept":
            group = KIND_TO_GROUP.get(r["kind"])
        else:
            group = case_id_to_group(r["case_id"])

        if group is None:
            continue  # GEN_* or unknown case_id prefix: skip group attribution

        group_total[group] += 1
        if r["correct"]:
            group_correct[group] += 1

    group_scores: dict[str, dict] = {}
    total_score = 0.0
    for gname, (_, max_pts) in score_groups.items():
        total = group_total.get(gname, 0)
        correct = group_correct.get(gname, 0)
        if total == 0:
            raw = float(max_pts)  # no test cases for this group: full credit
        else:
            raw = max_pts * correct / total
        group_scores[gname] = {
            "correct": correct,
            "total": total,
            "max_pts": max_pts,
            "score": raw,
        }
        total_score += raw

    return group_scores, round(total_score, 2)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _run_batch(
    nfa: NFA,
    type_map: dict[str, str],
    cases: list[dict],
) -> list[dict]:
    results = []
    for c in cases:
        acc, kind = classify(nfa, type_map, c["input"])
        actual = "Accept" if acc else "Reject"
        if c["expected"] == "Accept":
            correct = actual == "Accept" and kind == c["kind"]
        else:
            correct = actual == "Reject"
        results.append(
            {
                **c,
                "actual": actual,
                "actual_kind": kind,
                "correct": correct,
            }
        )
    return results


def main() -> int:
    ap = argparse.ArgumentParser(description="JFLAP NFA runner for CS3110")
    ap.add_argument("--jff", required=True, help="Path to num_lit.jff")
    ap.add_argument("--type-map", required=True, help="Path to type_map.tsv")
    ap.add_argument(
        "--expected", help="Path to expected.tsv for batch mode"
    )
    ap.add_argument("--out", help="Output .actual.tsv path (batch mode)")
    ap.add_argument(
        "inputs",
        nargs="*",
        help="Input strings to classify (inline mode, use <EPS> for empty string)",
    )
    args = ap.parse_args()

    nfa = load_nfa(args.jff)
    type_map = load_type_map(args.type_map)

    if args.expected:
        cases = load_expected_tsv(args.expected)
        results = _run_batch(nfa, type_map, cases)
        failed = sum(1 for r in results if not r["correct"])

        header = "# input\tactual\tactual_kind\tcase_id\texpected\texpected_kind\tmatch"
        lines = [header]
        for r in results:
            match = "OK" if r["correct"] else "FAIL"
            lines.append(
                f"{r['input_raw']}\t{r['actual']}\t{r['actual_kind']}\t"
                f"{r['case_id']}\t{r['expected']}\t{r['kind']}\t{match}"
            )

        if args.out:
            out_path = Path(args.out)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            print(
                f"Wrote {len(results)} results to {args.out}  "
                f"({len(results) - failed} OK, {failed} FAIL)"
            )
        else:
            print("\n".join(lines))

        if args.out:
            group_scores, total = score_cases(results)
            print(f"\n{'Group':<12} {'Correct':>8} {'Total':>6} {'Score':>8} {'Max':>5}")
            print("-" * 44)
            for gname, gs in group_scores.items():
                print(
                    f"{gname:<12} {gs['correct']:8} {gs['total']:6} "
                    f"{gs['score']:8.1f} {gs['max_pts']:5}"
                )
            print(f"{'TOTAL':<12} {'':8} {'':6} {total:8.1f} {'100':>5}")

        return 1 if failed else 0

    # Inline mode
    for inp in args.inputs:
        actual_str = "" if inp == "<EPS>" else inp
        acc, kind = classify(nfa, type_map, actual_str)
        print(f"{'Accept' if acc else 'Reject'}\t{kind}\t{inp!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
