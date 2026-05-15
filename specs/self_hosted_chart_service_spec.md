# Self-Hosted Chart Rendering Service Technical Specification

## Overview

This specification defines a self-hosted web service that accepts chart data and chart configuration, persists chart definitions, and renders financial charts using TradingView Lightweight Charts in hosted and embeddable web pages. The system is intended primarily as an internal tool, but the codebase and operational model must be production-quality and suitable for release as a deploy-it-yourself open source project.

The service must support two data acquisition modes: direct data submission and provider-backed retrieval. In direct mode, the caller sends data inline as JSON arrays or pandas-style records; in provider-backed mode, the caller submits a provider query definition and the service fetches latest data on demand from EODHD or Interactive Brokers via IB Gateway and `ib_async`.

The primary output of the system is a hosted chart URL and a stripped-down embeddable chart URL backed by a persisted chart definition keyed by a short opaque identifier. A synchronous PNG export endpoint must also be supported using caller-supplied width and height parameters and Playwright-based screenshot capture.

The system is intentionally narrow in scope for version 1. It is not a full charting workstation, multi-user SaaS, trading terminal, or streaming data platform. Version 1 focuses on durable chart definitions, on-demand data retrieval, deterministic indicator generation, responsive hosted rendering, and a simple deployment target consisting of a single VPS, Postgres, and a Python web service.

## Terminology

- **Chart definition**: The canonical high-level request body persisted as JSONB. This is the source of truth for what a chart is.
- **Normalized payload**: The backend-generated render contract consumed by the frontend renderer. This is an ephemeral, computed artifact derived from the chart definition and source data.
- **Inline data / direct data**: Market data submitted by the caller as part of the chart creation request and persisted with the chart definition.
- **Provider-backed data**: Market data fetched on demand from an external provider (EODHD or IB) at render time rather than persisted.
- **Series**: A single data stream within a chart, either raw input data (e.g., candlestick OHLCV) or a derived indicator (e.g., SMA line).
- **Pane**: A vertically stacked chart area. Version 1 implements single-pane rendering but the schema supports multiple panes for forward compatibility.
- **Chart ID**: A short, opaque, URL-safe, non-sequential identifier for a persisted chart.

## Goals and non-goals

### Goals

- Accept a high-level chart request over HTTP and persist it under a short non-sequential chart ID.
- Support direct input data using JSON arrays and pandas-style record objects.
- Support provider-backed retrieval from EODHD end-of-day history and IB historical bars through a modular adapter layer.
- Render charts in a hosted web page and an embeddable iframe-friendly page using TradingView Lightweight Charts.
- Regenerate provider-backed charts on demand using latest available data rather than persisting provider market data snapshots.
- Persist chart definitions indefinitely in Postgres using flexible JSONB-backed storage for semi-structured configuration payloads.
- Support server-side indicators in version 1: SMA, EMA, VWAP, and Bollinger Bands.
- Expose a synchronous PNG export endpoint using headless browser screenshots at caller-supplied dimensions.
- Provide responsive mobile-friendly viewing, with “good viewing on mobile” as the target rather than advanced mobile UX.
- Be deployable on a single VPS with structured logs and minimal operational complexity.
- Expose a health check endpoint for operational readiness monitoring.
- Support chart update and soft-delete for basic lifecycle management.
- Support paginated internal chart listing for operational use.

### Non-goals

- No application-level user accounts, tenant separation, billing, or quotas in version 1.
- No order placement, broker account data, positions, or live trading workflows.
- No streaming quotes, websockets, or real-time subscriptions in version 1.
- No chart layout persistence beyond the stored chart definition itself; there are no user workspaces or dashboards in version 1.
- No exchange calendar logic, premarket/after-hours session filtering, or market-hours semantics in version 1.
- No provider failover or multi-provider routing logic.
- No public search, discovery, or listing of charts. A private paginated listing endpoint is in scope for operational use.
- No caching strategy beyond optional short-lived normalized payload reuse inside the application process.

## System context

The system serves anonymous internet-accessible chart URLs and embed URLs while keeping all provider credentials server-side. Chart definitions are durable application records in Postgres and are identified by opaque, non-numeric, URL-safe IDs that are hard to guess but are not treated as secrets or authorization tokens.

The rendering engine is browser-based because TradingView Lightweight Charts is a client-side HTML5 canvas charting library designed to create chart instances and attach series data in the browser. The backend is responsible for input validation, provider integration, data normalization, indicator calculation, persistence, and image export orchestration.

## Functional requirements

### FR-1 Chart creation

The service shall expose an HTTP endpoint that accepts a chart creation request, validates it, persists the chart definition, and returns a chart ID plus absolute URLs for hosted viewing, embedding, and API retrieval.

The service shall support two chart source modes:

- `direct`: inline input data is included in the request and persisted with the chart definition.
- `provider`: the request includes provider configuration and range definition, and the service refetches latest data whenever the chart is rendered or exported.

