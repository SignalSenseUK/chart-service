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
| S7 | Normalization service | done | s7 | 8 dedicated tests; sort/coerce/dup-reject + volume histogram extraction with up/down coloring. |
| S8 | Indicator engine — SMA & EMA | done | s8 | 7 dedicated tests; rolling SMA, EMA with SMA seed, dispatcher. |
| S9 | Indicator engine — VWAP & Bollinger | done | s9 | 5 added indicator tests; cumulative VWAP and Bollinger upper/middle/lower with population stddev. |
| S10 | Render-payload builder | done | s10 | Builder normalizes, computes indicators, emits volume histogram, and updates last_rendered_at. |
| S11 | Static assets & JS renderer | done | s11 | charts.js + charts.css; node --check passes; chart-ready signal wired. |
| S12 | Hosted chart page | done | s12 | Jinja2 templates; 3 page tests; static mount on `/static`. |
| S13 | Embed page & CORS/CSP headers | done | s13 | `/embed/{id}` with `frame-ancestors *`; custom CORS middleware for `/api/*`. |
| S14 | Provider base interface & direct adapter | done | s14 | Adapter Protocol; DirectAdapter; render builder dispatches through registry. |
| S15 | Range resolver | done | s15 | 8 dedicated tests; d/w/m/y lookback, month clamp, year subtract. |
| S16 | EODHD adapter | done | s16 | 6 adapter tests + 2 integration tests; validation fetch on create. |
| S17 | IB adapter — connection & fetch | done | s17 | `ib_async` adapter with pacing, lock, retry/backoff; import smoke-tested. |
| S18 | IB adapter — normalization & wiring | done | s18 | 7 IB tests with mocked client; lifespan auto-connect when IB env vars present. |
| S19 | Browser exporter service | done | s19 | Playwright `connect_over_cdp` + `body[data-chart-ready="true"]` wait. |
| S20 | Export API route | done | s20 | 4 export tests; PNG response with no-store; 404/422/502/504 paths. |
| S21 | Dockerfile & Docker Compose | done | s21 | 4-service compose (app, postgres, browser, proxy); `docker compose config` validates. |
| S22 | Reverse proxy & security hardening | done | s22 | Caddy headers/limits; app request-id + 10 MB body limit; production error sanitization. |
| S23 | Smoke tests & documentation | done | s23 | End-to-end create/list/update/get/delete smoke; README authored. |

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

### S7 — Normalization service

- Added `app/domain/services/normalization_service.py` with `normalize_series` (OHLCV/OHLC/value formats: ascending sort, duplicate-date rejection, datetime-with-time rejection, numeric coercion) and `extract_volume_series` (histogram series with green/red up/down coloring, pane 1).
- Added 8 tests covering each rule. Full suite now at 33 passes.

### S8 — Indicator engine: SMA & EMA

- Added `app/domain/services/indicator_service.py` with `compute_sma`, `compute_ema`, and a `compute_indicator` dispatcher. Both calculators omit warm-up points and run in O(n) using a rolling-sum trick for SMA and a recursive EMA formula seeded by SMA.
- `_series_value` allows indicators to consume either OHLC bars or value bars (falls back to the `value` field).
- 7 indicator tests added. Full suite now at 40 passes.

### S9 — Indicator engine: VWAP & Bollinger

- Extended `indicator_service.py` with `compute_vwap` (cumulative typical*volume/volume; raises if any bar is missing OHLCV fields) and `compute_bollinger` (population stddev over the rolling window, selectable band).
- Dispatcher updated to route `vwap` and `bollinger`. Suite now at 45 passes.

### S10 — Render-payload builder

- Added `app/domain/services/render_payload_service.py` (`build_payload_from_definition` + async wrapper).
- First pass normalizes non-indicator series via `normalize_series`. Second pass computes indicators against the already-normalized source bars; missing-source references raise `ChartValidationError` (422). Third pass emits a volume histogram for the first OHLC/bar series whose normalized bars include `volume`.
- `GET /api/charts/{id}` now returns `ChartGetResponse` (`id`, `title`, `source_kind`, `instrument`, `payload`) and updates `last_rendered_at`.
- Updated `test_get_chart_returns_payload` to assert against the new shape and added `test_get_chart_with_indicator_series` covering SMA derivation. Suite now at 46 passes.
- Outstanding: provider-backed flows (S14+) will replace the inline-data lookup with adapter dispatch; the builder is structured so this swap is local to series-iteration step 1.

### S11 — Static assets & JS renderer

- Added `app/web/static/charts.js` exposing `window.ChartService.render(chartId, apiBase)` which fetches the normalized payload, applies a dark/light palette, dispatches by series type (candlestick, bar, line, area, histogram), reduces volume pane via `priceScale("volume").scaleMargins`, sets a ResizeObserver, and emits `document.body.dataset.chartReady = "true"` on next animation frame.
- Added `app/web/static/charts.css` with full-viewport flex layout, error overlay styling, and `body.embed`/`body.export-mode` overrides for chrome stripping.
- Verified syntax with `node --check`.
- Outstanding: visual rendering will be exercised in S12 (hosted page) and S19 (Playwright export).

