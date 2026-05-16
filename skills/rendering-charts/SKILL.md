---
name: rendering-charts
description: Generates, manages, and delivers interactive or static financial charts using the Chart Rendering Service. Use when the user requests to visualize financial data, create a chart, or export a chart image.
---

# Chart Rendering Service

## Chart creation workflow
Copy this checklist and track your progress:
```
Task Progress:
- [ ] Step 1: Determine data source
- [ ] Step 2: Construct ChartCreateRequest payload
- [ ] Step 3: Call POST /api/charts
- [ ] Step 4: Handle validation errors (if any)
- [ ] Step 5: Deliver requested output
```

**Step 1: Determine data source**
- Use `direct` to inject your own custom data.
- Use `eodhd` or `ib` to let the service fetch data automatically.

**Step 2: Construct payload**
Use this template for `POST /api/charts` and customize as needed:
```json
{
  "schema_version": 1,
  "source": { "kind": "eodhd" }, // "direct", "eodhd", or "ib"
  "instrument": {
    "symbol": "AAPL",
    "asset_class": "equity" // "equity", "forex", "futures", "crypto", "index"
  },
  "range": { // Required for eodhd/ib
    "mode": "relative",
    "lookback": "1y", // e.g., "7d", "1w", "3m", "1y"
    "anchor": "now"
  },
  "view": { "title": "AAPL Analysis", "theme": "dark" },
  "series": [
    {
      "id": "price",
      "type": "candlestick", // "candlestick", "line", "area", "histogram", "bar"
      "pane": 0
    }
  ]
}
```
*Note: If `source.kind == "direct"`, you must provide inline `data` and `data_format` ("ohlcv", "ohlc", "value") in the series. You must also omit the `range` field.*

**Step 3: Call API**
Submit the payload to `POST /api/charts`.

**Step 4: Handle validation errors**
If the API returns a 422 error, read the Pydantic error details, adjust the payload, and retry.

**Step 5: Deliver output**
- For interactive charts: Return the `view_url` (e.g., `/charts/{id}`).
- For static images: Request `GET /api/charts/{id}/png?width=800&height=600` and embed the returned image link.

## Advanced features
**Examples**: See [examples.md](examples.md) for common chart patterns and specific use cases.
**API Reference**: See [reference.md](reference.md) for a list of all available service endpoints and operations.
