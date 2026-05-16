# Primary Features

The Chart Service is built to act as a localized, high-performance rendering hub for financial time-series data. Below are the primary features implemented in the current version.

## 1. Multi-Provider Data Ingestion
The service decouples data definition from presentation by allowing you to define a chart pointing to a specific upstream provider, or by pushing inline data directly.

- **Direct Payload**: Push raw JSON arrays of OHLCV/OHLC or value data directly to the API. This is ideal for bespoke algorithmic signals or pre-processed datasets.
- **EODHD**: Natively fetch historical stock and ETF pricing data via the EODHD REST API.
- **Interactive Brokers (IB)**: Connect directly to an institutional IB Gateway via the `ib_async` module. The adapter handles reconnection, request pacing, and serialization for highly reliable data fetches.

## 2. Advanced Interactive Charting
The frontend leverages the industry-standard TradingView Lightweight Charts library for buttery-smooth panning, zooming, and crosshair tracking.

- Multiple series types supported (Candlestick, Bar, Line, Area, Histogram).
- Built-in dynamic theme support (Dark/Light).
- Automatic volume rendering on an isolated sub-pane as a histogram, colored contextually based on the associated bar's close vs open price.

## 3. Server-Side Indicator Engine
Avoid client-side bloat by calculating common technical indicators natively within the backend application. Indicators are computed dynamically on data retrieval, maintaining high responsiveness.

Current Supported Indicators:
- **SMA (Simple Moving Average)**
- **EMA (Exponential Moving Average)**
- **VWAP (Volume Weighted Average Price)**
- **Bollinger Bands** (Calculated using population standard deviation)

## 4. Headless Image Export
For integration into reports, emails, or static dashboards, the service can synchronously export high-fidelity PNG representations of your interactive charts.

- Uses Playwright/Browserless to spin up a headless Chromium instance.
- Safely strips application chrome, legends, and borders for a clean export using the `?export=true` view parameter.
- Employs a deterministically reliable `data-chart-ready` DOM signal to ensure no partially rendered screenshots are returned.

## 5. Embeddable Architecture
Easily distribute chart views across other applications.

- Dedicated `/embed/{id}` endpoints designed for `iframe` integration.
- Custom configurable Content-Security-Policy `frame-ancestors` directives.
- Cross-Origin Resource Sharing (CORS) correctly managed out of the box for `/api/*` endpoints.

## 6. Flexible Time Range Resolution
Define your chart ranges robustly:
- **Absolute Ranges**: Standard ISO dates (e.g. `2024-01-01` to `2024-06-01`).
- **Relative Ranges**: Flexible lookbacks (e.g. `3m`, `1y`, `7d`) dynamically evaluated relative to the current timestamp.
