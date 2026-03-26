# CS 3110 Group Project: Python Numeric Literal NFA
## Goal

Design and implement an NFA-based recognizer for Python numeric literals based on the Python reference lexical specification.

References:

- [Python Lexical Analysis — Numeric Literals][lexicalAnalysisNumericLiterals]
- [Python Reference — Notation][pythonNotationDef]

## Protected Files and Interface

Do **NOT** edit protected files and never save them as their hashes can change. Breaking the required grading and validation interface may cause execution failures and point deductions (including major deductions on Stage 2 correctness if the grader cannot run your submission as required).

Protected files (**do not modify!**):

- `tools/nfa_runner.py`
- `tools/check_stage1_artifacts.py`
- `tools/check_stage2_impl.py`
- `tools/validate.py`
- `tools/export_jflap_batch.py`
- `tests/public.expected.tsv`
- `tests/File_Formats.md`
- `src/run_impl.py`
- `src/json_bridge.py`
- `src/run_classifier.py`
- `src/RunClassifier.java`
- `src/JsonUtil.java`
- `src/numeric_literal_classifier.py.template`
- `src/NumericLiteralClassifier.java.template`
- `PROJECT.md`

## Timeline and Process Requirements

1. Stage 1 **must** be completed before Stage 2 implementation begins. The `nfa` tag should be used before any coding starts, or you will be pendalized: -5 points.
2. Make sure correct **tags** are used for **grading**. Stage 1 grading uses the `nfa` tag snapshot; Stage 2 grading uses the `code` tag snapshot. You are responsible for points deduction caused by incorrect tagging.
3. Always **commit** the stage deliverables first, then create/push the stage tag (`nfa` or `code`). Premature tagging before commit snapshots will be penalized: -5 per occurrence.
4. Commits should be **distributed** roughly evenly across the assignment timeline. Last-weekend-only commits will be penalized: -10 points.
5. Fewer than **10** total commits across both stages may be penalized: -10
6. Team meeting minutes must be recorded and commited on the same day in `README.md` (most recent first).

## Repository Rules

1. Keep all deliverables in the required paths and formats.
2. Use clear commit messages and meaningful commit granularity.

## Stage 1 Blueprint

Design the NFA blueprint artifacts first, then freeze that snapshot with the `nfa` tag.

### Deliverables

1. `nfa/`:
   - `num_lit.jff` — your final combined NFA covering all Python numeric literal kinds.
   - `bin_int.jff`, `oct_int.jff`, `dec_int.jff`, `zero_int.jff`, `hex_int.jff`, `float.jff`, `imag_num.jff` — required per-category sub-NFAs built and kept during design. You are encouraged to have more sub-NFAs such as `digipart.jff` and `exponent.jff`.
   - `type_map.tsv` — maps each accepting state ID in `num_lit.jff` to its literal kind (see `tests/File_Formats.md`).
2. `tests/student.expected.tsv`: your own test cases with expected accept/reject and kind labels. (Incorrect test cases provided by you will be penalized for *misunderstanding of the Python Language Specifications*.)
3. [`README.md`](README.md): Fill out the required information as you work on the project, especially meeting minutes, AI usage, member contributions, and extra features.

### Recommended Workflow and Requirements

1. Read and understand the Python Language Specifications that your NFAs are based on: (again: incorrect test cases provided by you will be penalized for *misunderstanding of the Python Language Specifications*.)
   - [Python Lexical Analysis — Numeric Literals][lexicalAnalysisNumericLiterals]
   - [Python Reference — Notation][pythonNotationDef]