### FR-2 Chart retrieval

The service shall expose an API endpoint that resolves a chart ID to its current normalized chart payload and metadata. If the chart is direct-backed, the service shall normalize persisted inline data into the frontend payload. If the chart is provider-backed, the service shall resolve the saved range and query the provider adapter for current data before generating the payload.

### FR-3 Hosted chart page

The service shall expose a human-viewable hosted chart page at `/charts/{id}` that loads the chart definition by ID and renders it in a minimal responsive page using TradingView Lightweight Charts. The hosted page may include only the simplest chrome required for context, such as title and optional legend, because the product direction favors simplicity over a feature-rich workstation interface.

### FR-4 Embed page

The service shall expose an iframe-oriented page at `/embed/{id}` that renders the same chart content with stripped-down page chrome suitable for embedding in other sites or internal tools. The embed page shall share the same backend resolution path as the hosted page and differ primarily in presentation.

### FR-5 PNG export

The service shall expose a synchronous PNG export endpoint for an existing chart ID using caller-supplied width and height parameters. The implementation shall render a chart page at the requested dimensions and capture a screenshot using Playwright’s screenshot API.

### FR-6 Indicator support

The backend shall compute the following indicators in version 1 when requested in the chart spec:

- Simple Moving Average (SMA)
- Exponential Moving Average (EMA)
- Volume Weighted Average Price (VWAP)
- Bollinger Bands

Indicator outputs shall be represented as derived series in the normalized payload so that hosted render, embed render, and PNG export remain consistent.

### FR-7 Range support

The chart specification shall support both fixed and rolling range semantics for provider-backed charts.

A fixed range shall specify explicit ISO dates:

```json
{
  "range": {
    "mode": "fixed",
    "start_date": "2000-01-01",
    "end_date": "2026-05-14"
  }
}
```

A rolling range shall specify a relative lookback ending at the current time:

```json
{
  "range": {
    "mode": "relative",
    "lookback": "25y",
    "anchor": "now"
  }
}
```

The service shall resolve both forms into provider-native query parameters at request time.

### FR-8 Time format handling

Caller-provided timestamps in version 1 shall be accepted as ISO date strings in `YYYY-MM-DD` format only. Datetime strings with time components shall be rejected. The normalization layer shall convert those values into the date representation expected by Lightweight Charts for daily-series data.

### FR-9 Multi-series and pane forward compatibility

The schema shall support multiple series from day one, and each series shall include a `pane` field. Version 1 runtime behavior may implement one-pane rendering first, but the contract must not prevent future expansion to multiple panes, since Lightweight Charts documents pane support as a first-class concept.

### FR-10 Chart update

The service shall expose an endpoint to update a chart definition for an existing chart ID. Updates may modify the title, view configuration, layout, series definitions, or inline data. The `updated_at` timestamp shall be set on every successful update.

### FR-11 Chart soft-delete

The service shall expose an endpoint to soft-delete a chart by setting a `deleted_at` timestamp. Soft-deleted charts shall not be returned by listing endpoints and shall return `410 Gone` on direct access via view, embed, API retrieval, or export endpoints.

### FR-12 Chart listing

The service shall expose a paginated listing endpoint for charts. The endpoint shall support cursor-based or offset pagination, ordering by `created_at` descending, and filtering by `source_kind`. Soft-deleted charts shall be excluded from listing results.

### FR-13 Health check

The service shall expose a `GET /health` endpoint that returns `200 OK` with a JSON body indicating application and database readiness. This endpoint shall be used by Docker Compose health checks and reverse proxy upstream monitoring.

### FR-14 Volume series

Volume data shall be preserved through normalization and included in the normalized payload. Version 1 shall render volume as a histogram series in a separate pane below the price chart. The volume histogram shall use the `Histogram` series type from Lightweight Charts. VWAP indicator computation depends on volume data being present in the source series.

## Non-functional requirements

### NFR-1 Maintainability

The codebase shall be organized as a modular Python application with separate concerns for API routing, domain models, provider adapters, data normalization, rendering translation, export logic, and persistence.

### NFR-2 Deployability

The system shall be deployable to a single VPS using Docker Compose with four services: application, Postgres, reverse proxy, and headless browser for PNG export.

### NFR-3 Performance

The system shall support direct chart rendering and API retrieval for approximately 25 years of daily data per series, which is on the order of several thousand bars and is practical for browser rendering and JSON transport when payload shape is kept compact. PNG export shall aim for synchronous behavior under normal load, subject to bounded dimensions and timeouts.

### NFR-4 Security

The service shall keep provider credentials entirely server-side and shall not embed credentials in chart URLs, frontend code, or public payloads. The service shall use opaque non-sequential IDs and request-size/rate controls, but chart URLs are not considered authenticated resources in version 1.

### NFR-5 Observability

The service shall emit structured JSON logs sufficient for operational troubleshooting. No metrics or tracing stack is required in version 1.

