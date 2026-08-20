# AGENTS.md

## Project

This repository is a fork of `engineerinvestor/Portfolio-Analysis`.

The goal of this fork is to adapt the existing portfolio analysis application for Korean-listed stocks and ETFs while reusing the upstream architecture, analysis logic, optimization logic, visualizations, and Streamlit UI wherever practical.

Do not rebuild functionality that already works in the upstream project without a clear reason.

## Source of Truth

Before implementation, read:

1. `AGENTS.md`
2. `docs/specification.md`
3. `ai-share/PROTOCOL.md`
4. Relevant existing source code and tests

`CLAUDE.md` is inherited from the upstream repository and may be used as reference for the original architecture.

If `CLAUDE.md` conflicts with `AGENTS.md` or `docs/specification.md`, the fork-specific documents take precedence.

## Development Principles

- Prefer minimal, focused changes over broad rewrites.
- Reuse existing analysis and optimization code whenever possible.
- Preserve existing public APIs unless a change is required by the specification.
- Keep market-data concerns separated from portfolio-analysis logic.
- Do not introduce unnecessary frameworks, abstractions, or dependencies.
- Do not implement postponed features unless explicitly requested.
- Avoid unrelated cleanup or refactoring during feature work.
- Preserve the upstream MIT license and attribution.

## Environment

- Python 3.12 is the primary development environment.
- Prefer `uv` for local Python environment and dependency management.
- Keep project dependencies declared in `pyproject.toml`.
- Do not commit virtual environments, secrets, credentials, or local configuration.

## Testing

Before completing a task:

- Run relevant existing tests.
- Add or update tests for changed behavior.
- Avoid making unit tests depend on live external market-data services where practical.
- Verify that the Streamlit application can start after changes affecting the UI or data layer.
- Report any test or environment blocker instead of silently bypassing it.

## Git

- Do not implement directly on `main`.
- Perform development on the current feature or fix branch.
- Do not merge into `main`.
- Do not force-push.
- Push completed work only to the current working branch.
- Use the Git identity already configured in the development environment.
- Do not override commit authorship with the upstream author's identity.

The user reviews the working branch before merging it into `main`.

## AI Collaboration

ChatGPT and Codex communication and session handover follow:

`./ai-share/PROTOCOL.md`

When a task is completed, record the required implementation summary, test results, blockers, and relevant decisions according to that protocol.
