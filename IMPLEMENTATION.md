# Implementation Log

This document tracks the implementation progress of the self-hosted chart service
following the steps defined in `specs/implementation_plan.md`.

## Status Overview

| Step | Title | Status | Commit | Notes |
|------|-------|--------|--------|-------|
| S1 | Project scaffold & config | done | s1 | FastAPI app factory boots; venv installs cleanly. |
| S2 | Database setup & migrations | done | s2 | Alembic offline SQL renders the full schema; SQLite import test passes. |
| S3 | ID generation & health endpoint | done | s3 | 6 unit/integration tests passing. |
| S4 | Pydantic request/response schemas | done | s4 | 14 tests passing including discriminated range, source-mode rules, indicator wiring. |
| S5 | Chart CRUD routes (create + get) | done | s5 | 18 tests passing; `POST /api/charts` and `GET /api/charts/{id}` wired with dependency-injected DB. |
| S6 | Chart update, soft-delete, listing | done | s6 | 25 tests passing; PUT/DELETE/GET list endpoints with pagination + filter. |
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

### S3 — ID generation & health endpoint

- Added `app/core/ids.py` (`generate_chart_id`) using `secrets.choice` over a 64-char URL-safe alphabet.
- Added `app/api/routes/health.py` with `GET /health` returning 200/`ok` on success and 503/`degraded` on DB failure.
- Wired the health router into `create_app()`.
- Added `tests/conftest.py` with an in-memory SQLite-backed FastAPI fixture (dependency override on `get_db`), plus `tests/test_ids.py` and `tests/test_health.py`.
- `pytest -q` reports 6 passes.

### S4 — Pydantic request/response schemas

- Added `app/domain/schemas/chart_request.py` with discriminated `FixedRange`/`RelativeRange`, source/instrument/view/layout/style/indicator/series models, `schema_version` default `1`, and a model validator that enforces direct-vs-provider rules, max 50k data points, series-id uniqueness, and indicator source linkage.
- Added `app/domain/schemas/chart_response.py` with create/list/error response models.
- Added `app/domain/schemas/normalized_payload.py` (`PayloadMeta`, `PayloadSeries`, `NormalizedChartPayload`, `ChartGetResponse`).
- Added `tests/test_chart_schemas.py` covering the cross-field rules. `pytest -q` reports 14 passes.

### S5 — Chart CRUD routes (create + get)

- Added `app/domain/services/chart_service.py` with `create_chart`/`get_chart` (plus update/delete/list helpers used by S6 next) and a `_split_definition` helper that stores inline series in the `inline_series` column keyed by series id.
- Added `app/api/errors.py` with domain exceptions (`ChartNotFoundError`, `ChartDeletedError`, etc.), a JSON-shape error response handler, and a request-validation handler that returns `{ "error": { code, message } }`.
- Added `app/api/dependencies.py` with FastAPI dependency wrappers.
- Added `app/api/routes/charts.py` with `POST /api/charts` (returns view/embed/api URLs from `BASE_URL`) and `GET /api/charts/{id}` (raw definition + inline series; render-payload pipeline lands in S10).
- Wired error handlers and chart router into `app/main.py`.
- Added `tests/test_chart_crud.py` with positive/negative create/get coverage. Sidestepped the `HTTP_422_UNPROCESSABLE_ENTITY` deprecation by using the literal `422`. Suite is at 18 passing tests.

### S6 — Chart update, soft-delete, listing

- Added `PUT /api/charts/{id}`, `DELETE /api/charts/{id}` (204), and `GET /api/charts?page&limit&source_kind` routes.
- Relaxed `SeriesInput` cross-field rule so provider charts may omit both inline data and an indicator; instead, `ChartCreateRequest` enforces "direct ⇒ inline data" and "provider ⇒ no inline data + range required". This was discovered when writing the update test that swaps to an `eodhd` source.
- Tightened direct-chart rule to require inline data on every non-indicator series.
- Made the pagination test order-agnostic to dodge same-microsecond timestamp ties on SQLite.
- 25 tests passing.






