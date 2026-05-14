# Self-Hosted Chart Rendering Service Technical Specification

## Overview

This specification defines a self-hosted web service that accepts chart data and chart configuration, persists chart definitions, and renders financial charts using TradingView Lightweight Charts in hosted and embeddable web pages.[cite:4][cite:44] The system is intended primarily as an internal tool, but the codebase and operational model must be production-quality and suitable for release as a deploy-it-yourself open source project.[cite:39][cite:44]

The service must support two data acquisition modes: direct data submission and provider-backed retrieval.[cite:26][cite:37] In direct mode, the caller sends data inline as JSON arrays or pandas-style records; in provider-backed mode, the caller submits a provider query definition and the service fetches latest data on demand from EODHD or Interactive Brokers via IB Gateway and `ib_async`.[cite:26][cite:37][cite:7]

The primary output of the system is a hosted chart URL and a stripped-down embeddable chart URL backed by a persisted chart definition keyed by a short opaque identifier.[cite:49][cite:55] A synchronous PNG export endpoint must also be supported using caller-supplied width and height parameters and Playwright-based screenshot capture.[cite:28][cite:30]

The system is intentionally narrow in scope for version 1. It is not a full charting workstation, multi-user SaaS, trading terminal, or streaming data platform.[cite:4][cite:37] Version 1 focuses on durable chart definitions, on-demand data retrieval, deterministic indicator generation, responsive hosted rendering, and a simple deployment target consisting of a single VPS, Postgres, and a Python web service.[cite:39][cite:44]

## Goals and non-goals

### Goals

- Accept a high-level chart request over HTTP and persist it under a short non-sequential chart ID.[cite:49][cite:55]
- Support direct input data using JSON arrays and pandas-style record objects.[cite:4]
- Support provider-backed retrieval from EODHD end-of-day history and IB historical bars through a modular adapter layer.[cite:26][cite:37][cite:7]
- Render charts in a hosted web page and an embeddable iframe-friendly page using TradingView Lightweight Charts.[cite:4]
- Regenerate provider-backed charts on demand using latest available data rather than persisting provider market data snapshots.[cite:26][cite:37]
- Persist chart definitions indefinitely in Postgres using flexible JSONB-backed storage for semi-structured configuration payloads.[cite:44][cite:43]
- Support server-side indicators in version 1: SMA, EMA, VWAP, and Bollinger Bands.[cite:4]
- Expose a synchronous PNG export endpoint using Playwright screenshots at caller-supplied dimensions.[cite:28][cite:30]
- Provide responsive mobile-friendly viewing, with “good viewing on mobile” as the target rather than advanced mobile UX.[cite:4]
- Be deployable on a single VPS with structured logs and minimal operational complexity.[cite:39][cite:44]

### Non-goals

- No application-level user accounts, tenant separation, billing, or quotas in version 1.[cite:39]
- No order placement, broker account data, positions, or live trading workflows.[cite:37]
- No streaming quotes, websockets, or real-time subscriptions in version 1.[cite:37]
- No chart layout persistence beyond the stored chart definition itself; there are no user workspaces or dashboards in version 1.[cite:44]
- No exchange calendar logic, premarket/after-hours session filtering, or market-hours semantics in version 1.[cite:37]
- No provider failover or multi-provider routing logic.[cite:26][cite:37]
- No public search, discovery, or listing of charts.[cite:49]
- No caching strategy beyond optional short-lived normalized payload reuse inside the application process.[cite:44]

## System context

The system serves anonymous internet-accessible chart URLs and embed URLs while keeping all provider credentials server-side.[cite:26][cite:37] Chart definitions are durable application records in Postgres and are identified by opaque, non-numeric, URL-safe IDs that are hard to guess but are not treated as secrets or authorization tokens.[cite:44][cite:49][cite:55]

The rendering engine is browser-based because TradingView Lightweight Charts is a client-side HTML5 canvas charting library designed to create chart instances and attach series data in the browser.[cite:4] The backend is responsible for input validation, provider integration, data normalization, indicator calculation, persistence, and image export orchestration.[cite:39][cite:44][cite:28]

## Functional requirements

### FR-1 Chart creation