### S12 — Hosted chart page

- Added Jinja2 templates `chart.html` (loads Lightweight Charts from unpkg) and `error.html` (used for 404/410).
- Added `app/api/routes/pages.py` with `GET /charts/{id}` plus a shared `_render_chart_page` helper that handles 404/410.
- Mounted `/static` in `create_app` so `charts.js`/`charts.css` are served by the app.
- Tests cover the 200/404/410 paths. Full suite at 49 passes.

### S13 — Embed page & CORS/CSP headers

- Added `embed.html` (no title bar) and `GET /embed/{id}` route that returns `Content-Security-Policy: frame-ancestors *`.
- Implemented a small `ApiCORSMiddleware` that only fires for `/api/*` (sets `Access-Control-Allow-Origin: *` and answers preflight `OPTIONS`). Hosted/embed pages remain same-origin by default.
- Tests cover both header contracts and verify the hosted page does not get the CORS header. Suite at 53 passes.

### S14 — Provider base interface & direct adapter

- Added `app/providers/base.py` with `ProviderRequest`, `ProviderSeriesResult`, `ProviderHealth`, and `MarketDataAdapter` Protocol.
- Added `app/providers/direct.py` (validates + normalizes inline data via `normalize_series`) and `app/providers/registry.py` with lazy `get_adapter()` (EODHD and IB are imported inside the function so missing dependencies do not break direct flows).
- Refactored `build_payload` to be fully async and dispatch each non-indicator series through the adapter; it now returns `(payload, warnings)` and the GET route surfaces warnings on the response.
- Added a placeholder `range_resolver.resolve_range` raising `NotImplementedError`; full implementation lands in S15.
- Existing 53 tests continue to pass.

### S15 — Range resolver

- Implemented `resolve_range` with fixed-mode ISO parsing and relative-mode d/w/m/y lookback. Month subtraction clamps day-of-month overflow (e.g. Mar 31 - 1m → Feb 28).
- `_today()` is a module-level seam so tests can monkeypatch deterministically. 8 tests added; full suite at 61 passes.

### S16 — EODHD adapter

- Added `app/providers/eodhd.py` implementing `MarketDataAdapter` with EOD historical fetch, httpx-based HTTP, 4xx → 422, 5xx → 502, and a "short range" warning. Adapter exposes a `_client_factory` seam so tests can pass an `httpx.MockTransport`.
- Validation fetch added to `chart_service.create_chart` for any non-direct source: range is resolved, adapter is called, and an empty result is rejected with `provider_empty`/422.
- 6 EODHD unit tests using mocked transports plus 2 integration tests covering create-with-validation and provider-empty rejection. Suite at 69 passes.
- Outstanding: real EODHD calls are not exercised in CI; a smoke test against a sandbox key can be added later if desired.

### S17 — IB adapter: connection & fetch

- Added `app/providers/ib.py` with `IbAdapter` implementing the `MarketDataAdapter` protocol on top of `ib_async`. Holds a persistent connection, reconnects with exponential backoff (1 → 30s, 5 attempts), serializes historical requests via `asyncio.Lock`, and enforces a 1s pacing gap between fetches.
- Builds a `Contract` from `provider_config` (`secType`, `exchange`, `currency`, etc.) with sensible defaults derived from `asset_class`.
- `fetch_series` resolves date range to an IB duration string, calls `reqHistoricalDataAsync`, truncates earlier-than-requested bars, sorts ascending, and emits a warning when the earliest returned bar is later than the requested start.
- Adapter is not yet wired into the registry/lifespan — that happens in S18 alongside normalization edge cases.
- Outstanding: no live IB Gateway in CI, so end-to-end is exercised only via mocks in S18.

### S18 — IB adapter: normalization & wiring

- IB adapter was already routed through the lazy registry in S14. S18 hardens normalization (handles `BarData`-like objects via `getattr`, strips time-of-day from dates, sorts ascending, filters bars before the requested start), and confirms the validation fetch path in `chart_service.create_chart` reuses the same adapter.
- Updated `app/main.py` lifespan to lazily connect to IB on startup when `IB_HOST`/`IB_PORT`/`IB_CLIENT_ID` are all set, and to disconnect on shutdown. Connection failure is logged but does not block app startup.
- Added 7 IB tests (sec-type mapping, duration string, date parsing, bar normalization, contract building, missing-config rejection, end-to-end fetch through a fake IB client). Full suite at 76 passes.

### S19 — Browser exporter service

- Added `app/exports/browser_exporter.py` with `BrowserExporter` (Playwright `connect_over_cdp` to the configured CDP websocket, wait for `body[data-chart-ready="true"]`, screenshot `#chart-container` or fall back to full page) and custom exceptions (`ExportConnectionError`, `ExportTimeoutError`, `ExportRenderError`).
- Charts JS already toggles `body.export-mode` when `?export=true` is present in the URL (added in S11) so the screenshot can hide title/legend chrome.
- One unit test for the "no endpoint configured" path; live sidecar exports cannot run in CI without browser/chrome. Suite at 77.