2. Build the required sub-NFAs above first, then merge them into `nfa/num_lit.jff`.
3. Include both accepted and rejected examples for each literal kind in your own test cases in `tests/student.expected.tsv`.
4. Validate your NFA against both public tests and your own tests using JFLAP Batch Test and Multiple Run:
   `tools/export_jflap_batch.py` converts a `.tsv` test file into up to two JFLAP-ready files (see `tests/File_Formats.md` for test-file format rules):
   - `.jflap.batch.txt`: non-empty input strings and expected Accept/Reject results;
   - `.jflap.manual.txt`: a manual checklist for empty-string (`<EPS>`) case(s) that JFLAP batch test files cannot handle automatically.   

   Run it once for the public test file and once for your own test file:
   ```bash
   python tools/export_jflap_batch.py --expected tests/public.expected.tsv \
       --out tests/public.jflap.batch.txt --manual-out tests/public.jflap.manual.txt

   python tools/export_jflap_batch.py --expected tests/student.expected.tsv \
       --out tests/student.jflap.batch.txt --manual-out tests/student.jflap.manual.txt
   ```

   Then load each batch file in JFLAP per [official Batch Test tutorial][jflapBatchTestTutorial]:
   1) From the JFLAP main menu, choose **Batch** menu -> **Batch Test**.
   2) Select your automaton file (`nfa/num_lit.jff`).
   3) Select your batch text file (e.g., `tests/public.jflap.batch.txt`) and run inputs for non-empty rows.
   4) If `tests/public.jflap.manual.txt` exists, manually verify the listed `<EPS>` case by entering the empty string (epsilon or lambda, depending on your JFLAP Preferences setting) in a separately opened NFA file. See [JFLAP: Running Input on an NFA](https://jflap.org/tutorial/fa/createfa/fa.html#runNFA).   
5. Pass local artifact checks before tagging:
   ```bash
   python tools/validate.py stage1
   ```
   This verifies Stage 1 artifact presence/format (`nfa/num_lit.jff`, the required sub-NFAs, `nfa/type_map.tsv`, `tests/student.expected.tsv`) and checks against public tests. (Public, hidden, and fuzzy tests are used for official grading. Incorrect test cases provided by you will be penalized for misunderstanding of the Python Language Specifications.)

6. Commit all Stage 1 deliverables first, then create/push tag `nfa`. (Please note the grading is **solely** based the tagged version - please test **thoroughly** before you tag any commit)
   ```bash
   git tag nfa
   git push origin nfa
   ```

***Reminder***: Stage 1 **must** be completed before Stage 2 implementation begins. The `nfa` tag should be used before any coding starts, or you will be pendalized: -5 points. (see all [process requirements](#timeline-and-process-requirements))

## Stage 2 Product

Implement the Stage 1 blueprint in Python or Java using maintainable explicit state/transition logic, then freeze that snapshot with the `code` tag.

### Deliverables
1. `src/`: your "Python Numeric Literal" classifier implementation file with starter template provided (see [Recommended Workflow](#cp-starter-template) below).
   #### Python Team
   - `numeric_literal_classifier.py`
   #### Java Team
   - `NumericLiteralClassifier.java`
2. `nfa/`: (whether there were changes to them after Stage 1 tagging of `nfa`)
   - `num_lit.jff`
   - `type_map.tsv`
3. `tests/student.expected.tsv`(whether there were changes to them after Stage 1 tagging of `nfa`. Incorrect test cases provided by you will be penalized for *misunderstanding of the Python Language Specifications*.)
4. [`README.md`](README.md): Fill out the required information as you work on the project, especially meeting minutes, AI usage, member contributions, and extra features.

**DO NOT EDIT** the following protected files in `src/`: (see the list of [all protected files](#protected-files-and-interface))
- `run_impl.py` — grading/validation interface (`--input INPUT_TSV --out OUTPUT_TSV`)
- `json_bridge.py` — TSV handler and JSON driver
- `run_classifier.py` — Python JSON adapter/utility
- `RunClassifier.java` and `src/JsonUtil.java` — Java JSON adapter/utility

### Recommended Workflow and Requirements
<a id="cp-starter-template"></a>
1. Start by copying the provided starter template file to your classifier implementation file:

   Use **exactly one** flow below:
   #### Python Team
   **a.** Copy `src/numeric_literal_classifier.py.template` to `src/numeric_literal_classifier.py`

   Windows:
   ```powershell
   Copy-Item src/numeric_literal_classifier.py.template src/numeric_literal_classifier.py
   ```

   macOS/Linux:

   ```bash
   cp src/numeric_literal_classifier.py.template src/numeric_literal_classifier.py
   ```
   **b.** Implement `classify_num_lit(input_text)` in `src/numeric_literal_classifier.py`.

   #### Java team
   **a.** Copy `src/NumericLiteralClassifier.java.template` to `src/NumericLiteralClassifier.java`

   Windows:

   ```powershell
   Copy-Item src/NumericLiteralClassifier.java.template src/NumericLiteralClassifier.java
   ```

   macOS/Linux:

   ```bash
   cp src/NumericLiteralClassifier.java.template src/NumericLiteralClassifier.java
   ```

   **b.** Implement `classifyNumLit(...)` in `src/NumericLiteralClassifier.java`.

   #### Common requirements for all classifier implementations:
   - Use explicit state and transition representations; no hardcoded hit-or-miss literal case checking.
   - Keep transition logic maintainable and update-friendly (table or graph representation preferred)
   - Ensure behavior parity: your **current (Stage 2)** `nfa/num_lit.jff` and classifier function should behave **exactly** the same with **any** test string (public tests, your own tests, as well as hidden and fuzzy tests run by the grader).
   - The process that runs your numeric literal classifier function receives one JSON request document from `stdin` and sends one JSON response document back to `stdout`. So your classifier implementation should not read `stdin` or write to `stdout`; use `stderr` for debugging output if needed.

      JSON bridge behavior:
      - Normal success: `src/run_impl.py` writes the required actual TSV file.
      - Invalid JSON on stdout: the protected bridge stops with a contract error before writing output.
      - Child exits nonzero: the protected bridge reports the child stderr and stops.
      - Child interrupted or timed out: the protected bridge reports that status and stops.

3. Pass local checks before tagging:
   ```bash
   python tools/validate.py stage2
   ```
   This runs your implementation in `src` against public and your own test sets and reports pass/fail summaries. (Public, hidden, and fuzzy tests are used for official grading. Incorrect test cases provided by you will be penalized for misunderstanding of the Python Language Specifications.)

   Optional targeted debugging (usually not needed, because `tools/validate.py stage2` already runs `run_impl.py`):
   ```bash
   python src/run_impl.py --input INPUT_TSV --out OUTPUT_TSV
   ```

4. Commit all Stage 2 deliverables first, then create/push tag `code`. (Please note the grading is **solely** based the tagged version - please test **thoroughly** before you tag any commit)
   ```bash
   git tag code
   git push origin code
   ```

## Rubrics

Scoring weights for correctness for **each** stage (**Total** for both stages: 210 / 200):

1. DEC_INT: 25
2. ZERO_INT: 5
3. BIN_INT: 10
4. OCT_INT: 10
5. HEX_INT: 10
6. FLOAT: 40
7. IMAG: +5

*Process and professionalism deductions* can be applied as documented.

## Repository Rules

1. Keep all deliverables in the required paths and formats.
2. Use clear commit messages and meaningful commit granularity.

## Grading Notes

- Incorrect test cases provided by you will be penalized for misunderstanding of the Python Language Specifications.
- Public, hidden, and fuzzy tests are used for official grading. Only public and student-provided tests will be run by the `tools/alidate.py`.

[lexicalAnalysisNumericLiterals]: https://docs.python.org/3/reference/lexical_analysis.html#numeric-literals
[pythonNotationDef]: https://docs.python.org/3/reference/introduction.html#notation
[jflapBatchTestTutorial]: https://jflap.org/tutorial/batch/batch.htm