### NFR-6 CORS and embedding policy

The embed page at `/embed/{id}` shall set `Content-Security-Policy: frame-ancestors *` to allow cross-origin iframe embedding. API routes under `/api/` shall set `Access-Control-Allow-Origin: *` to permit cross-origin API consumption. The hosted chart page at `/charts/{id}` may use default same-origin framing policy.

## Architecture

### High-level architecture

The system consists of the following major components:

1. FastAPI HTTP application for API routes, page routes, and static asset delivery.
2. Postgres database for durable chart definitions and related metadata.
3. Provider adapter layer for direct input, EODHD, and IB historical bars.
4. Normalization and indicator engine that converts source data into a canonical internal representation.
5. Frontend renderer pages built around TradingView Lightweight Charts.
6. Headless browser sidecar for PNG export via Chrome DevTools Protocol.
7. Reverse proxy (Caddy recommended for automatic TLS, or Nginx) for TLS termination, compression, and rate limiting.

### Request flow: chart creation

1. Client sends `POST /api/charts` with a high-level chart definition.
2. Backend validates the payload using Pydantic models.
3. For provider-backed charts, backend performs a validation fetch to confirm the provider can resolve the symbol and range. If the validation fetch fails, the request is rejected with a `422` error describing the provider failure.
4. Backend generates a short opaque chart ID.
5. Backend persists the canonical chart definition in Postgres JSONB columns.
6. Backend returns chart URLs and metadata.

### Request flow: chart view or embed

1. Browser requests `/charts/{id}` or `/embed/{id}`.
2. Backend resolves the chart definition from Postgres by ID.
3. Backend either uses inline data or calls the relevant provider adapter for latest source data.
4. Backend normalizes data, computes derived indicator series, and produces a normalized chart payload.
5. Frontend page loads the payload and renders the chart with TradingView Lightweight Charts.

### Request flow: PNG export

1. Client requests `/api/charts/{id}/png?width=...&height=...`.
2. Backend validates chart existence and dimensions.
3. Backend constructs an internal render URL for the chart in export mode.
4. Backend connects to the headless browser sidecar via `EXPORT_BROWSER_WS_ENDPOINT` using Playwright's `connect_over_cdp` and loads the render URL.
5. The browser waits for the chart-ready signal (see FR-5 and Frontend Rendering Contract).
6. The browser captures a screenshot of the chart container and returns `image/png` synchronously to the caller.

## Technology choices

### Backend

- Python 3.12 or current supported Python 3.x LTS runtime
- FastAPI for HTTP APIs and page serving.
- Pydantic v2 for schema validation and serialization.
- SQLAlchemy 2.x async stack with `asyncpg` for Postgres access.
- Alembic for schema migrations.

### Database

- PostgreSQL as the primary and only database in version 1.
- JSONB columns for chart definitions and flexible metadata.

### Frontend

- Minimal HTML/CSS/JavaScript frontend served as static assets by the application or reverse proxy.
- TradingView Lightweight Charts v4.x (`lightweight-charts@^4.0`) as the rendering library. Version 4 is required for forward-compatible multi-pane support.

### Export

- A headless Chromium browser running as a Docker Compose sidecar service (e.g., `browserless/chrome` or `chromium` image) exposing a Chrome DevTools Protocol (CDP) websocket endpoint.
- Playwright Python as the client library to connect to the remote browser via `EXPORT_BROWSER_WS_ENDPOINT`. The application container does not install Chromium locally.
- This architecture keeps the application container lightweight (~200 MB vs ~1.2 GB with bundled Chromium) and isolates browser resource consumption.

### Provider libraries

- Standard HTTP client for EODHD requests against end-of-day historical endpoints.
- `ib_async` for Interactive Brokers historical data access via remote IB Gateway.

## Domain model

### Core entities

#### Chart

A persisted chart definition addressed by a short opaque ID.

Fields:
- `id: str`
- `created_at: datetime`
- `updated_at: datetime`
- `deleted_at: Optional[datetime]`
- `source_kind: str`
- `title: Optional[str]`
- `chart_definition: dict`
- `inline_series: Optional[dict]`
- `last_rendered_at: Optional[datetime]`
- `last_exported_at: Optional[datetime]`

Notes:
- `normalized_payload` is not persisted. It is an ephemeral computed artifact derived from the chart definition and source data at request time. Caching, if needed in future, should use a separate cache layer rather than the source-of-truth table.
- Instrument metadata (symbol, asset class, label) is stored within `chart_definition.instrument` and is not promoted to a separate column. The GIN index on `chart_definition` supports instrument-based queries.

#### ChartDefinition

The canonical high-level request body persisted as JSONB.

Substructures:
- `source`
- `instrument`
- `range`
- `view`
- `layout`
- `series`
- `annotations` (reserved for future use)

#### NormalizedChartPayload

The backend-generated render contract consumed by the frontend renderer.

