# Implementation Log

This document tracks the implementation progress of the self-hosted chart service
following the steps defined in `specs/implementation_plan.md`.

## Status Overview

| Step | Title | Status | Commit | Notes |
|------|-------|--------|--------|-------|
| S1 | Project scaffold & config | done | s1 | FastAPI app factory boots; venv installs cleanly. |
| S2 | Database setup & migrations | done | s2 | Alembic offline SQL renders the full schema; SQLite import test passes. |
| S3 | ID generation & health endpoint | pending | — | — |
| S4 | Pydantic request/response schemas | pending | — | — |
| S5 | Chart CRUD routes (create + get) | pending | — | — |
| S6 | Chart update, soft-delete, listing | pending | — | — |
| S7 | Normalization service | pending | — | — |
| S8 | Indicator engine — SMA & EMA | pending | — | — |
| S9 | Indicator engine — VWAP & Bollinger | pending | — | — |
| S10 | Render-payload builder | pending | — | — |
| S11 | Static assets & JS renderer | pending | — | — |
| S12 | Hosted chart page | pending | — | — |
| S13 | Embed page & CORS/CSP headers | pending | — | — |
| S14 | Provider base interface & direct adapter | pending | — | — |
| S15 | Range resolver | pending | — | — |
| S16 | EODHD adapter | pending | — | — |
| S17 | IB adapter — connection & fetch | pending | — | — |
| S18 | IB adapter — normalization & wiring | pending | — | — |
| S19 | Browser exporter service | pending | — | — |
| S20 | Export API route | pending | — | — |
| S21 | Dockerfile & Docker Compose | pending | — | — |
| S22 | Reverse proxy & security hardening | pending | — | — |
| S23 | Smoke tests & documentation | pending | — | — |

## Detailed Notes

### S1 — Project scaffold & config

- Added `pyproject.toml`, `requirements.txt`, `requirements-dev.txt`, `.env.example`, `.gitignore`.
- Created `app/` package with `core/config.py` (Pydantic settings) and `core/logging.py` (structlog JSON).
- Implemented `app/main.py` with `create_app()` factory and lifespan stub.
- Confirmed `.venv/bin/python -c "from app.main import create_app; create_app()"` succeeds.
- Outstanding: no DB wiring yet (planned in S2); `ib_async` and `playwright` are included up-front to avoid later requirement churn but their browser/IB Gateway dependencies are deferred.

### S2 — Database setup & migrations

- Added `app/db/session.py` with lazy async engine, sessionmaker, `get_db` dependency, and `init_db`/`close_db` lifecycle helpers.
- Added `app/db/models.py` with `Chart` model and a `_JsonB` type decorator that uses JSONB on Postgres and JSON elsewhere (keeps SQLite test paths usable).
- Set up Alembic (`alembic.ini`, `app/db/migrations/env.py`, `script.py.mako`, hand-written `0001_initial_charts` revision) including all four indexes from the spec.
- Wired `init_db`/`close_db` into `app/main.py` lifespan, guarded by a configured `DATABASE_URL` so the app can still boot in dev without a database.
- Verified `alembic upgrade head --sql` renders the expected Postgres schema; verified `Base.metadata.create_all` works against SQLite for tests.
- Outstanding: real-Postgres apply will happen in the deployment step (S21+). No Alembic autogenerate run because there is no live DB; migration is hand-authored.


