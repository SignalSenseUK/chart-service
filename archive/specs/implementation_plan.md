# Self-Hosted Chart Service — Implementation Plan & Prompt Pack

> Generated from `specs/self_hosted_chart_service_spec.md`

---

## 1. Project Blueprint

### Milestone 1: Foundation & Core API

**Goal**: Stand up the FastAPI application skeleton, Postgres persistence, config/logging infrastructure, ID generation, and the full CRUD + listing API surface for direct-data charts.

**Components**: FastAPI app factory, Pydantic v2 domain schemas, SQLAlchemy 2.x async models, Alembic migrations, config module, structured logging, ID generator.

**Artifacts**: `POST/GET/PUT/DELETE /api/charts`, `GET /api/charts` (list), `GET /health`, database schema, migration files.

---

### Milestone 2: Data Normalization & Indicator Engine

**Goal**: Build the server-side pipeline that converts raw chart definitions (inline data) into the canonical normalized payload, including derived indicator series (SMA, EMA, VWAP, Bollinger Bands).

**Components**: Normalization service, indicator engine, render-payload builder.

**Artifacts**: Normalization module, indicator calculation module, normalized payload schema, unit tests for each indicator.

---

### Milestone 3: Frontend Rendering

**Goal**: Deliver the hosted chart page (`/charts/{id}`) and embed page (`/embed/{id}`) using TradingView Lightweight Charts v4, including responsive layout, volume histogram, theme support, and the chart-ready signal contract.

**Components**: HTML templates / static pages, JavaScript chart renderer (`charts.js`), CSS, page route handlers.

**Artifacts**: `chart.html`, `embed.html`, `charts.js`, `charts.css`, page routes.

---

### Milestone 4: EODHD Provider Integration

**Goal**: Implement the first external provider adapter — EODHD end-of-day historical data — with fixed and relative range resolution, so provider-backed charts can be created, persisted, and rendered with live data.

**Components**: Provider adapter base protocol, EODHD adapter, range resolver, chart service integration.

**Artifacts**: Provider base interface, EODHD adapter module, integration with chart creation & retrieval flows.

---

### Milestone 5: IB Provider Integration

**Goal**: Implement the Interactive Brokers historical-bar adapter via `ib_async`, including connection lifecycle management, pacing guardrails, and contract resolution.

**Components**: IB adapter, connection manager, pacing/guardrail logic.

**Artifacts**: IB adapter module, connection lifecycle manager, environment config for IB Gateway.

---

### Milestone 6: PNG Export

**Goal**: Deliver synchronous PNG export via the headless browser sidecar, connecting over CDP websocket with Playwright, honouring dimension bounds and timeouts.

**Components**: Browser exporter service, export API route, Docker Compose sidecar configuration.

**Artifacts**: `GET /api/charts/{id}/png`, browser exporter module, Docker Compose service definition.

---

### Milestone 7: Deployment & Hardening

**Goal**: Complete Docker Compose topology (app + Postgres + proxy + browser sidecar), reverse-proxy config, rate limiting, request-size limits, CORS/CSP headers, backup strategy, and end-to-end smoke tests.

**Components**: Dockerfiles, Docker Compose, Caddy/Nginx config, smoke test suite, README/ops docs.

**Artifacts**: `Dockerfile`, `docker-compose.yml`, proxy config, smoke tests, operational documentation.

---

## 2. Refined Implementation Steps

### Milestone 1 — Foundation & Core API

| Step | Objective | Main Changes | Deps |
|------|-----------|-------------|------|
| **S1** | Project scaffold & config | Create project layout (`app/`), `pyproject.toml` / `requirements.txt`, `app/core/config.py` (Pydantic `BaseSettings` reading env vars), `app/core/logging.py` (structlog JSON), `app/main.py` (FastAPI app factory). | — |
| **S2** | Database setup & migrations | `app/db/session.py` (async engine + session factory), `app/db/models.py` (SQLAlchemy `Chart` model), Alembic init + initial migration creating `charts` table with indexes. | S1 |
| **S3** | ID generation & health endpoint | `app/core/ids.py` (nanoid-style generator), `GET /health` route checking DB connectivity. | S2 |
| **S4** | Pydantic request/response schemas | `app/domain/schemas/` — `chart_request.py` (create/update input), `chart_response.py` (create response, get response, list response, error response). Validation rules per spec. | S1 |
| **S5** | Chart CRUD routes (create + get) | `app/api/routes/charts.py` — `POST /api/charts` (validate, persist, return URLs), `GET /api/charts/{id}` (retrieve, return definition). Direct-data only; no normalization yet — return raw definition. Wire router into `main.py`. | S2, S3, S4 |
| **S6** | Chart update, soft-delete, listing | `PUT /api/charts/{id}`, `DELETE /api/charts/{id}`, `GET /api/charts` (paginated, filtered). Soft-delete logic, 410 handling. `app/api/errors.py` for standard error responses. | S5 |

---

### Milestone 2 — Data Normalization & Indicator Engine

| Step | Objective | Main Changes | Deps |
|------|-----------|-------------|------|
| **S7** | Normalization service | `app/domain/services/normalization_service.py` — accept raw inline series, sort by date, validate, coerce types, produce canonical OHLCV bars and value points. | S4 |
| **S8** | Indicator engine — SMA & EMA | `app/domain/services/indicator_service.py` — SMA and EMA calculators operating on canonical bar arrays. Unit tests. | S7 |
| **S9** | Indicator engine — VWAP & Bollinger | Add VWAP (cumulative) and Bollinger Bands (middle/upper/lower) to indicator service. Unit tests. | S8 |
| **S10** | Render-payload builder | `app/domain/services/render_payload_service.py` — orchestrate normalization + indicators, produce `NormalizedChartPayload` matching the frontend contract. Volume extraction into histogram series. Wire into `GET /api/charts/{id}`. | S7, S9 |

---

### Milestone 3 — Frontend Rendering