Substructures:
- `meta`
- `layout_options`
- `series`
- `legend_config`
- `render_hints`

## Database schema

### Table: `charts`

Recommended DDL outline:

```sql
create table charts (
  id text primary key,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  deleted_at timestamptz null,
  source_kind text not null check (source_kind in ('direct', 'eodhd', 'ib')),
  title text null,
  chart_definition jsonb not null,
  inline_series jsonb null,
  last_rendered_at timestamptz null,
  last_exported_at timestamptz null
);
```

Recommended indexes:

```sql
create index idx_charts_created_at on charts (created_at desc);
create index idx_charts_source_kind on charts (source_kind);
create index idx_charts_chart_definition_gin on charts using gin (chart_definition);
create index idx_charts_deleted_at on charts (deleted_at) where deleted_at is null;
```

PostgreSQL JSONB is appropriate here because the chart definition is semistructured, likely to evolve, and benefits from native JSON operators and indexing.

### JSONB schema versioning

The `chart_definition` JSONB payload shall include a top-level `schema_version` field (integer, starting at `1`). Schema changes to the chart definition structure shall follow an additive-only policy in version 1 — new fields may be added with defaults, but existing fields shall not be renamed or removed. If a breaking change is required in a future version, the application shall include a migration function that upgrades old definitions on read.

### Persistence policy

- Charts live forever unless soft-deleted via the delete endpoint.
- Soft-deleted charts retain their data in the database but are excluded from listing and return `410 Gone` on direct access.
- Direct charts persist inline data in `inline_series`.
- Provider-backed charts do not persist fetched market data by default.
- The normalized payload is not persisted. It is computed on demand from the chart definition and source data.

## ID generation

Chart IDs shall be short, opaque, URL-safe, and non-sequential. The implementation may use a Nano ID-inspired alphabet and entropy model even if the exact implementation is in Python rather than JavaScript.

Requirements:
- Minimum entropy sufficient to avoid practical guessing through enumeration.
- URL-safe alphabet.
- No numeric autoincrement IDs exposed publicly.
- Stable length for consistent URL appearance.

Recommended default: 16 to 21 URL-safe characters.

## API specification

### Content types

All API request bodies shall use `Content-Type: application/json`. API responses shall use `Content-Type: application/json` unless otherwise noted. PNG export responses shall use `Content-Type: image/png`. Hosted and embed page responses shall use `Content-Type: text/html`.

### Inline data limits

Direct chart creation requests shall be limited to a maximum of 50,000 data points per series and a maximum request body size of 10 MB at the application level. The reverse proxy should enforce a lower body size limit (e.g., 5 MB) as a first line of defense.

### 1. Create chart

**Route**: `POST /api/charts`

**Purpose**: Persist a chart definition and return stable URLs.

**Request body**:

```json
{
  "source": {
    "kind": "direct",
    "provider": null,
    "provider_config": null
  },
  "instrument": {
    "symbol": "SPY",
    "asset_class": "equity",
    "label": "SPDR S&P 500 ETF"
  },
  "range": {
    "mode": "fixed",
    "start_date": "2000-01-01",
    "end_date": "2026-05-14"
  },
  "view": {
    "title": "SPY Daily",
    "theme": "dark",
    "mobile_responsive": true
  },
  "layout": {
    "pane_mode": "single",
    "legend": true,
    "autosize": true
  },
  "series": [
    {
      "id": "price",
      "type": "candlestick",
      "pane": 0,
      "data_format": "ohlcv",
      "data": [
        { "time": "2026-05-01", "open": 560.12, "high": 564.2, "low": 558.1, "close": 563.85, "volume": 72830000 }
      ]
    },
    {
      "id": "ema20",
      "type": "line",
      "pane": 0,
      "indicator": {
        "name": "ema",
        "length": 20,
        "source_series": "price"
      }
    }
  ]
}
```

**Response**:

```json
{
  "id": "p9VdX7qQk2RtA1mB",
  "view_url": "https://charts.example.com/charts/p9VdX7qQk2RtA1mB",
  "embed_url": "https://charts.example.com/embed/p9VdX7qQk2RtA1mB",
  "api_url": "https://charts.example.com/api/charts/p9VdX7qQk2RtA1mB"
}
```

Validation rules:
- `source.kind` must be one of `direct`, `eodhd`, `ib`.
- Direct charts must include inline data for at least one non-derived series.
- Provider charts must not include inline market data as authoritative source data.
- Dates must be ISO date strings in `YYYY-MM-DD` format.
- Width and height are not supplied at creation time because export dimensions are caller-specified per export request.
- Maximum 50,000 data points per series for inline data.

### 2. Get chart payload

**Route**: `GET /api/charts/{id}`

**Purpose**: Return resolved chart metadata and normalized payload.

**Response shape**:

