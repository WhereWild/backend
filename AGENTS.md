# WhereWild Back-End Copilot Instructions

## Scope

This repo is the Python backend for WhereWild.

- Core libraries: `util/`
- Data/one-off pipelines: `scripts/`
- API entrypoint: `main.py`
- Large runtime data: `data/` (synced from Backblaze B2, not fully tracked in git)

## Stack

- Python 3.12+
- FastAPI + Uvicorn
- Pandas / NumPy / PyArrow
- GDAL-backed Docker workflow for GIS dependencies
- Dependency management with `uv`

## Ground Rules

- Avoid using bold for emphasis in Markdown, even for section labels or warnings.
- Keep changes focused and incremental; avoid broad rewrites.
- Prefer clear, direct logic over indirection.
- Keep functions/files concise; split large files into focused helpers/components when needed.
- Maintain low code smell: avoid redundant wrappers, unclear naming, and comments that explain obvious logic.
- Do not hardcode paths that are environment-specific.
- Preserve existing CLI/script behavior unless explicitly requested.
- When adding/adjusting scripts, keep them runnable via module form (`python -m ...`).

## Setup and Run

### Local Python (`uv`)

- Install deps: `uv sync`
- Run API locally (if your environment has required native deps): `uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000`
- Run tests: `uv run pytest -q`
- Run lint: `uv run ruff check .`

### Recommended GIS workflow (Docker)

- Start GDAL shell: `./gt.sh`
- Inside container, common helpers are preloaded (`api`, `api-fg`, `pd`, `pdb`, `b2-*`).
- `gt.sh` auto-runs `b2-mount` before opening the shell.

## Data and B2

- Shared source of truth is B2 bucket `wherewild-data`.
- Use read-only/mount flows by default; only use write helpers when intentionally publishing data.
- Common helper commands inside the GDAL shell:
    - `b2-mount` / `b2-umount`
    - `b2-pull-all` / `b2-pull-sync`
    - `b2-pull <path>` and `b2-push <path>`
    - `b2-push-all` / `b2-overwrite-remote` (require explicit force flags)

## Validation Checklist

Before finishing code changes:

1. Run targeted checks first (`uv run pytest -q <target>` when possible).
2. If API behavior changed, sanity-check endpoints via `api-fg` or `uvicorn`.
3. Keep docs in sync when behavior or workflows change (`README.md`, docs pages).

## Common Pitfalls

- Mixing host and container paths (`/workspace/...` is container path).
- Assuming B2 sync happens automatically in all run modes.
- Editing data-processing scripts without validating downstream expectations in `util/`.
- Introducing heavy abstractions where simple functions are sufficient.