| Step | Objective | Main Changes | Deps |
|------|-----------|-------------|------|
| **S11** | Static assets & JS renderer | `app/web/static/charts.js` — fetch payload from API, create Lightweight Charts instance, add series by type (candlestick, line, area, histogram), apply theme, emit chart-ready signal. `app/web/static/charts.css` — responsive base styles. | S10 |
| **S12** | Hosted chart page | `app/web/templates/chart.html` — minimal page shell loading `charts.js`. `app/api/routes/pages.py` — `GET /charts/{id}` serving the page with server-injected chart ID. Error states (404, provider failure, empty data). | S11 |
| **S13** | Embed page & CORS/CSP headers | `app/web/templates/embed.html` — stripped chrome. `GET /embed/{id}` route. `Content-Security-Policy: frame-ancestors *` on embed. `Access-Control-Allow-Origin: *` on `/api/` routes. | S12 |

---

### Milestone 4 — EODHD Provider

| Step | Objective | Main Changes | Deps |
|------|-----------|-------------|------|
| **S14** | Provider base interface & direct adapter | `app/providers/base.py` (Protocol), `app/providers/direct.py` (validates/normalizes inline data). Refactor chart service to use adapter dispatch. | S10 |
| **S15** | Range resolver | Utility to resolve fixed and relative ranges into concrete `start_date` / `end_date`. Parse lookback strings (`30d`, `12m`, `25y`). | S4 |
| **S16** | EODHD adapter | `app/providers/eodhd.py` — HTTP client, credential handling, response normalization. Validation fetch on chart creation (422 on failure). Timeout via `EODHD_TIMEOUT_MS`. | S14, S15 |

---

### Milestone 5 — IB Provider

| Step | Objective | Main Changes | Deps |
|------|-----------|-------------|------|
| **S17** | IB adapter — connection & fetch | `app/providers/ib.py` — `ib_async` connection manager (persistent connection, auto-reconnect with backoff), historical bar fetch, pacing guardrails, single in-flight request enforcement. | S14, S15 |
| **S18** | IB adapter — normalization & wiring | Normalize IB bars to canonical format, wire into chart creation (validation fetch) and retrieval. Environment config (`IB_HOST`, `IB_PORT`, `IB_CLIENT_ID`). | S17 |

---

### Milestone 6 — PNG Export

| Step | Objective | Main Changes | Deps |
|------|-----------|-------------|------|
| **S19** | Browser exporter service | `app/exports/browser_exporter.py` — connect to sidecar via `EXPORT_BROWSER_WS_ENDPOINT` using Playwright `connect_over_cdp`, load internal render URL, wait for chart-ready signal, capture screenshot. | S12 |
| **S20** | Export API route | `app/api/routes/exports.py` — `GET /api/charts/{id}/png?width=&height=`. Validate dimensions, call exporter, return `image/png` with `Cache-Control: no-store`. Error handling (404, 422, 504). | S19 |

---

### Milestone 7 — Deployment & Hardening

| Step | Objective | Main Changes | Deps |
|------|-----------|-------------|------|
| **S21** | Dockerfile & Docker Compose | `Dockerfile` (Python slim, no Chromium), `docker-compose.yml` (app, postgres, browser sidecar, proxy). Health checks. | S20 |
| **S22** | Reverse proxy & security | Caddy/Nginx config — TLS, compression, rate limits on `/api/charts` POST and `/png`, body size limits. | S21 |
| **S23** | Smoke tests & documentation | End-to-end smoke tests (create direct chart, view, export PNG). `README.md` with deployment instructions. Backup cron job example. | S22 |

---

### Coverage & Complexity Check

- **All milestones covered**: S1–S6 (M1), S7–S10 (M2), S11–S13 (M3), S14–S16 (M4), S17–S18 (M5), S19–S20 (M6), S21–S23 (M7). ✅
- **No large jumps**: Each step adds one focused concern. ✅
- **No redundancy**: Each step has a unique deliverable. ✅
- **Dependencies are linear with controlled fan-in**: No circular dependencies. ✅

---

## 3. Code-Generation Prompt Pack

### Step S1 — Project Scaffold & Configuration

```text
[INSTRUCTIONS FOR THE CODE-GENERATION LLM]

Context:
- We are building a self-hosted chart rendering service (Python/FastAPI/Postgres).
- This is the very first step. No code exists yet.
- The project lives in a repository root with a `specs/` folder containing the technical spec.

Task:
Create the initial project scaffold with configuration and logging.

Requirements:
1. Create `pyproject.toml` with project metadata and dependencies:
   - fastapi, uvicorn[standard], pydantic>=2.0, pydantic-settings
   - sqlalchemy[asyncio]>=2.0, asyncpg, alembic
   - structlog, python-json-logger
   - httpx (for EODHD later), playwright (for export later)
   - Dev deps: pytest, pytest-asyncio, httpx (for test client)
2. Create `app/__init__.py` (empty).
3. Create `app/core/__init__.py` (empty).
4. Create `app/core/config.py`:
   - A Pydantic `BaseSettings` class named `Settings` reading from env vars.
   - Fields: DATABASE_URL, BASE_URL, APP_ENV (default "development"), LOG_LEVEL (default "INFO"),
     EODHD_API_KEY (optional), EODHD_TIMEOUT_MS (default 30000),
     IB_HOST (optional), IB_PORT (optional int), IB_CLIENT_ID (optional int), IB_TIMEOUT_MS (default 30000),
     EXPORT_BROWSER_WS_ENDPOINT (optional), EXPORT_TIMEOUT_MS (default 15000),
     PNG_MIN_WIDTH (320), PNG_MIN_HEIGHT (200), PNG_MAX_WIDTH (2400), PNG_MAX_HEIGHT (1600),
     DB_POOL_SIZE (5), DB_MAX_OVERFLOW (10).
   - A module-level `get_settings()` function using `lru_cache`.
4. Create `app/core/logging.py`:
   - Configure `structlog` for JSON output.
   - A `setup_logging(log_level: str)` function to initialize structured logging.
   - A `get_logger(name: str)` convenience function.
5. Create `app/main.py`:
   - FastAPI application factory function `create_app() -> FastAPI`.
   - Call `setup_logging` on startup.
   - Include a lifespan context manager stub for future DB init.
   - App metadata: title="Chart Service", version="1.0.0".
6. Create a `.env.example` with all required env vars documented.

Output:
- All files listed above, with brief inline comments explaining non-obvious choices.
- A short summary of what was created.
```

---

### Step S2 — Database Setup & Migrations