```json
{
  "id": "p9VdX7qQk2RtA1mB",
  "title": "SPY Daily",
  "source_kind": "direct",
  "instrument": {
    "symbol": "SPY",
    "asset_class": "equity",
    "label": "SPDR S&P 500 ETF"
  },
  "payload": {
    "meta": {
      "timezone": "UTC",
      "theme": "dark"
    },
    "layout_options": {},
    "series": []
  }
}
```

If the chart is provider-backed, the service shall fetch latest source data before returning the payload.

### 3. Hosted chart page

**Route**: `GET /charts/{id}`

**Purpose**: Render a minimal full page chart.

Requirements:
- Responsive layout.
- Minimal wrapper UI.
- SEO is not required.
- Page shall fetch the resolved payload from `/api/charts/{id}` or receive it server-side.
- Page shall emit a "chart ready" signal for export workflows.

Error states:
- `404`: Chart not found — display a minimal "chart not found" page.
- Provider fetch failure — display a minimal error message in place of the chart.
- Empty data — display the chart chrome with a "no data available" message.

### 4. Embed chart page

**Route**: `GET /embed/{id}`

**Purpose**: Render a minimal iframe-safe chart view.

Requirements:
- Same chart rendering logic as hosted page.
- Reduced chrome and margins.
- Stable height behavior and responsive width.
- No interactive toolbar beyond what is easiest to implement.

### 5. PNG export

**Route**: `GET /api/charts/{id}/png?width={w}&height={h}`

**Purpose**: Return a PNG image of the chart at requested dimensions.

Validation:
- Width and height required.
- Width and height must be integers.
- Width and height must fall within configured safe bounds to prevent abuse.

Recommended bounds:
- minimum width: 320
- minimum height: 200
- maximum width: 2400
- maximum height: 1600

Error behavior:
- `404` if chart not found.
- `422` if dimensions invalid.
- `504` or `500` if export times out or rendering fails.

The response shall include `Cache-Control: no-store` to prevent stale PNG caching for provider-backed charts.

### 6. List charts

**Route**: `GET /api/charts?page=1&limit=20&source_kind=direct`

**Purpose**: Return a paginated list of charts for operational use.

**Response shape**:

```json
{
  "charts": [
    {
      "id": "p9VdX7qQk2RtA1mB",
      "title": "SPY Daily",
      "source_kind": "direct",
      "created_at": "2026-05-14T12:00:00Z",
      "updated_at": "2026-05-14T12:00:00Z"
    }
  ],
  "total": 42,
  "page": 1,
  "limit": 20
}
```

Rules:
- Default page size: 20, maximum page size: 100.
- Soft-deleted charts are excluded.
- Results ordered by `created_at` descending.
- Optional `source_kind` filter.

### 7. Update chart

**Route**: `PUT /api/charts/{id}`

**Purpose**: Replace the chart definition for an existing chart.

**Request body**: Same shape as the create endpoint.

**Response**: Same shape as the create endpoint, with updated URLs.

Rules:
- `source_kind` may not be changed (e.g., a direct chart cannot be converted to a provider chart).
- `updated_at` is set to current time on success.
- Returns `404` if the chart does not exist or is soft-deleted.

### 8. Delete chart

**Route**: `DELETE /api/charts/{id}`

**Purpose**: Soft-delete a chart.

**Response**: `204 No Content` on success.

Rules:
- Sets `deleted_at` to current time.
- Returns `404` if the chart does not exist.
- Returns `410 Gone` if the chart is already deleted.

### 9. Health check

**Route**: `GET /health`

**Purpose**: Report application and database readiness.

**Response**:

```json
{
  "status": "ok",
  "database": "connected",
  "version": "1.0.0"
}
```

Returns `200 OK` when healthy, `503 Service Unavailable` when the database is unreachable.

## Input schema details

### Source model

```json
{
  "source": {
    "kind": "direct | eodhd | ib",
    "provider": "optional explicit provider name",
    "provider_config": {}
  }
}
```

Rules:
- `direct` uses inline data and ignores provider config.
- `eodhd` requires provider identifiers and date resolution fields appropriate to EOD historical retrieval.
- `ib` requires provider config sufficient to resolve the contract externally and request historical bars through `ib_async`.

### Range model

#### Fixed range

```json
{
  "range": {
    "mode": "fixed",
    "start_date": "YYYY-MM-DD",
    "end_date": "YYYY-MM-DD"
  }
}
```

#### Relative range

```json
{
  "range": {
    "mode": "relative",
    "lookback": "25y",
    "anchor": "now"
  }
}
```

Rules:
- Both range modes are supported for provider-backed charts.
- Direct charts may include range for metadata, but inline data remains authoritative.
- `lookback` must parse into a supported relative duration unit such as `d`, `w`, `m`, or `y`.

### Instrument model

```json
{
  "instrument": {
    "symbol": "string",
    "asset_class": "equity | forex | futures | crypto | index",
    "label": "optional display name"
  }
}
```

Rules:
- The system stores the symbol as provided in the chart config.
- For provider-backed charts, the provider adapter is responsible for interpreting the symbol according to provider rules.