The service shall expose an HTTP endpoint that accepts a chart creation request, validates it, persists the chart definition, and returns a chart ID plus absolute URLs for hosted viewing, embedding, and API retrieval.[cite:39][cite:44]

The service shall support two chart source modes:

- `direct`: inline input data is included in the request and persisted with the chart definition.[cite:4]
- `provider`: the request includes provider configuration and range definition, and the service refetches latest data whenever the chart is rendered or exported.[cite:26][cite:37]

### FR-2 Chart retrieval

The service shall expose an API endpoint that resolves a chart ID to its current normalized chart payload and metadata.[cite:44] If the chart is direct-backed, the service shall normalize persisted inline data into the frontend payload.[cite:4] If the chart is provider-backed, the service shall resolve the saved range and query the provider adapter for current data before generating the payload.[cite:26][cite:37]

### FR-3 Hosted chart page

The service shall expose a human-viewable hosted chart page at `/charts/{id}` that loads the chart definition by ID and renders it in a minimal responsive page using TradingView Lightweight Charts.[cite:4] The hosted page may include only the simplest chrome required for context, such as title and optional legend, because the product direction favors simplicity over a feature-rich workstation interface.[cite:4]

### FR-4 Embed page

The service shall expose an iframe-oriented page at `/embed/{id}` that renders the same chart content with stripped-down page chrome suitable for embedding in other sites or internal tools.[cite:4] The embed page shall share the same backend resolution path as the hosted page and differ primarily in presentation.[cite:4]

### FR-5 PNG export

The service shall expose a synchronous PNG export endpoint for an existing chart ID using caller-supplied width and height parameters.[cite:28][cite:30] The implementation shall render a chart page at the requested dimensions and capture a screenshot using Playwright’s screenshot API.[cite:28][cite:30]

### FR-6 Indicator support

The backend shall compute the following indicators in version 1 when requested in the chart spec:

- Simple Moving Average (SMA)
- Exponential Moving Average (EMA)
- Volume Weighted Average Price (VWAP)
- Bollinger Bands

Indicator outputs shall be represented as derived series in the normalized payload so that hosted render, embed render, and PNG export remain consistent.[cite:4]

### FR-7 Range support

The chart specification shall support both fixed and rolling range semantics for provider-backed charts.[cite:26][cite:37]

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

The service shall resolve both forms into provider-native query parameters at request time.[cite:26][cite:37]

### FR-8 Time format handling

Caller-provided timestamps in version 1 shall be accepted as ISO date strings only.[cite:62][cite:65] The normalization layer shall convert those values into the date representation expected by Lightweight Charts for daily-series data.[cite:62][cite:65]

### FR-9 Multi-series and pane forward compatibility

The schema shall support multiple series from day one, and each series shall include a `pane` field.[cite:4] Version 1 runtime behavior may implement one-pane rendering first, but the contract must not prevent future expansion to multiple panes, since Lightweight Charts documents pane support as a first-class concept.[cite:16][cite:17]

## Non-functional requirements

### NFR-1 Maintainability

The codebase shall be organized as a modular Python application with separate concerns for API routing, domain models, provider adapters, data normalization, rendering translation, export logic, and persistence.[cite:39][cite:44]

### NFR-2 Deployability

The system shall be deployable to a single VPS using Docker Compose with three services: application, Postgres, and reverse proxy.[cite:39][cite:44]

### NFR-3 Performance

The system shall support direct chart rendering and API retrieval for approximately 25 years of daily data per series, which is on the order of several thousand bars and is practical for browser rendering and JSON transport when payload shape is kept compact.[cite:4] PNG export shall aim for synchronous behavior under normal load, subject to bounded dimensions and timeouts.[cite:28][cite:30]

### NFR-4 Security

The service shall keep provider credentials entirely server-side and shall not embed credentials in chart URLs, frontend code, or public payloads.[cite:26][cite:37] The service shall use opaque non-sequential IDs and request-size/rate controls, but chart URLs are not considered authenticated resources in version 1.[cite:49][cite:55]

### NFR-5 Observability

The service shall emit structured JSON logs sufficient for operational troubleshooting.[cite:39] No metrics or tracing stack is required in version 1.[cite:39]

## Architecture

### High-level architecture

The system consists of the following major components:

1. FastAPI HTTP application for API routes, page routes, and static asset delivery.[cite:39]
2. Postgres database for durable chart definitions and related metadata.[cite:44]
3. Provider adapter layer for direct input, EODHD, and IB historical bars.[cite:26][cite:37][cite:7]
4. Normalization and indicator engine that converts source data into a canonical internal representation.[cite:4]
5. Frontend renderer pages built around TradingView Lightweight Charts.[cite:4]
6. Playwright export service for PNG generation.[cite:28][cite:30]
7. Reverse proxy (Nginx or Caddy) for TLS termination, compression, and rate limiting.[cite:39]

### Request flow: chart creation

1. Client sends `POST /api/charts` with a high-level chart definition.[cite:39]
2. Backend validates the payload using Pydantic models.[cite:39]
3. Backend generates a short opaque chart ID.[cite:49][cite:55]
4. Backend persists the canonical chart definition in Postgres JSONB columns.[cite:44][cite:43]
5. Backend returns chart URLs and metadata.[cite:39]

### Request flow: chart view or embed

1. Browser requests `/charts/{id}` or `/embed/{id}`.[cite:4]
2. Backend resolves the chart definition from Postgres by ID.[cite:44]
3. Backend either uses inline data or calls the relevant provider adapter for latest source data.[cite:26][cite:37]
4. Backend normalizes data, computes derived indicator series, and produces a normalized chart payload.[cite:4]
5. Frontend page loads the payload and renders the chart with TradingView Lightweight Charts.[cite:4]

### Request flow: PNG export

1. Client requests `/api/charts/{id}/png?width=...&height=...`.[cite:28]
2. Backend validates chart existence and dimensions.[cite:28]
3. Backend constructs an internal render URL for the chart in export mode.[cite:28][cite:30]
4. Playwright loads the page and waits for a ready signal from the frontend renderer.[cite:28][cite:30]
5. Playwright captures a screenshot of the chart container and returns `image/png` synchronously.[cite:28][cite:30]

## Technology choices

### Backend

- Python 3.12 or current supported Python 3.x LTS runtime
- FastAPI for HTTP APIs and page serving.[cite:39]
- Pydantic v2 for schema validation and serialization.[cite:39]
- SQLAlchemy 2.x async stack with `asyncpg` for Postgres access.[cite:58]
- Alembic for schema migrations.[cite:58]

### Database

- PostgreSQL as the primary and only database in version 1.[cite:44]
- JSONB columns for chart definitions and flexible metadata.[cite:44][cite:43]

### Frontend

- Minimal HTML/CSS/JavaScript frontend served as static assets by the application or reverse proxy.[cite:39]
- TradingView Lightweight Charts as the rendering library.[cite:4]

### Export

- Playwright Python for headless browser screenshot generation.[cite:28][cite:30]

### Provider libraries

- Standard HTTP client for EODHD requests against end-of-day historical endpoints.[cite:26]
- `ib_async` for Interactive Brokers historical data access via remote IB Gateway.[cite:7]

## Domain model

### Core entities

#### Chart

A persisted chart definition addressed by a short opaque ID.[cite:44][cite:49]

Fields:
- `id: str`
- `created_at: datetime`
- `updated_at: datetime`
- `source_kind: str`
- `title: Optional[str]`
- `instrument_meta: dict`
- `chart_definition: dict`
- `normalized_payload: Optional[dict]`
- `inline_series: Optional[dict]`
- `last_rendered_at: Optional[datetime]`
- `last_exported_at: Optional[datetime]`

#### ChartDefinition

The canonical high-level request body persisted as JSONB.[cite:44]

Substructures:
- `source`
- `instrument`
- `range`
- `view`
- `layout`
- `series`
- `annotations` (reserved for future use)

#### NormalizedChartPayload