```text
[INSTRUCTIONS FOR THE CODE-GENERATION LLM]

Context:
- The project scaffold exists with FastAPI app factory, Pydantic Settings config, and structlog logging.
- Files: app/main.py, app/core/config.py, app/core/logging.py, pyproject.toml.
- No database code exists yet.

Task:
Set up SQLAlchemy 2.x async database access and create the initial Alembic migration for the `charts` table.

Requirements:
1. Create `app/db/__init__.py` (empty).
2. Create `app/db/session.py`:
   - Create an async SQLAlchemy engine using `DATABASE_URL` from settings.
   - Use `DB_POOL_SIZE` and `DB_MAX_OVERFLOW` from settings.
   - Create an `async_sessionmaker` bound to the engine.
   - Provide an `async def get_db()` async generator for FastAPI dependency injection.
   - Provide `async def init_db()` and `async def close_db()` for lifespan management.
3. Create `app/db/models.py`:
   - A declarative base using SQLAlchemy 2.x `DeclarativeBase`.
   - A `Chart` model mapping to the `charts` table with columns:
     - id: Text, primary key
     - created_at: DateTime(timezone=True), server_default=now()
     - updated_at: DateTime(timezone=True), server_default=now(), onupdate=now()
     - deleted_at: DateTime(timezone=True), nullable
     - source_kind: Text, not null, check constraint for ('direct','eodhd','ib')
     - title: Text, nullable
     - chart_definition: JSONB, not null
     - inline_series: JSONB, nullable
     - last_rendered_at: DateTime(timezone=True), nullable
     - last_exported_at: DateTime(timezone=True), nullable
4. Initialize Alembic:
   - Create `alembic.ini` and `app/db/migrations/` directory.
   - Configure `env.py` to use async engine and import models for autogenerate.
   - Generate the initial migration creating the `charts` table.
   - Include index creation: idx_charts_created_at (created_at DESC), idx_charts_source_kind, idx_charts_chart_definition_gin (GIN on chart_definition), idx_charts_deleted_at (partial WHERE deleted_at IS NULL).
5. Update `app/main.py` lifespan to call `init_db()` on startup and `close_db()` on shutdown.

Output:
- All files listed above.
- The generated Alembic migration file.
- A short summary of what changed.
```

---

### Step S3 — ID Generation & Health Endpoint

```text
[INSTRUCTIONS FOR THE CODE-GENERATION LLM]

Context:
- Project scaffold, config, logging, database session, SQLAlchemy Chart model, and Alembic migration are in place.
- The FastAPI app factory in app/main.py has lifespan DB init/close.

Task:
Implement opaque chart ID generation and the GET /health endpoint.

Requirements:
1. Create `app/core/ids.py`:
   - A function `generate_chart_id(length: int = 16) -> str` producing URL-safe, non-sequential IDs.
   - Use Python's `secrets` module with a URL-safe alphabet (A-Z, a-z, 0-9, - _).
   - IDs should be 16 characters by default (sufficient entropy to prevent enumeration).
2. Create `app/api/__init__.py` (empty).
3. Create `app/api/routes/__init__.py` (empty).
4. Create `app/api/routes/health.py`:
   - `GET /health` endpoint.
   - Attempt a simple DB query (e.g., `SELECT 1`) using the async session.
   - On success: return `{"status": "ok", "database": "connected", "version": "1.0.0"}` with 200.
   - On DB failure: return `{"status": "degraded", "database": "disconnected", "version": "1.0.0"}` with 503.
5. Wire the health router into `app/main.py`.
6. Add a unit test in `tests/test_ids.py` verifying ID length, URL-safety, and uniqueness across 1000 generated IDs.

Output:
- All new and modified files.
- A short summary of what changed.
```

---

### Step S4 — Pydantic Request & Response Schemas

```text
[INSTRUCTIONS FOR THE CODE-GENERATION LLM]

Context:
- Project has: FastAPI app, config, logging, DB models, migrations, ID generation, health endpoint.
- No API schemas or chart routes exist yet.

Task:
Create the Pydantic v2 schemas for chart creation/update requests and all API responses.

Requirements:
1. Create `app/domain/__init__.py` and `app/domain/schemas/__init__.py` (empty).
2. Create `app/domain/schemas/chart_request.py` with models:
   - `SourceInput`: kind (Literal["direct","eodhd","ib"]), provider (Optional[str]), provider_config (Optional[dict])
   - `InstrumentInput`: symbol (str), asset_class (Literal["equity","forex","futures","crypto","index"]), label (Optional[str])
   - `FixedRange` / `RelativeRange` / `RangeInput`: discriminated union on mode field. Fixed: start_date, end_date as date strings (YYYY-MM-DD validated). Relative: lookback (str, regex validated for patterns like 30d, 12m, 25y), anchor (Literal["now"]).
   - `ViewInput`: title (Optional[str]), theme (Literal["light","dark"], default "dark"), mobile_responsive (bool, default True), timezone (str, default "UTC"), locale (str, default "en-GB")
   - `LayoutInput`: pane_mode (Literal["single","multi"], default "single"), legend (bool, default True), autosize (bool, default True)
   - `SeriesStyleInput`: color, line_width (1-4), opacity (0.0-1.0), up_color, down_color — all Optional.
   - `IndicatorInput`: name (Literal["sma","ema","vwap","bollinger"]), length (Optional[int]), stddev (Optional[float]), source_series (str), band (Optional[Literal["upper","middle","lower"]])
   - `SeriesInput`: id (str), type (Literal["candlestick","line","area","histogram","bar"]), pane (int, ge=0), data_format (Optional), data (Optional[list[dict]]), indicator (Optional[IndicatorInput]), style (Optional[SeriesStyleInput]), label (Optional[str])
   - `ChartCreateRequest`: source, instrument, range (Optional), view (Optional with defaults), layout (Optional with defaults), series (list[SeriesInput], min 1)
   - Add a model validator: if source.kind == "direct", at least one series must have inline data. If source.kind != "direct", no series may have inline data. Max 50000 data points per series.
3. Create `app/domain/schemas/chart_response.py` with models:
   - `ChartCreateResponse`: id, view_url, embed_url, api_url
   - `ChartSummary`: id, title, source_kind, created_at, updated_at
   - `ChartListResponse`: charts (list[ChartSummary]), total (int), page (int), limit (int)
   - `ErrorDetail`: code (str), message (str)
   - `ErrorResponse`: error (ErrorDetail)
4. Create `app/domain/schemas/normalized_payload.py` with models:
   - `PayloadMeta`: title, theme, timezone
   - `PayloadSeries`: id, type, pane, data (list[dict]), style (Optional[dict]), label (Optional[str])
   - `NormalizedChartPayload`: meta, layout_options (dict), series (list[PayloadSeries])
   - `ChartGetResponse`: id, title, source_kind, instrument (dict), payload (NormalizedChartPayload)
5. Add `schema_version: int = 1` to ChartCreateRequest for JSONB versioning.

Output:
- All schema files with field-level docstrings on non-obvious validations.
- A short summary of what changed.
```