### View model

```json
{
  "view": {
    "title": "optional string",
    "theme": "light | dark",
    "mobile_responsive": true,
    "timezone": "UTC",
    "locale": "en-GB"
  }
}
```

### Layout model

```json
{
  "layout": {
    "pane_mode": "single | multi",
    "legend": true,
    "autosize": true
  }
}
```

Rules:
- Runtime may implement only `single` in version 1 while still accepting a pane index field per series.

### Series model

Each series entry may represent raw input data or a derived indicator series. The series `type` field uses the same vocabulary in both input and output schemas.

Valid `type` values: `candlestick`, `line`, `area`, `histogram`, `bar`.

Valid `data_format` values: `ohlcv` (open/high/low/close/volume), `ohlc` (no volume), `value` (single numeric value per timestamp).

Raw series example:

```json
{
  "id": "price",
  "type": "candlestick",
  "pane": 0,
  "data_format": "ohlcv",
  "data": [
    { "time": "2026-05-01", "open": 100, "high": 105, "low": 99, "close": 103, "volume": 1000000 }
  ]
}
```

Derived series example:

```json
{
  "id": "bb_upper",
  "type": "line",
  "pane": 0,
  "indicator": {
    "name": "bollinger",
    "length": 20,
    "stddev": 2,
    "source_series": "price",
    "band": "upper"
  }
}
```

Required fields:
- `id`
- `type`
- `pane`

Optional fields depending on role:
- `data_format`
- `data`
- `indicator`
- `style`
- `label`

### Series style model

The optional `style` field controls visual presentation of a series. All fields are optional and fall back to Lightweight Charts defaults when omitted.

```json
{
  "style": {
    "color": "#2962FF",
    "line_width": 2,
    "opacity": 1.0,
    "up_color": "#26a69a",
    "down_color": "#ef5350"
  }
}
```

Rules:
- `color` applies to line and area series.
- `up_color` and `down_color` apply to candlestick and bar series.
- `line_width` applies to line series (integer, 1-4).
- `opacity` applies to all series types (float, 0.0-1.0).

## Normalized internal data model

The backend shall normalize all source data into canonical internal bar/value records before rendering translation.

### Canonical OHLCV bar

```json
{
  "time": "2026-05-01",
  "open": 100.0,
  "high": 105.0,
  "low": 99.0,
  "close": 103.0,
  "volume": 1000000.0
}
```

### Canonical value point

```json
{
  "time": "2026-05-01",
  "value": 103.0
}
```

Normalization rules:
- Sort all rows by ascending date before indicator computation and frontend serialization.
- Reject duplicate dates within a series unless a future override policy is introduced.
- Coerce numeric fields to floats/ints as appropriate.
- Preserve input symbol metadata separately from time-series rows.

## Frontend rendering contract

The frontend should consume a compact normalized payload that maps directly onto Lightweight Charts’ series model.

Recommended shape:

```json
{
  "meta": {
    "title": "SPY Daily",
    "theme": "dark",
    "timezone": "UTC"
  },
  "layout_options": {
    "autosize": true
  },
  "series": [
    {
      "id": "price",
      "type": "candlestick",
      "pane": 0,
      "data": [
        { "time": "2026-05-01", "open": 100, "high": 105, "low": 99, "close": 103 }
      ]
    },
    {
      "id": "sma20",
      "type": "line",
      "pane": 0,
      "data": [
        { "time": "2026-05-01", "value": 101.4 }
      ]
    }
  ]
}
```

Frontend responsibilities:
- Create chart instance.
- Apply theme and layout options.
- Add series by type.
- Set series data.
- Resize responsively.
- Emit a chart-ready signal when first render completes for export coordination.

### Chart-ready signal contract

The frontend renderer shall signal rendering completion by setting the `data-chart-ready` attribute on the `<body>` element to `"true"`:

```javascript
document.body.dataset.chartReady = 'true';
```

The export service shall wait for this attribute before capturing the screenshot. The recommended polling strategy is `page.wait_for_selector('body[data-chart-ready="true"]')` with a configurable timeout (default: `EXPORT_TIMEOUT_MS`).

## Indicator engine requirements

### SMA

Compute rolling simple average over the configured source series close or value field.

### EMA

Compute exponential moving average over the configured source series close or value field.

### VWAP

Compute volume-weighted average price for OHLCV-capable source series. The default implementation shall use cumulative VWAP over the returned dataset in version 1 unless a session-reset policy is added later.

### Bollinger Bands

Compute middle band, upper band, and lower band from the configured source series with adjustable period and standard deviation multiplier.

Indicator requirements:
- Derived series must inherit timestamps from the source series after warm-up periods.
- Missing early values may be omitted or represented as gaps; the policy must be consistent across indicators.
- Indicators shall be computed server-side in version 1 so all render targets receive identical results.

## Provider adapter specification