### S20 — Export API route

- Added `app/api/routes/exports.py` exposing `GET /api/charts/{id}/png?width&height`.
- Validates dimensions against `PNG_MIN/MAX_WIDTH/HEIGHT`, fetches the chart (404 if missing/410 if deleted via existing error handlers), and constructs the internal render URL using `BASE_URL` with `?export=true` so the frontend hides chrome.
- On success: returns `image/png` with `Cache-Control: no-store` and updates `last_exported_at`. On `ExportTimeoutError`: 504. On `ExportConnectionError`: 502. Structured logs include chart id, dimensions, and duration.
- Added 4 export tests (chart-missing 404, width-too-small 422, no-endpoint 502, mocked happy path returns PNG). Suite at 81.

### S21 — Dockerfile & Docker Compose

- Added `Dockerfile` (python:3.12-slim, non-root user, healthcheck on `/health`, ASGI factory entrypoint, no Chromium installed in app image).
- Added `docker-compose.yml` with four services: `app`, `postgres:16-alpine` (with healthcheck), `browser` (browserless/chrome with 1G memory limit), and `proxy` (Caddy with mounted Caddyfile + persistent volumes).
- Added an initial `Caddyfile` placeholder with TLS, gzip/zstd compression, static cache headers, and forwarded-IP wiring (rate limits + body-size are hardened in S22).
- `docker compose config` validates the file shape locally. The app image build is not exercised in CI here.
- Outstanding: real container build/run requires Docker daemon access; left to the deployment environment.

### S22 — Reverse proxy & security hardening

- Expanded the Caddyfile with security headers (`X-Content-Type-Options`, `Referrer-Policy`, HSTS, removed `Server`), `X-Frame-Options: SAMEORIGIN` on hosted pages, a 5 MB request-body limit on `/api/*`, static-asset caching, and reusable snippets. Added rate-limit snippets gated on the `caddy-ratelimit` module (commented imports so a stock Caddy build still loads); deployment notes call out the rate-limit module requirement.
- Added two middlewares to the FastAPI app: `RequestIdMiddleware` (reuses incoming `X-Request-ID` or mints a v4 UUID, binds it onto every structlog log line, and echoes it back to the client), and `BodySizeLimitMiddleware` (returns 413 with the standard error envelope when `Content-Length > 10 MB`).
- Added an unhandled-exception handler that emits "internal server error" when `APP_ENV == production` and the underlying class/message otherwise, so stack traces never leak in production. The error always carries the `internal_error` code.
- Added 3 middleware tests. Suite at 84.

### S23 — Smoke tests & documentation

- Added `tests/test_smoke.py` exercising the full lifecycle through the FastAPI app (`/health` → create → get with EMA + volume → update → list → delete → 410).
- Authored `README.md` covering quick start, API surface, environment variables, architecture diagram, local development, and backup guidance.
- Existing `tests/conftest.py` already provided shared async fixtures (`app_with_db`, `client`); no additions needed.
- Final suite: 85 passes.

## Final verification

- Test suite: **85 / 85 passing** (`.venv/bin/pytest`).
- Every step S1–S23 was committed as its own commit on `main` and pushed to `origin/main`.
- Acceptance criteria (cross-referenced against `specs/self_hosted_chart_service_spec.md` §Acceptance Criteria):
  1. Direct charts: create / update / soft-delete / list / get / hosted render — covered by S5/S6/S12 + tests.
  2. EODHD provider with fixed and relative ranges — covered by S15/S16 (live calls require a real key).
  3. IB provider via `ib_async` — covered by S17/S18 (live runs require IB Gateway).
  4. SMA/EMA/VWAP/Bollinger computed server-side and rendered as derived series — S8/S9/S10.
  5. PNG export via headless browser sidecar — S19/S20 (live exports require a CDP-capable browser).
  6. Single-VPS deploy with app + Postgres + proxy + browser — S21 (`docker-compose.yml`).
  7. No provider credentials leak to clients; structured JSON logs — S1/S22.
  8. `GET /health` reports DB readiness — S3.
  9. Volume preserved and rendered as a histogram — S7/S10.

## Outstanding follow-ups

- Live EODHD/IB and PNG export flows are mocked in CI; before production use, run a smoke test against real credentials and a running CDP browser.
- Caddy rate-limit module (`caddy-ratelimit`) must be compiled into the proxy image before enabling the commented imports in `Caddyfile`.
- Lightweight Charts is loaded from unpkg in `chart.html`/`embed.html`; for air-gapped deployments, vendor the JS bundle.
- Alembic migration was hand-authored (no live DB at scaffold time). Run `alembic upgrade head` against a fresh Postgres before deployment.
