---

### Step S5 — Chart CRUD Routes (Create & Get)

```text
[INSTRUCTIONS FOR THE CODE-GENERATION LLM]

Context:
- Project has: FastAPI app, config, logging, DB models (Chart), migrations, ID generation, health endpoint, and complete Pydantic schemas for request/response.
- No chart API routes exist yet.

Task:
Implement POST /api/charts and GET /api/charts/{id} for direct-data charts.

Requirements:
1. Create `app/domain/services/__init__.py` (empty).
2. Create `app/domain/services/chart_service.py`:
   - `async def create_chart(db, request: ChartCreateRequest) -> Chart`: generate ID, build chart_definition dict (source, instrument, range, view, layout, series without inline data), extract inline_series from series with data, persist Chart row, return model.
   - `async def get_chart(db, chart_id: str) -> Chart | None`: query by ID, return None if not found.
   - Check for deleted_at — if set, raise a domain exception that maps to 410.
3. Create `app/api/routes/charts.py`:
   - `POST /api/charts`: accept ChartCreateRequest, call chart_service.create_chart, return ChartCreateResponse with URLs built from BASE_URL.
   - `GET /api/charts/{id}`: call chart_service.get_chart, for now return the raw chart_definition and inline_series without normalization (placeholder until S10 wires the render payload builder).
   - Use FastAPI dependency injection for DB session.
4. Create `app/api/dependencies.py`:
   - Re-export `get_db` and `get_settings` as FastAPI dependencies.
5. Wire the charts router into `app/main.py` under prefix `/api`.
6. Add basic integration tests in `tests/test_chart_crud.py`:
   - Test creating a direct chart returns 201 with expected response shape.
   - Test getting a chart by ID returns 200.
   - Test getting a non-existent ID returns 404.

Output:
- All new and modified files.
- A short summary of what changed.
```

---

### Step S6 — Chart Update, Soft-Delete & Listing

```text
[INSTRUCTIONS FOR THE CODE-GENERATION LLM]

Context:
- Project has: full scaffold, DB, schemas, chart_service with create/get, POST and GET /api/charts routes, health endpoint, basic tests.
- Missing: update, delete, listing, and standardized error handling.

Task:
Implement PUT, DELETE, and paginated GET list endpoints, plus standardized error responses.

Requirements:
1. Create `app/api/errors.py`:
   - Define custom exception classes: ChartNotFoundError, ChartDeletedError, ValidationError.
   - Register FastAPI exception handlers that return the ErrorResponse schema with appropriate HTTP status codes (404, 410, 400/422).
2. Update `app/domain/services/chart_service.py`:
   - `async def update_chart(db, chart_id, request: ChartCreateRequest) -> Chart`: find chart, verify not deleted (410), verify source_kind unchanged (422), update chart_definition, inline_series, title, updated_at. Return updated model.
   - `async def delete_chart(db, chart_id: str)`: find chart, if not found raise 404, if already deleted raise 410, set deleted_at to now.
   - `async def list_charts(db, page, limit, source_kind) -> tuple[list[Chart], int]`: paginated query, exclude soft-deleted, order by created_at DESC, optional source_kind filter. Return (charts, total_count).
3. Update `app/api/routes/charts.py`:
   - `PUT /api/charts/{id}`: call update_chart, return ChartCreateResponse.
   - `DELETE /api/charts/{id}`: call delete_chart, return 204 No Content.
   - `GET /api/charts`: accept query params page (default 1), limit (default 20, max 100), source_kind (optional). Return ChartListResponse.
4. Register error handlers in `app/main.py`.
5. Add tests in `tests/test_chart_crud.py`:
   - Update a chart and verify updated_at changes.
   - Delete a chart and verify 204, then GET returns 410.
   - List charts with pagination.

Output:
- All new and modified files.
- A short summary of what changed.
```

---

### Step S7 — Normalization Service

```text
[INSTRUCTIONS FOR THE CODE-GENERATION LLM]

Context:
- Project has: full CRUD API for direct charts, DB, schemas, error handling, health endpoint.
- GET /api/charts/{id} currently returns raw chart_definition. No normalization pipeline exists.

Task:
Build the normalization service that converts raw inline series data into canonical internal representations.

Requirements:
1. Create `app/domain/services/normalization_service.py`:
   - `def normalize_series(raw_data: list[dict], data_format: str) -> list[dict]`:
     - Sort rows by ascending date (time field).
     - Reject duplicate dates within a series (raise ValueError with descriptive message).
     - Coerce numeric fields (open, high, low, close, volume, value) to float.
     - Validate time strings are YYYY-MM-DD format; reject datetime strings with time components.
     - For "ohlcv" format: validate presence of time, open, high, low, close, volume fields.
     - For "ohlc" format: validate time, open, high, low, close.
     - For "value" format: validate time, value.
     - Return sorted, validated, type-coerced list of canonical dicts.
   - `def extract_volume_series(ohlcv_data: list[dict], source_series_id: str) -> dict`:
     - Extract volume data from OHLCV bars into a histogram-type series payload.
     - Assign green color for bars where close >= open, red otherwise.
     - Return a PayloadSeries-compatible dict with type "histogram" and pane 1.
2. Add unit tests in `tests/test_normalization.py`:
   - Test sorting, duplicate rejection, type coercion, format validation.
   - Test volume extraction with correct coloring.

Output:
- All new files.
- A short summary of what changed.
```

---

### Step S8 — Indicator Engine: SMA & EMA

