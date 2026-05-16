# Examples for Chart Rendering

Generate payloads following these examples:

**Example 1: EODHD Price with SMA Indicator**
Input: Show a 3-month TSLA chart with a 20-day SMA.
Output:
```json
{
  "schema_version": 1,
  "source": { "kind": "eodhd" },
  "instrument": { "symbol": "TSLA", "asset_class": "equity" },
  "range": { "mode": "relative", "lookback": "3m" },
  "series": [
    { "id": "price", "type": "candlestick", "pane": 0 },
    { 
      "id": "sma-20", 
      "type": "line", 
      "pane": 0, 
      "indicator": { "name": "sma", "length": 20, "source_series": "price" } 
    }
  ]
}
```

**Example 2: Direct Data Injection**
Input: Plot this custom equity curve data.
Output:
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
        {"time": "2023-01-01", "value": 10000}, 
        {"time": "2023-01-02", "value": 10150} 
      ]
    }
  ]
}
```
