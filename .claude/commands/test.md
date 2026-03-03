Run the full Istari test suite — identical to what CI runs in `.github/workflows/ci.yml`.

## Backend (in `backend/`)

Run these steps in order. Stop and report if any step fails.

1. **Lint:** `cd backend && ruff check src/ tests/`
2. **Type check:** `cd backend && mypy src/`
3. **Tests:** `cd backend && pytest`

The venv must be active: `source backend/.venv/bin/activate` before running backend steps.

## Frontend (in `frontend/`)

Run these steps in order. Stop and report if any step fails.

1. **Lint:** `cd frontend && npm run lint`
2. **Type check:** `cd frontend && npm run typecheck`
3. **Tests:** `cd frontend && npm test -- --run`

## Report

After all steps complete, print a summary table:

| Step | Result |
|------|--------|
| backend: ruff | ✓ / ✗ |
| backend: mypy | ✓ / ✗ |
| backend: pytest | ✓ / ✗ |
| frontend: lint | ✓ / ✗ |
| frontend: typecheck | ✓ / ✗ |
| frontend: vitest | ✓ / ✗ |

Include test counts (e.g. "273 passed") and any failure output.