```text
[INSTRUCTIONS FOR THE CODE-GENERATION LLM]

Context:
- Project has: full CRUD API, normalization service producing canonical OHLCV/value bars.
- No indicator calculation exists yet.

Task:
Implement SMA and EMA indicator calculators.

Requirements:
1. Create `app/domain/services/indicator_service.py`:
   - `def compute_sma(bars: list[dict], length: int, field: str = "close") -> list[dict]`:
     - Compute rolling simple moving average over the specified field.
     - Return list of {"time": ..., "value": ...} dicts.
     - Omit the first (length - 1) bars where the average is not yet defined.
   - `def compute_ema(bars: list[dict], length: int, field: str = "close") -> list[dict]`:
     - Compute exponential moving average. Multiplier = 2 / (length + 1).
     - Seed with SMA of the first `length` bars.
     - Return list of {"time": ..., "value": ...} dicts starting from bar index (length - 1).
   - `def compute_indicator(name: str, bars: list[dict], config: dict) -> list[dict]`:
     - Dispatcher that routes to the correct calculator based on indicator name.
     - For "sma" and "ema", extract `length` from config and call the appropriate function.
     - Raise ValueError for unknown indicator names.
2. Add unit tests in `tests/test_indicators.py`:
   - Test SMA with known values (e.g., 5 bars, length 3 → verify exact outputs).
   - Test EMA with known values.
   - Test warm-up period handling (correct number of output points).
   - Test with "value" format data (single numeric field).

Output:
- All new files.
- A short summary of what changed.
```

---

### Step S9 — Indicator Engine: VWAP & Bollinger Bands

```text
[INSTRUCTIONS FOR THE CODE-GENERATION LLM]

Context:
- Project has: full CRUD API, normalization service, indicator service with SMA and EMA.
- Need to add VWAP and Bollinger Bands to complete the v1 indicator engine.

Task:
Add VWAP and Bollinger Bands calculators to the indicator service.

Requirements:
1. Update `app/domain/services/indicator_service.py`:
   - `def compute_vwap(bars: list[dict]) -> list[dict]`:
     - Compute cumulative VWAP over the dataset: cumulative(typical_price * volume) / cumulative(volume).
     - Typical price = (high + low + close) / 3.
     - Requires volume field; raise ValueError if volume is missing from any bar.
     - Return list of {"time": ..., "value": ...} starting from bar 0.
   - `def compute_bollinger(bars: list[dict], length: int, stddev: float = 2.0, band: str = "middle", field: str = "close") -> list[dict]`:
     - Middle band = SMA(length) of the specified field.
     - Upper band = middle + stddev * rolling_stddev(length).
     - Lower band = middle - stddev * rolling_stddev(length).
     - `band` parameter selects which band to return ("upper", "middle", "lower").
     - Omit the first (length - 1) points.
     - Return list of {"time": ..., "value": ...}.
   - Update `compute_indicator` dispatcher to handle "vwap" and "bollinger".
2. Add unit tests in `tests/test_indicators.py`:
   - Test VWAP with known OHLCV data.
   - Test Bollinger middle equals SMA.
   - Test Bollinger upper/lower with known stddev values.
   - Test VWAP raises error when volume is missing.

Output:
- Modified indicator_service.py.
- Updated tests.
- A short summary of what changed.
```

---

### Step S10 — Render Payload Builder

```text
[INSTRUCTIONS FOR THE CODE-GENERATION LLM]

Context:
- Project has: full CRUD API, normalization service, indicator service (SMA, EMA, VWAP, Bollinger).
- GET /api/charts/{id} still returns raw definition. No pipeline converts definition + data into the normalized frontend payload.

Task:
Build the render-payload builder that orchestrates normalization and indicators, and wire it into the GET chart endpoint.

Requirements:
1. Create `app/domain/services/render_payload_service.py`:
   - `async def build_payload(chart: Chart) -> NormalizedChartPayload`:
     - Extract view, layout, and series config from chart.chart_definition.
     - Build PayloadMeta from view config (title, theme, timezone).
     - Build layout_options from layout config.
     - For each series in the definition:
       a. If it has inline data (look up in chart.inline_series by series id): normalize via normalization_service.
       b. If it has an indicator config: find the source series data (already normalized), compute the indicator via indicator_service.compute_indicator.
       c. Build a PayloadSeries with id, type, pane, computed data, optional style and label.
     - If any OHLCV series exists, extract volume into a separate histogram series using normalization_service.extract_volume_series.
     - Return NormalizedChartPayload.
   - Handle missing source series for indicators gracefully (raise descriptive 422 error).
2. Update `app/api/routes/charts.py` GET /api/charts/{id}:
   - Call build_payload on the retrieved chart.
   - Return ChartGetResponse with id, title, source_kind, instrument (from chart_definition), and the built payload.
   - Update last_rendered_at timestamp on the chart.
3. Add integration test:
   - Create a direct chart with candlestick data + an SMA indicator series.
   - GET the chart and verify the payload contains both the price series and the computed SMA series with correct data points.

Output:
- All new and modified files.
- A short summary of what changed.
```

---

### Step S11 — Static Assets & JavaScript Renderer

```text
[INSTRUCTIONS FOR THE CODE-GENERATION LLM]

Context:
- Project has: full CRUD API, normalization, indicators, render-payload builder producing NormalizedChartPayload.
- GET /api/charts/{id} returns a JSON payload with meta, layout_options, and series arrays.
- No frontend rendering code exists yet.

Task:
Create the JavaScript chart renderer and CSS that will power both the hosted and embed pages.

Requirements:
1. Create `app/web/` directory with `static/` and `templates/` subdirectories. Add __init__.py files as needed.
2. Create `app/web/static/charts.js`:
   - Accept a chart ID and an API base URL.
   - Fetch the payload from `/api/charts/{chartId}`.
   - Create a TradingView Lightweight Charts `createChart()` instance on a container div.
   - Apply theme from payload.meta.theme (dark/light with appropriate color schemes).
   - Apply layout_options (autosize).
   - Iterate over payload.payload.series and add each:
     - "candlestick" → addCandlestickSeries(), set data
     - "line" → addLineSeries(), set data, apply style (color, lineWidth)
     - "area" → addAreaSeries(), set data
     - "histogram" → addHistogramSeries(), set data (for volume)
     - "bar" → addBarSeries(), set data
   - Apply series style properties (up_color, down_color, color, line_width, opacity) when present.
   - Handle pane assignment: for v1, volume histograms render in the price pane with priceScaleId: 'volume' and reduced height via scaleMargins.
   - After all series are added and data set, call `chart.timeScale().fitContent()`.
   - Emit chart-ready signal: `document.body.dataset.chartReady = 'true'`.
   - Handle errors: display a user-friendly message in the container div if fetch fails or data is empty.
   - Implement responsive resize using ResizeObserver on the container.
3. Create `app/web/static/charts.css`:
   - Full-viewport chart container styling.
   - Dark and light theme base styles (background, text color).
   - Minimal chrome: title bar area, error message styling.
   - Mobile-responsive rules (font sizes, padding).
4. Include TradingView Lightweight Charts v4 via CDN (unpkg or jsdelivr) in the HTML templates (created next step), not bundled.

Output:
- charts.js, charts.css files.
- A short summary of what was created.
```

