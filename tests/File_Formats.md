# File Formats (Authoritative)

This document is kept in `tests/` because these formats are used directly while building and running test files.
All `.tsv` files use tab-separated values (TSV): fields delimited by one or more tab characters.

## Canonical Test File: `tests/*.expected.tsv`

Delimiter: one or more TAB characters (`\t+`).

Columns (required order):

1. `input`
2. `expected` (`Accept` or `Reject`)
3. `kind` (`BIN_INT | OCT_INT | DEC_INT | ZERO_INT | HEX_INT | FLOAT | IMAG | -`)
4. `case_id` (stable identifier such as `#HEX_0012`)
5. `note` (optional, can include labels such as `@trace`)

Rules:

- Keep existing `case_id` values stable once shared.
- Do not duplicate `case_id` values.
- For empty input, use `<EPS>` in the `input` column.

## JFLAP Batch Convenience File: `tests/*.jflap.batch.txt`

Generated from canonical TSV files.

Line format:

`inputString` followed by spaces then `Accept` or `Reject`.

Rules:

- Omits `case_id` and notes.
- Omits `<EPS>` rows because empty input is not portable in batch text format.

## JFLAP Munual Input File: `tests/*.jflap.manual.txt`
If `tests/*.jflap.manual.txt` exists for the same test set (for example `tests/public.jflap.manual.txt`), manually verify all listed `<EPS>` rows.
