# AI Share

state: active
id: 20260820T142819+0900-agent
created_at: 2026-08-20T14:28:19+09:00
type: result
reply_to: none

## Context

Korean market v1 was completed and pushed in `bbd1430` on
`feat/korean-market-v1`; the full suite passed with 209 tests.

## Message

Documented upstream-originated bugs found during the implementation in
`docs/upstream-issues.md`.

The document covers reproduction symptoms, causes, fixes, affected files,
commits, and verification for:

1. pandas 3 removal of `M`/`Y` resample aliases
2. Matplotlib legend handles/labels argument incompatibility
3. `BenchmarkComparison` using portfolio returns before initialization
4. Yahoo multi-ticker response order silently mismatching input weights

Korean-market feature additions themselves were intentionally excluded.
Blockers: none.