---

### Step S12 — Hosted Chart Page

```text
[INSTRUCTIONS FOR THE CODE-GENERATION LLM]

Context:
- Project has: full backend API, render-payload builder, charts.js renderer, charts.css.
- No HTML pages or page-serving routes exist yet.

Task:
Create the hosted chart page and its serving route.

Requirements:
1. Create `app/web/templates/chart.html`:
   - Minimal HTML5 page.
   - Load Lightweight Charts v4 from CDN.
   - Load charts.css and charts.js from static paths.
   - Include a `<div id="chart-container">` taking full viewport.
   - Include a title bar `<div id="chart-title">` for the chart title (populated by JS).
   - Script block: read chart ID from a data attribute or inline variable injected server-side, call the renderer.
   - Include meta viewport tag for mobile responsiveness.
2. Create `app/api/routes/pages.py`:
   - `GET /charts/{id}`: serve chart.html with the chart ID injected.
   - First, validate the chart exists and is not deleted:
     - 404 → render a minimal "Chart not found" HTML page.
     - 410 → render a minimal "Chart has been removed" HTML page.
   - Use Jinja2 templates or simple string formatting to inject the chart ID.
   - Set appropriate Content-Type: text/html.
3. Mount static files directory in `app/main.py` at `/static`.
4. Wire the pages router into `app/main.py`.
5. Add `jinja2` to dependencies if using Jinja2 templates.

Output:
- chart.html template, pages.py route, updated main.py.
- A short summary of what changed.
```

---

### Step S13 — Embed Page & CORS/CSP Headers

```text
[INSTRUCTIONS FOR THE CODE-GENERATION LLM]

Context:
- Project has: full backend, charts.js, charts.css, hosted chart page at /charts/{id}.

Task:
Create the embed page and configure CORS/CSP headers per spec.

Requirements:
1. Create `app/web/templates/embed.html`:
   - Same rendering logic as chart.html but with stripped-down chrome.
   - No title bar, minimal margins and padding.
   - Body background matches theme.
   - Chart container fills the full iframe viewport.
2. Update `app/api/routes/pages.py`:
   - `GET /embed/{id}`: serve embed.html with chart ID injected.
   - Same 404/410 error handling as hosted page.
   - Add response header `Content-Security-Policy: frame-ancestors *` on embed responses.
3. Add CORS middleware or manual headers:
   - All routes under `/api/` shall include `Access-Control-Allow-Origin: *`.
   - Use FastAPI's CORSMiddleware configured for API routes.
   - The hosted page at `/charts/{id}` uses default same-origin framing (no special CSP).
4. Update `app/main.py` to include CORS middleware.

Output:
- embed.html, updated pages.py, updated main.py.
- A short summary of what changed.
```

---

### Step S14 — Provider Base Interface & Direct Adapter

```text
[INSTRUCTIONS FOR THE CODE-GENERATION LLM]

Context:
- Project has: full CRUD API, normalization, indicators, render-payload builder, frontend rendering pages.
- Currently, chart retrieval only handles inline data from chart.inline_series directly in the render-payload builder.
- No formal provider adapter abstraction exists.

Task:
Create the provider adapter protocol and refactor data retrieval to use adapter dispatch.

Requirements:
1. Create `app/providers/__init__.py` (empty).
2. Create `app/providers/base.py`:
   - Define `ProviderRequest` dataclass: symbol, asset_class, start_date, end_date, provider_config (dict).
   - Define `ProviderSeriesResult` dataclass: data (list[dict]), warnings (list[str]).
   - Define `ProviderHealth` dataclass: healthy (bool), message (str).
   - Define `MarketDataAdapter` Protocol with:
     - `async def fetch_series(self, request: ProviderRequest) -> ProviderSeriesResult`
     - `async def healthcheck(self) -> ProviderHealth`
3. Create `app/providers/direct.py`:
   - `DirectAdapter` implementing MarketDataAdapter.
   - `fetch_series`: extract inline data from the chart's inline_series, validate and normalize via normalization_service, return as ProviderSeriesResult.
   - `healthcheck`: always returns healthy.
4. Create `app/providers/registry.py`:
   - A function `get_adapter(source_kind: str) -> MarketDataAdapter` that returns the appropriate adapter instance.
   - For now, only "direct" is registered. "eodhd" and "ib" raise NotImplementedError.
5. Refactor `app/domain/services/render_payload_service.py`:
   - Instead of directly reading chart.inline_series, use `get_adapter(chart.source_kind)` to fetch series data.
   - Pass the adapter result through the existing normalization and indicator pipeline.
6. Verify existing tests still pass after refactor.

Output:
- All new and modified files.
- A short summary of what changed.
```

---

### Step S15 — Range Resolver

```text
[INSTRUCTIONS FOR THE CODE-GENERATION LLM]

Context:
- Project has: full API, provider adapter protocol, direct adapter. Provider-backed charts need date range resolution before fetching.

Task:
Build the range resolver utility.

Requirements:
1. Create `app/domain/services/range_resolver.py`:
   - `def resolve_range(range_config: dict) -> tuple[date, date]`:
     - If mode == "fixed": parse start_date and end_date as YYYY-MM-DD, validate start <= end, return as (date, date).
     - If mode == "relative": parse lookback string (e.g., "30d", "12m", "25y", "4w").
       - Supported units: d (days), w (weeks), m (months), y (years).
       - Anchor "now" means today's date.
       - Compute start_date = now - lookback, end_date = now.
       - Return as (date, date).
     - Raise ValueError for unsupported formats or invalid ranges.
2. Add unit tests in `tests/test_range_resolver.py`:
   - Test fixed range parsing.
   - Test relative range with each unit (d, w, m, y).
   - Test invalid lookback strings are rejected.
   - Test start_date > end_date is rejected.

Output:
- range_resolver.py and tests.
- A short summary of what changed.
```