### Common adapter interface

Each provider adapter shall implement a common interface conceptually equivalent to:

```python
class MarketDataAdapter(Protocol):
    async def fetch_series(self, request: ProviderRequest) -> ProviderSeriesResult: ...
    async def healthcheck(self) -> ProviderHealth: ...
```

### Direct adapter

Purpose:
- Validate inline input rows.
- Normalize data into canonical internal representation.
- Persist inline series for future regeneration.

### EODHD adapter

Scope:
- End-of-day historical data only in version 1.

Requirements:
- Accept symbol and resolved date range.
- Call the EOD historical endpoint using server-side credentials.
- Normalize returned rows into canonical OHLCV or value series.
- Never expose the provider token to clients.

### IB adapter

Scope:
- Historical bars only in version 1 via remote IB Gateway using `ib_async`.

Requirements:
- Accept already-resolved contract information or equivalent provider config sufficient for retrieval.
- Respect historical data pacing and request-size limits documented by Interactive Brokers.
- Enforce guardrails on range size and repeated requests.
- Normalize returned bars into canonical series.

Connection lifecycle:
- The application shall maintain a single persistent `ib_async` connection to the configured IB Gateway.
- If the connection drops, the adapter shall attempt automatic reconnection with exponential backoff.
- Only one historical data request shall be in-flight at a time per client ID, in accordance with IB Gateway limits.
- The `IB_CLIENT_ID` environment variable must be unique per application instance to avoid conflicts when multiple instances connect to the same gateway.

### Provider policies

The following policies apply to all provider adapters:

**Timeouts**: Each provider fetch shall be subject to a configurable timeout (`EODHD_TIMEOUT_MS`, `IB_TIMEOUT_MS`). Default: 30,000 ms.

**Retries**: Version 1 shall not retry failed provider requests. All provider failures are immediately surfaced to the caller as `502 Bad Gateway`.

**Partial data**: If a provider returns data for a shorter range than requested (e.g., ticker listed after the requested start date), the chart shall render the available data as-is. The API response may include a `warnings` array noting the discrepancy.

## Error handling

The API shall use JSON error responses for API routes and simple human-readable fallback text or minimal error pages for hosted/embed routes.

Recommended error categories:
- `400 Bad Request`: malformed input body.
- `404 Not Found`: unknown chart ID.
- `409 Conflict`: duplicate conflicting series IDs within a chart definition.
- `410 Gone`: chart has been soft-deleted.
- `422 Unprocessable Entity`: semantic validation failure such as invalid range, missing inline data, unsupported indicator config, or provider validation failure at chart creation.
- `502 Bad Gateway`: provider failure from EODHD or IB Gateway.
- `504 Gateway Timeout`: export or provider request timeout.

Error response shape:

```json
{
  "error": {
    "code": "invalid_range",
    "message": "Relative lookback must use a supported duration format such as 30d, 12m, or 25y."
  }
}
```

## Security requirements

The service is anonymously readable, but it still requires baseline hardening because provider-backed charts can trigger upstream data requests.

Required controls:
- Provider credentials stored only in server environment configuration.
- Request body size limits at reverse proxy and application level.
- Export dimension limits to prevent oversized screenshot abuse.
- Basic IP-based rate limiting at the reverse proxy for chart creation and export endpoints.
- Strict input validation for chart creation payloads.
- No stack traces or credential-bearing error messages in public responses.

The chart ID is an identifier, not an authentication boundary. Any possession of a valid URL implies read access in version 1.

## Logging and observability

Structured JSON logs shall be emitted for:
- incoming requests
- chart creation
- chart resolution
- provider fetches
- export attempts
- error conditions
- duration measurements for provider fetch, normalization, render, and export stages.

Suggested log fields:
- `timestamp`
- `level`
- `request_id` — generated as a UUID v4 per incoming request, or extracted from an `X-Request-ID` header if provided by the caller or reverse proxy.
- `route`
- `chart_id`
- `source_kind`
- `provider`
- `duration_ms`
- `status_code`
- `error_code`

## Deployment specification

### Target topology

Single VPS deployment with Docker Compose.

Services:
- `app` — Python application container (~200 MB, no Chromium)
- `postgres` — PostgreSQL database
- `proxy` — Caddy (recommended) or Nginx reverse proxy
- `browser` — headless Chromium sidecar (e.g., `browserless/chrome` or `zenika/alpine-chrome`) for PNG export via CDP websocket

### Reverse proxy responsibilities

- TLS termination.
- Gzip or Brotli compression.
- Rate limiting for expensive routes.
- Static asset caching headers where appropriate.
- Forwarding real client IP information to the app.

### Environment variables

