# Implementation Log

This document tracks the implementation progress of the self-hosted chart service
following the steps defined in `specs/implementation_plan.md`.

## Status Overview

| Step | Title | Status | Commit | Notes |
|------|-------|--------|--------|-------|
| S1 | Project scaffold & config | done | s1 | FastAPI app factory boots; venv installs cleanly. |
| S2 | Database setup & migrations | pending | — | — |
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