The backend-generated render contract consumed by the frontend renderer.[cite:4]

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
  source_kind text not null,
  title text null,
  instrument_meta jsonb not null,
  chart_definition jsonb not null,
  normalized_payload jsonb null,
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
create index idx_charts_instrument_meta_gin on charts using gin (instrument_meta);
```

PostgreSQL JSONB is appropriate here because the chart definition is semistructured, likely to evolve, and benefits from native JSON operators and indexing.[cite:44][cite:43]

### Persistence policy

- Charts live forever unless manually deleted in a future administrative tool.[cite:44]
- Direct charts persist inline data in `inline_series`.[cite:44]
- Provider-backed charts do not persist fetched market data by default.[cite:26][cite:37]
- `normalized_payload` is optional and may be treated as a rebuildable optimization artifact rather than a source of truth.[cite:44]

## ID generation

Chart IDs shall be short, opaque, URL-safe, and non-sequential.[cite:49][cite:55] The implementation may use a Nano ID-inspired alphabet and entropy model even if the exact implementation is in Python rather than JavaScript.[cite:49][cite:55]

Requirements:
- Minimum entropy sufficient to avoid practical guessing through enumeration.[cite:49][cite:55]
- URL-safe alphabet.
- No numeric autoincrement IDs exposed publicly.
- Stable length for consistent URL appearance.

Recommended default: 16 to 21 URL-safe characters.[cite:49][cite:55]

## API specification

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
      "kind": "candlestick",
      "pane": 0,
      "data_format": "ohlcv",
      "data": [
        { "time": "2026-05-01", "open": 560.12, "high": 564.2, "low": 558.1, "close": 563.85, "volume": 72830000 }
      ]
    },
    {
      "id": "ema20",
      "kind": "line",
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
- `source.kind` must be one of `direct`, `eodhd`, `ib`.[cite:26][cite:37]
- Direct charts must include inline data for at least one non-derived series.[cite:4]
- Provider charts must not include inline market data as authoritative source data.[cite:26][cite:37]
- Dates must be ISO date strings.[cite:62][cite:65]
- Width and height are not supplied at creation time because export dimensions are caller-specified per export request.[cite:28]

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

If the chart is provider-backed, the service shall fetch latest source data before returning the payload.[cite:26][cite:37]

### 3. Hosted chart page

**Route**: `GET /charts/{id}`

**Purpose**: Render a minimal full page chart.

Requirements:
- Responsive layout.[cite:4]
- Minimal wrapper UI.
- SEO is not required.
- Page shall fetch the resolved payload from `/api/charts/{id}` or receive it server-side.
- Page shall emit a “chart ready” signal for export workflows.[cite:28][cite:30]

### 4. Embed chart page

**Route**: `GET /embed/{id}`

**Purpose**: Render a minimal iframe-safe chart view.

Requirements:
- Same chart rendering logic as hosted page.[cite:4]
- Reduced chrome and margins.
- Stable height behavior and responsive width.
- No interactive toolbar beyond what is easiest to implement.

### 5. PNG export

**Route**: `GET /api/charts/{id}/png?width={w}&height={h}`

**Purpose**: Return a PNG image of the chart at requested dimensions.[cite:28][cite:30]

Validation:
- Width and height required.
- Width and height must be integers.
- Width and height must fall within configured safe bounds to prevent abuse.[cite:28]

Recommended bounds:
- minimum width: 320
- minimum height: 200
- maximum width: 2400
- maximum height: 1600

Error behavior:
- `404` if chart not found.
- `422` if dimensions invalid.
- `504` or `500` if export times out or rendering fails.[cite:28][cite:30]

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
- `direct` uses inline data and ignores provider config.[cite:4]
- `eodhd` requires provider identifiers and date resolution fields appropriate to EOD historical retrieval.[cite:26]
- `ib` requires provider config sufficient to resolve the contract externally and request historical bars through `ib_async`.[cite:7][cite:37]

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
- Both range modes are supported for provider-backed charts.[cite:26][cite:37]
- Direct charts may include range for metadata, but inline data remains authoritative.[cite:4]
- `lookback` must parse into a supported relative duration unit such as `d`, `w`, `m`, or `y`.[cite:37]

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
- The system stores the symbol as provided in the chart config.[cite:26][cite:37]
- For provider-backed charts, the provider adapter is responsible for interpreting the symbol according to provider rules.[cite:26][cite:37]

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
- Runtime may implement only `single` in version 1 while still accepting a pane index field per series.[cite:16][cite:17]

### Series model

Each series entry may represent raw input data or a derived indicator series.

Raw series example:

```json
{
  "id": "price",
  "kind": "candlestick",
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
  "kind": "line",
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
- `kind`
- `pane`

Optional fields depending on role:
- `data_format`
- `data`
- `indicator`
- `style`
- `label`

## Normalized internal data model

The backend shall normalize all source data into canonical internal bar/value records before rendering translation.[cite:4]

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
- Sort all rows by ascending date before indicator computation and frontend serialization.[cite:4]
- Reject duplicate dates within a series unless a future override policy is introduced.[cite:4]
- Coerce numeric fields to floats/ints as appropriate.
- Preserve input symbol metadata separately from time-series rows.

## Frontend rendering contract

The frontend should consume a compact normalized payload that maps directly onto Lightweight Charts’ series model.[cite:4]

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
- Create chart instance.[cite:4]
- Apply theme and layout options.[cite:4]
- Add series by type.[cite:4]
- Set series data.[cite:4]
- Resize responsively.[cite:4]
- Emit a ready signal when first render completes for export coordination.[cite:28][cite:30]

## Indicator engine requirements

### SMA

Compute rolling simple average over the configured source series close or value field.

### EMA

Compute exponential moving average over the configured source series close or value field.

### VWAP

Compute volume-weighted average price for OHLCV-capable source series. The default implementation shall use cumulative VWAP over the returned dataset in version 1 unless a session-reset policy is added later.[cite:4]

### Bollinger Bands

Compute middle band, upper band, and lower band from the configured source series with adjustable period and standard deviation multiplier.

Indicator requirements:
- Derived series must inherit timestamps from the source series after warm-up periods.
- Missing early values may be omitted or represented as gaps; the policy must be consistent across indicators.[cite:4]
- Indicators shall be computed server-side in version 1 so all render targets receive identical results.[cite:4]

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
- Persist inline series for future regeneration.[cite:4]

### EODHD adapter

Scope:
- End-of-day historical data only in version 1.[cite:26]

Requirements:
- Accept symbol and resolved date range.
- Call the EOD historical endpoint using server-side credentials.[cite:26]
- Normalize returned rows into canonical OHLCV or value series.
- Never expose the provider token to clients.[cite:26]

### IB adapter

Scope:
- Historical bars only in version 1 via remote IB Gateway using `ib_async`.[cite:7][cite:37]

Requirements:
- Accept already-resolved contract information or equivalent provider config sufficient for retrieval.[cite:7]
- Respect historical data pacing and request-size limits documented by Interactive Brokers.[cite:37]
- Enforce guardrails on range size and repeated requests.[cite:37]
- Normalize returned bars into canonical series.

## Error handling

The API shall use JSON error responses for API routes and simple human-readable fallback text or minimal error pages for hosted/embed routes.[cite:39]

Recommended error categories:
- `400 Bad Request`: malformed input body.
- `404 Not Found`: unknown chart ID.
- `409 Conflict`: duplicate conflicting series IDs within a chart definition.
- `422 Unprocessable Entity`: semantic validation failure such as invalid range, missing inline data, or unsupported indicator config.[cite:39]
- `502 Bad Gateway`: provider failure from EODHD or IB Gateway.[cite:26][cite:37]
- `504 Gateway Timeout`: export or provider request timeout.[cite:28][cite:37]

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

The service is anonymously readable, but it still requires baseline hardening because provider-backed charts can trigger upstream data requests.[cite:26][cite:37]

Required controls:
- Provider credentials stored only in server environment configuration.[cite:26][cite:37]
- Request body size limits at reverse proxy and application level.[cite:39]
- Export dimension limits to prevent oversized screenshot abuse.[cite:28]
- Basic IP-based rate limiting at the reverse proxy for chart creation and export endpoints.[cite:39]
- Strict input validation for chart creation payloads.[cite:39]
- No stack traces or credential-bearing error messages in public responses.[cite:39]

The chart ID is an identifier, not an authentication boundary.[cite:49][cite:55] Any possession of a valid URL implies read access in version 1.[cite:49][cite:55]

## Logging and observability

Structured JSON logs shall be emitted for:
- incoming requests
- chart creation
- chart resolution
- provider fetches
- export attempts
- error conditions
- duration measurements for provider fetch, normalization, render, and export stages.[cite:39]

Suggested log fields:
- `timestamp`
- `level`
- `request_id`
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
- `app`
- `postgres`
- `proxy`

### Reverse proxy responsibilities

- TLS termination.
- Gzip or Brotli compression.
- Rate limiting for expensive routes.
- Static asset caching headers where appropriate.
- Forwarding real client IP information to the app.[cite:39]

### Environment variables

Required application configuration:
- `DATABASE_URL`
- `BASE_URL`
- `APP_ENV`
- `LOG_LEVEL`
- `EODHD_API_KEY`
- `IB_HOST`
- `IB_PORT`
- `IB_CLIENT_ID`
- `EXPORT_BROWSER_WS_ENDPOINT` or local browser settings
- `EXPORT_TIMEOUT_MS`
- `PNG_MIN_WIDTH`
- `PNG_MIN_HEIGHT`
- `PNG_MAX_WIDTH`
- `PNG_MAX_HEIGHT`

### Backup and recovery

Because charts live forever, database backups are required operationally even in version 1.[cite:44] A daily logical backup of Postgres is sufficient initially.[cite:44]

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
    playwright_exporter.py
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

- Set up FastAPI app, config, logging, database session management, and migrations.[cite:39][cite:58]
- Create `charts` table.[cite:44]
- Implement opaque ID generation.[cite:49][cite:55]
- Implement `POST /api/charts` and `GET /api/charts/{id}` for direct charts only.[cite:39]

### Phase 2: Frontend rendering

- Build minimal hosted page and embed page.[cite:4]
- Implement normalized payload rendering with Lightweight Charts.[cite:4]
- Add responsive layout and chart-ready signal.[cite:28][cite:30]

### Phase 3: Indicators

- Implement SMA, EMA, VWAP, and Bollinger calculations.[cite:4]
- Add derived-series materialization to payload builder.[cite:4]

### Phase 4: EODHD provider

- Implement provider adapter and range resolution for fixed and relative modes.[cite:26]
- Add provider-backed chart creation and retrieval.[cite:26]

### Phase 5: IB provider

- Implement historical bar adapter using `ib_async`.[cite:7]
- Add request guardrails and pacing-aware limits.[cite:37]

### Phase 6: PNG export

- Build Playwright exporter with synchronous response path.[cite:28][cite:30]
- Validate width/height bounds and timeout handling.[cite:28]

### Phase 7: Hardening

- Add proxy rate limits, request size limits, and operational docs.[cite:39]
- Add basic smoke tests for chart create/view/export flows.[cite:39]

## Acceptance criteria

The implementation shall be considered complete for version 1 when all of the following are true:

1. A direct-data chart can be created, stored in Postgres, retrieved by opaque chart ID, and rendered in both hosted and embed pages.[cite:44][cite:4]
2. A provider-backed EODHD chart can be created with fixed or relative range semantics and renders using latest fetched data.[cite:26]
3. A provider-backed IB historical chart can be created and rendered against a remote IB Gateway through `ib_async`, with documented limitations and guardrails.[cite:7][cite:37]
4. Requested indicators SMA, EMA, VWAP, and Bollinger are computed server-side and displayed correctly as derived series.[cite:4]
5. `GET /api/charts/{id}/png` returns a PNG image synchronously for valid dimensions under normal operating conditions.[cite:28][cite:30]
6. The application deploys successfully on a single VPS with Docker Compose, Postgres, and a reverse proxy.[cite:39][cite:44]
7. The service exposes no provider credentials to clients and emits structured JSON logs for core operations.[cite:26][cite:39]

## Open implementation notes

The specification intentionally leaves some engineering choices to the implementation team while constraining behavior and interfaces sufficiently to avoid ambiguity.[cite:39][cite:44] Acceptable implementation-level decisions include whether frontend payloads are fetched client-side or server-rendered into the HTML, whether `normalized_payload` is persisted eagerly or lazily, and whether the application uses server-side templates or static HTML plus JSON API for the page shell.[cite:39][cite:44]

The implementation team should favor the simplest solution that preserves the public contract, because the product’s value in version 1 comes from a stable chart definition model, reliable provider abstraction, and a minimal deployable system rather than UI sophistication.[cite:4][cite:44]
