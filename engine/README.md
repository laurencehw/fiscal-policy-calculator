# Fiscal engine API on Vercel

The repository's FastAPI app (`api.py`) with only the scoring engine's
dependencies, deployed as one Vercel Python function (tools plan FPC-4,
decision F1(b)).

Vercel project settings:

- Root Directory: `engine`; "Include files outside the Root Directory" on (the default).
- Framework preset: FastAPI. `pyproject.toml` lists the dependencies and the build step.
- Environment variables:
  - `FISCAL_API_KEYS`: `site:<secret>`, the key the Next.js site sends.
  - `ANTHROPIC_API_KEY`: only if Ask runs here.
  - `FRED_API_KEY`: optional; the bundled seed is used without it.
  - `ASSISTANT_USAGE_DB=/tmp/assistant_usage.db`: the bundle is read-only.

Known limits:

- The first request after idle waits about 6 seconds while the engine warms up.
  After that, a preset scores in about 0.2 seconds.
- Ask's daily cost cap is kept in SQLite under `/tmp`, and the request rate limit
  in memory, so each running instance keeps its own count. Under load neither is
  a hard ceiling until they move to shared storage (planned with FPC-12).

Check locally from the repository root:

    python engine/build.py && python -c "import sys; sys.path.insert(0, 'engine'); import index"
