# AI Share

state: active
id: 20260820T164918+0900-agent
created_at: 2026-08-20T16:49:18+09:00
type: result
reply_to: none

## Message

Updated `AGENTS.md` as requested.

- Translated the complete repository agent guidance into Korean while preserving
  the existing project, precedence, development, environment, Git, and AI Share
  rules.
- Added a concise testing-scope rule directly to `AGENTS.md`; no separate testing
  policy document was created.
- Targeted tests are now the default for changed behavior and adjacent shared
  code only.
- The full test suite is run only when the user explicitly requests it.
- Final reports must state the exact verification scope and say
  `전체 회귀 테스트: 미실행 (사용자 요청 없음)` when applicable.
- Documentation-only changes may use document-appropriate validation instead of
  code tests.

Verification:

- `git diff --check`: passed.
- Code tests: not run because this is a documentation-only change.
- Full regression: not run because the user did not request it.

Blockers: none.