---

### Step S16 — EODHD Adapter

```text
[INSTRUCTIONS FOR THE CODE-GENERATION LLM]

Context:
- Project has: full API, provider protocol, direct adapter, range resolver.
- EODHD_API_KEY and EODHD_TIMEOUT_MS are in Settings.

Task:
Implement the EODHD provider adapter for end-of-day historical data.

Requirements:
1. Create `app/providers/eodhd.py`:
   - `EodhdAdapter` implementing MarketDataAdapter.
   - `__init__`: accept api_key and timeout_ms from settings.
   - `fetch_series(request: ProviderRequest) -> ProviderSeriesResult`:
     - Build URL: `https://eodhd.com/api/eod/{symbol}?from={start}&to={end}&period=d&fmt=json&api_token={key}`.
     - Use httpx.AsyncClient with timeout.
     - Parse JSON response into canonical OHLCV bars (map EODHD field names to internal names).
     - Include warnings if returned data range is shorter than requested.
     - Handle HTTP errors: 4xx → raise with descriptive message, 5xx → raise as provider failure.
   - `healthcheck`:
     - Make a lightweight API call (e.g., exchange list) to verify connectivity.
2. Update `app/providers/registry.py`:
   - Register "eodhd" to return EodhdAdapter instance.
3. Update chart creation flow in `app/domain/services/chart_service.py`:
   - For provider-backed charts (source.kind != "direct"), perform a validation fetch during chart creation.
   - If validation fetch fails, reject with 422 including the provider error message.
   - Do not persist fetched market data for provider-backed charts.
4. Update render-payload builder to use range resolver for provider-backed charts before calling the adapter.
5. Add tests:
   - Unit test with mocked httpx responses for success and failure cases.
   - Test that provider-backed chart creation performs validation fetch.

Output:
- eodhd.py, updated registry.py, updated chart_service.py, updated render_payload_service.py.
- A short summary of what changed.
```

---

### Step S17 — IB Adapter: Connection & Fetch

```text
[INSTRUCTIONS FOR THE CODE-GENERATION LLM]

Context:
- Project has: full API, provider protocol, direct and EODHD adapters, range resolver.
- IB_HOST, IB_PORT, IB_CLIENT_ID, IB_TIMEOUT_MS are in Settings.
- ib_async is a dependency for connecting to IB Gateway.

Task:
Implement the IB provider adapter with connection lifecycle management.

Requirements:
1. Create `app/providers/ib.py`:
   - `IbAdapter` implementing MarketDataAdapter.
   - Connection manager:
     - Maintain a single persistent `ib_async.IB()` connection.
     - On init, connect to IB_HOST:IB_PORT with IB_CLIENT_ID.
     - Implement auto-reconnect with exponential backoff (1s, 2s, 4s, max 30s).
     - Use an asyncio.Lock to enforce single in-flight historical data request.
   - `fetch_series(request: ProviderRequest) -> ProviderSeriesResult`:
     - Build IB contract from provider_config (requires fields like secType, exchange, currency).
     - Call `ib.reqHistoricalDataAsync()` with resolved date range and bar size "1 day".
     - Respect IB pacing: enforce minimum 1-second gap between requests.
     - Normalize returned BarData into canonical OHLCV bars.
     - Handle timeout via IB_TIMEOUT_MS.
   - `healthcheck`:
     - Check if IB connection is active and return status.
   - Provide `async def connect()` and `async def disconnect()` lifecycle methods.