Required application configuration:
- `DATABASE_URL` — format: `postgresql+asyncpg://user:pass@host:port/dbname`
- `BASE_URL` — public base URL for generating chart URLs (e.g., `https://charts.example.com`)
- `APP_ENV` — one of `development`, `staging`, `production`
- `LOG_LEVEL` — one of `DEBUG`, `INFO`, `WARNING`, `ERROR`
- `EODHD_API_KEY`
- `EODHD_TIMEOUT_MS` — default: `30000`
- `IB_HOST`
- `IB_PORT`
- `IB_CLIENT_ID`
- `IB_TIMEOUT_MS` — default: `30000`
- `EXPORT_BROWSER_WS_ENDPOINT` — CDP websocket URL of the browser sidecar (e.g., `ws://browser:3000`)
- `EXPORT_TIMEOUT_MS` — default: `15000`
- `PNG_MIN_WIDTH` — default: `320`
- `PNG_MIN_HEIGHT` — default: `200`
- `PNG_MAX_WIDTH` — default: `2400`
- `PNG_MAX_HEIGHT` — default: `1600`
- `DB_POOL_SIZE` — default: `5`
- `DB_MAX_OVERFLOW` — default: `10`

### Backup and recovery

Because charts live forever (unless soft-deleted), database backups are required operationally even in version 1. Recommended setup:
- A cron job running `pg_dump --format=custom` daily to a local volume or S3-compatible object store.
- Retention policy: 7 daily backups + 4 weekly backups.
- Backup verification: periodic restore to a temporary database to confirm backup integrity.

## Suggested project structure

```text
app/
  api/
    routes/
      charts.py
      pages.py
      exports.py
    dependencies.py
    errors.py
  core/
    config.py
    logging.py
    ids.py
  db/
    models.py
    session.py
    migrations/
  domain/
    schemas/
      chart_request.py
      chart_response.py
      normalized_payload.py
    services/
      chart_service.py
      normalization_service.py
      indicator_service.py
      render_payload_service.py
  providers/
    base.py
    direct.py
    eodhd.py
    ib.py
  exports/
    browser_exporter.py
  web/
    static/
      charts.js
      charts.css
    templates/
      chart.html
      embed.html
  main.py
```

## Implementation phases

### Phase 1: Foundation

- Set up FastAPI app, config, logging, database session management, and migrations.
- Create `charts` table with soft-delete support.
- Implement opaque ID generation.
- Implement `POST /api/charts`, `GET /api/charts/{id}`, `PUT /api/charts/{id}`, `DELETE /api/charts/{id}`, and `GET /api/charts` (listing) for direct charts only.
- Implement `GET /health` endpoint.

### Phase 2: Frontend rendering

- Build minimal hosted page and embed page.
- Implement normalized payload rendering with Lightweight Charts.
- Add responsive layout and chart-ready signal.

### Phase 3: Indicators

- Implement SMA, EMA, VWAP, and Bollinger calculations.
- Add derived-series materialization to payload builder.

### Phase 4: EODHD provider

- Implement provider adapter and range resolution for fixed and relative modes.
- Add provider-backed chart creation and retrieval.

### Phase 5: IB provider

- Implement historical bar adapter using `ib_async`.
- Add request guardrails and pacing-aware limits.

### Phase 6: PNG export

- Configure headless browser sidecar in Docker Compose.
- Build browser exporter connecting to sidecar via CDP websocket.
- Implement chart-ready signal contract.
- Validate width/height bounds and timeout handling.

### Phase 7: Hardening

- Add proxy rate limits, request size limits, and operational docs.
- Add basic smoke tests for chart create/view/export flows.

## Acceptance criteria

The implementation shall be considered complete for version 1 when all of the following are true:

1. A direct-data chart can be created, updated, soft-deleted, listed, stored in Postgres, retrieved by opaque chart ID, and rendered in both hosted and embed pages.
2. A provider-backed EODHD chart can be created with fixed or relative range semantics and renders using latest fetched data.
3. A provider-backed IB historical chart can be created and rendered against a remote IB Gateway through `ib_async`, with documented limitations and guardrails.
4. Requested indicators SMA, EMA, VWAP, and Bollinger are computed server-side and displayed correctly as derived series.
5. `GET /api/charts/{id}/png` returns a PNG image synchronously for valid dimensions under normal operating conditions, using the headless browser sidecar.
6. The application deploys successfully on a single VPS with Docker Compose, Postgres, reverse proxy, and headless browser sidecar.
7. The service exposes no provider credentials to clients and emits structured JSON logs for core operations.
8. `GET /health` returns application and database readiness status.
9. Volume data is preserved and rendered as a histogram series.

## Open implementation notes

The specification intentionally leaves some engineering choices to the implementation team while constraining behavior and interfaces sufficiently to avoid ambiguity. Acceptable implementation-level decisions include whether frontend payloads are fetched client-side or server-rendered into the HTML, and whether the application uses server-side templates or static HTML plus JSON API for the page shell.

The implementation team should favor the simplest solution that preserves the public contract, because the product's value in version 1 comes from a stable chart definition model, reliable provider abstraction, and a minimal deployable system rather than UI sophistication.
