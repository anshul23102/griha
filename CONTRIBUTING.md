# Contributing

Thanks for looking. Griha is a hackathon project, but fixes and improvements are welcome.

## Set up

```bash
git clone https://github.com/anshul23102/griha.git && cd griha
cd backend && uv sync && uv run pytest -q          # 150 tests
cd ../frontend && pnpm install && npx tsc -b       # the real typecheck
```

The full stack (Temporal, Prometheus, Grafana) and the browser tests are described in the README under *Quick start* and *Testing and CI*.

## Ground rules

- **Synthetic data only.** Never commit real personal or financial data, regulatory PDFs, or third-party datasets (`data-external/` is git-ignored on purpose).
- **Cite your source.** A change to a compliance control should name the paragraph and say whether it was read in the primary text. If you cannot verify it, label it *secondary* or *unverified*, as the existing controls do.
- **Say what is simulated.** Do not present a simulated feed or a synthetic figure as real. The README table "What is real, what is simulated, what is not built" must stay true.
- **Decision logic changes bump the version.** If a change alters decisions, compliance wording or output shape, bump `ENGINE_VERSION` in `backend/griha/config.py`; if it changes the policy file, bump its `version`.
- **Tests with the change.** Backend behaviour gets a pytest test; user-facing flows get a Playwright test in `frontend/e2e/run.mjs`.
- **Accessibility.** New pages must pass the axe checks used in the browser tests, in English and Hindi.

## Pull requests

Keep them focused, describe what changed and why, and note any regulatory paragraph involved. CI must be green: backend tests, bandit, pip-audit, frontend typecheck and build, and the Docker image check.