2. Add `ib_async` to project dependencies.
3. Do NOT wire into the provider registry yet (that's S18).

Output:
- ib.py with connection manager and fetch logic.
- A short summary of what changed.
```

---

### Step S18 — IB Adapter: Normalization & Wiring

```text
[INSTRUCTIONS FOR THE CODE-GENERATION LLM]

Context:
- Project has: IB adapter module with connection manager and fetch logic (S17), but it's not yet wired into the application.

Task:
Normalize IB bar data and wire the adapter into the chart service.

Requirements:
1. Update `app/providers/ib.py`:
   - Ensure IB BarData normalization produces canonical OHLCV dicts matching the internal format (time as YYYY-MM-DD string, float values for OHLCV fields).
   - Handle edge cases: partial data ranges, zero-volume bars, contract not found.
2. Update `app/providers/registry.py`:
   - Register "ib" to return IbAdapter instance.
   - IbAdapter should be initialized lazily (only when first needed) since IB Gateway may not always be available.
3. Update `app/main.py` lifespan:
   - On startup: if IB config is present, initialize IB adapter connection.
   - On shutdown: disconnect IB adapter.
4. Update chart creation validation:
   - For IB charts, validation fetch should verify the contract resolves and at least some data is available.
5. Add tests with mocked ib_async:
   - Test bar normalization with sample BarData objects.
   - Test connection failure handling.

Output:
- Updated ib.py, registry.py, main.py.
- A short summary of what changed.
```

---

### Step S19 — Browser Exporter Service

```text
[INSTRUCTIONS FOR THE CODE-GENERATION LLM]

Context:
- Project has: full API, all providers, frontend pages rendering charts at /charts/{id} and /embed/{id}.
- The frontend emits `document.body.dataset.chartReady = 'true'` when rendering completes.
- EXPORT_BROWSER_WS_ENDPOINT and EXPORT_TIMEOUT_MS are in Settings.
- No export functionality exists yet.

Task:
Build the browser exporter service that captures PNG screenshots via the headless browser sidecar.

Requirements:
1. Create `app/exports/__init__.py` (empty).
2. Create `app/exports/browser_exporter.py`:
   - `class BrowserExporter`:
     - `__init__(self, ws_endpoint: str, timeout_ms: int)`.
     - `async def capture_png(self, render_url: str, width: int, height: int) -> bytes`:
       - Connect to the browser sidecar via `playwright.async_api.async_playwright()`.
       - Use `browser.connect_over_cdp(ws_endpoint)`.
       - Create a new page with viewport set to width x height.
       - Navigate to render_url.
       - Wait for chart-ready signal: `page.wait_for_selector('body[data-chart-ready="true"]', timeout=timeout_ms)`.
       - Capture screenshot of `#chart-container` element as PNG bytes.
       - Close the page and return the bytes.
       - On timeout: raise an ExportTimeoutError.
       - On connection failure: raise an ExportConnectionError.
   - Define custom exceptions: ExportTimeoutError, ExportConnectionError.
3. The render_url should be an internal URL (e.g., `http://localhost:8000/charts/{id}?export=true`).
   - When `?export=true` is present, the chart page should hide non-chart chrome for a clean screenshot.
4. Update `app/web/static/charts.js` to check for `export=true` query parameter and hide chrome accordingly.
5. Add `playwright` to project dependencies (already listed but ensure it's importable).

Output:
- browser_exporter.py, updated charts.js.
- A short summary of what changed.
```

---

### Step S20 — Export API Route

```text
[INSTRUCTIONS FOR THE CODE-GENERATION LLM]

Context:
- Project has: browser exporter service that can capture PNGs via the sidecar.
- No export API route exists yet.
- PNG dimension bounds are configured in Settings.

Task:
Create the PNG export API endpoint.

Requirements:
1. Create `app/api/routes/exports.py`:
   - `GET /api/charts/{id}/png`:
     - Query params: width (int, required), height (int, required).
     - Validate chart exists (404 if not) and is not deleted (410).
     - Validate dimensions against configured bounds (PNG_MIN/MAX_WIDTH/HEIGHT). Return 422 if invalid.
     - Construct internal render URL for the chart.
     - Call BrowserExporter.capture_png().
     - Return Response with content_type="image/png", body=png_bytes.
     - Set `Cache-Control: no-store` header.
     - Update chart.last_exported_at timestamp.
   - Error handling:
     - ExportTimeoutError → 504 Gateway Timeout.
     - ExportConnectionError → 502 Bad Gateway (browser sidecar unreachable).
2. Wire the exports router into `app/main.py` under `/api`.
3. Add structured logging for export attempts (chart_id, width, height, duration_ms, success/failure).

Output:
- exports.py, updated main.py.
- A short summary of what changed.
```

---

### Step S21 — Dockerfile & Docker Compose

```text
[INSTRUCTIONS FOR THE CODE-GENERATION LLM]

Context:
- Project has: complete application with all API routes, providers, frontend pages, and PNG export.
- No containerization exists yet.

Task:
Create the Dockerfile and Docker Compose configuration for the full deployment topology.

Requirements:
1. Create `Dockerfile`:
   - Base: python:3.12-slim.
   - Install system deps (only what's needed — no Chromium).
   - Copy requirements and install Python deps.
   - Copy application code.
   - Expose port 8000.
   - CMD: uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8000.
   - Add non-root user for security.
2. Create `docker-compose.yml` with four services:
   - `app`: build from Dockerfile, env from .env, depends on postgres and browser, health check via /health.
   - `postgres`: postgres:16-alpine, persistent volume, pg_isready health check.
   - `browser`: browserless/chrome or zenika/alpine-chrome, internal CDP port, resource limits.
   - `proxy`: caddy:2-alpine, ports 80/443, volume for config, depends on app.
3. Create `Caddyfile` placeholder: reverse proxy to app:8000, auto TLS, gzip.
4. Create `.env.example` with all required variables for Docker Compose.

Output:
- Dockerfile, docker-compose.yml, Caddyfile, .env.example.
- A short summary of what was created.
```

---

### Step S22 — Reverse Proxy & Security Hardening

```text
[INSTRUCTIONS FOR THE CODE-GENERATION LLM]

Context:
- Project has: Docker Compose with app, postgres, browser, and proxy services.
- Caddy is the reverse proxy. Basic Caddyfile exists.

Task:
Configure the reverse proxy with rate limiting, request size limits, and security headers.

Requirements:
1. Update `Caddyfile`:
   - Rate limiting for expensive routes:
     - POST /api/charts: limit to 10 req/min per IP.
     - GET /api/charts/*/png: limit to 5 req/min per IP.
   - Request body size limit: 5 MB max.
   - Security headers: X-Content-Type-Options, X-Frame-Options (for non-embed routes), Strict-Transport-Security.
   - Static asset caching: Cache-Control headers for /static/* (1 day).
   - Forward real client IP via X-Forwarded-For / X-Real-IP.
   - Enable gzip and zstd compression.
2. Update `app/main.py`:
   - Add application-level request body size limit of 10 MB.
   - Add middleware to generate and propagate `request_id` (UUID v4 or from X-Request-ID header).
   - Ensure structured logs include request_id on all log entries.
3. Review error responses:
   - Ensure no stack traces or credential-bearing messages leak in production (APP_ENV == "production").
   - Sanitize error messages in ErrorResponse.

Output:
- Updated Caddyfile, updated main.py.
- A short summary of what changed.
```

---

### Step S23 — Smoke Tests & Documentation

```text
[INSTRUCTIONS FOR THE CODE-GENERATION LLM]

Context:
- Project is feature-complete: full API, providers, rendering, export, containerized deployment.
- Need end-to-end validation and documentation.

Task:
Add smoke tests and create project documentation.

Requirements:
1. Create `tests/test_smoke.py`:
   - End-to-end tests using httpx AsyncClient against the FastAPI app:
     a. Health check returns 200 with expected shape.
     b. Create a direct chart with sample candlestick + EMA data → verify 201 and response URLs.
     c. GET the created chart → verify 200 with normalized payload containing both price and EMA series.
     d. Update the chart title → verify updated_at changed.
     e. List charts → verify the chart appears.
     f. Delete the chart → verify 204, then GET returns 410, list excludes it.
   - (PNG export smoke test is optional here since it requires the browser sidecar.)
2. Create `README.md`:
   - Project description and purpose.
   - Quick start: prerequisites, clone, configure .env, docker-compose up.
   - API reference: brief table of all endpoints with methods, paths, and purpose.
   - Environment variables reference.
   - Architecture overview (4-service Docker Compose topology).
   - Development setup: local Python venv, running migrations, running tests.
   - Backup instructions: pg_dump cron example with retention policy.
3. Create `tests/conftest.py`:
   - Shared fixtures: test database URL, async client, sample chart data factories.
4. Verify all existing tests pass by listing the test command: `pytest -v`.

Output:
- test_smoke.py, conftest.py, README.md.
- A short summary of what was created.
```

---

*End of prompt pack. Steps S1–S23 cover the complete implementation from empty repository to deployable, hardened service.*
