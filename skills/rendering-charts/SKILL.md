---
name: rendering-charts
description: Creates, manages, and exports financial charts (candlestick, line, area, histogram) via the Chart Rendering Service API. Use when the user requests to create a chart, plot a stock price, visualize OHLCV data, add technical indicators (SMA, EMA), export a chart as PNG, display candlestick data, show a trading view, render financial data, generate an interactive chart, or work with chart URLs. Supports EODHD and Interactive Brokers data sources plus direct data injection.
allowed-tools: Bash(curl:*), Bash(httpie:*), fetch, WebFetch
---

# Chart Rendering Service

## Service Endpoint

The Chart Rendering Service base URL is determined by environment:

| Environment | Base URL |
|-------------|----------|
| Local development | `http://localhost:8000` |
| Docker | `http://chart-service:8000` |
| Custom | Set `CHART_SERVICE_URL` environment variable |

All API paths below are relative to this base URL. No authentication is required currently.

## Chart Creation Workflow

Copy this checklist and track your progress:
```
Task Progress:
- [ ] Step 1: Determine data source
- [ ] Step 2: Construct ChartCreateRequest payload
- [ ] Step 3: Call POST /api/charts
- [ ] Step 4: Handle validation errors (if any)
- [ ] Step 5: Deliver requested output
```

### Step 1: Determine data source

| Source kind | When to use | Requires `range`? | Requires `data`? |
|-------------|-------------|-------------------|-------------------|
| `eodhd` | Fetch market data from EODHD automatically | Yes | No |
| `ib` | Fetch from Interactive Brokers | Yes | No |
| `direct` | Inject your own custom data | No (omit it) | Yes |

### Step 2: Construct payload

Use this template for `POST /api/charts` and customize as needed:
```json
{
  "schema_version": 1,
  "source": { "kind": "eodhd" },
  "instrument": {
    "symbol": "AAPL",
    "asset_class": "equity"
  },
  "range": {
    "mode": "relative",
    "lookback": "1y",
    "anchor": "now"
  },
  "view": { "title": "AAPL Analysis", "theme": "dark" },
  "series": [
    {
      "id": "price",
      "type": "candlestick",
      "pane": 0
    }
  ]
}
```

**Field reference:**

| Field | Values | Notes |
|-------|--------|-------|
| `source.kind` | `"direct"`, `"eodhd"`, `"ib"` | Data source |
| `instrument.asset_class` | `"equity"`, `"forex"`, `"futures"`, `"crypto"`, `"index"` | Asset type |
| `range.lookback` | e.g., `"7d"`, `"1w"`, `"3m"`, `"1y"` | Time range for eodhd/ib |
| `range.anchor` | `"now"` or ISO date | Anchor point for lookback |
| `series[].type` | `"candlestick"`, `"line"`, `"area"`, `"histogram"`, `"bar"` | Chart type |
| `series[].pane` | Integer (0, 1, 2...) | Pane index; 0 = main chart |

**Direct data source:** If `source.kind == "direct"`, you must provide inline `data` and `data_format` (`"ohlcv"`, `"ohlc"`, `"value"`) in the series. Omit the `range` field entirely.

**Adding indicators:** Add indicator series referencing another series via `source_series`:
```json
{
  "id": "sma-20",
  "type": "line",
  "pane": 0,
  "indicator": { "name": "sma", "length": 20, "source_series": "price" }
}
```

### Step 3: Call API

Submit the payload using curl:
```bash
curl -X POST http://localhost:8000/api/charts \
  -H "Content-Type: application/json" \
  -d '<your-payload-json>'
```

Or using a fetch/HTTP tool: `POST http://localhost:8000/api/charts` with `Content-Type: application/json` header and JSON body.

**Response (201 Created):**
```json
{
  "id": "chart_abc123",
  "view_url": "/charts/chart_abc123",
  "embed_url": "/embed/chart_abc123",
  "api_url": "/api/charts/chart_abc123",
  "png_url": "/api/charts/chart_abc123/png"
}
```

### Step 4: Handle validation errors

If the API returns a 422 error, read the Pydantic error details, adjust the payload, and retry.

**Common errors:**

| Error | Cause | Fix |
|-------|-------|-----|
| 422: `data` required for direct source | `source.kind == "direct"` but no `data` in series | Add `data` array and `data_format` to each series |
| 422: `range` required | Using `eodhd` or `ib` without a range | Add `range` with `mode` and `lookback` |
| 422: invalid `asset_class` | Unsupported asset class value | Use one of: equity, forex, futures, crypto, index |
| 422: `range` must be omitted for direct | Direct source with a range field | Remove the `range` field entirely |
| 404: chart not found | Invalid chart ID | Verify ID from the creation response |
| 422: invalid `data_format` | Unsupported format | Use one of: ohlcv, ohlc, value |

### Step 5: Deliver output

- **Interactive charts:** Return the `view_url` (e.g., `/charts/{id}`).
- **Embeddable charts:** Return the `embed_url` (e.g., `/embed/{id}`).
- **Static images:** Request `GET /api/charts/{id}/png?width=800&height=600` and return the image.

## Quick Examples

**EODHD candlestick with SMA indicator:**
```json
{
  "schema_version": 1,
  "source": { "kind": "eodhd" },
  "instrument": { "symbol": "TSLA", "asset_class": "equity" },
  "range": { "mode": "relative", "lookback": "3m" },
  "series": [
    { "id": "price", "type": "candlestick", "pane": 0 },
    { "id": "sma-20", "type": "line", "pane": 0, "indicator": { "name": "sma", "length": 20, "source_series": "price" } }
  ]
}
```

**Direct data injection (custom equity curve):**
```json
{
  "schema_version": 1,
  "source": { "kind": "direct" },
  "instrument": { "symbol": "CUSTOM", "asset_class": "equity" },
  "series": [
    {
      "id": "curve",
      "type": "area",
      "pane": 0,
      "data_format": "value",
      "data": [
        { "time": "2023-01-01", "value": 10000 },
        { "time": "2023-01-02", "value": 10150 }
      ]
    }
  ]
}
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| **POST** | `/api/charts` | Create chart. Returns chart with URLs. |
| **GET** | `/api/charts` | List charts. Query params: `page`, `limit`, `source_kind`. |
| **GET** | `/api/charts/{id}` | Get full chart payload including data arrays. |
| **PUT** | `/api/charts/{id}` | Update chart definition. |
| **DELETE** | `/api/charts/{id}` | Soft-delete a chart. |
| **GET** | `/api/charts/{id}/png` | Export PNG. Query params: `width`, `height`. |
| **GET** | `/charts/{id}` | Frontend chart viewing page. |
| **GET** | `/embed/{id}` | Iframe-friendly embed page. |

## Deep-Dive Documentation

| Reference | When to Use |
|-----------|-------------|
| [references/api-reference.md](references/api-reference.md) | Full request/response schemas for all endpoints |
| [references/examples.md](references/examples.md) | Additional chart patterns and advanced use cases |
