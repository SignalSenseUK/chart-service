# Future Potential Improvements

While the current Chart Service architecture is robust and ready for production, there are several areas of potential expansion to enhance performance, usability, and feature breadth.

## 1. Caching Layer (Redis)
**Current State**: Each chart retrieval (`GET /api/charts/{id}`) dynamically executes indicator computation and, for provider-backed charts, network fetches to the upstream data provider.
**Improvement**: Introduce a Redis caching layer for normalized payloads. Provider data and computed indicators could be cached with a TTL relative to the requested range (e.g., historical data cached for 24 hours, recent intraday data cached for 5 minutes), dramatically reducing API latency and upstream provider costs.

## 2. Real-Time Streaming (WebSockets)
**Current State**: Data is historical and statically rendered at the time of the API request.
**Improvement**: Extend the FastApi backend to support WebSockets, streaming live data updates from providers like IB directly to the frontend Lightweight Charts instance, enabling live-updating ticks and bars.

## 3. Expanded Provider Ecosystem
**Current State**: Native support for EODHD, IB, and Direct Data.
**Improvement**: Add additional adapters adhering to the `MarketDataAdapter` protocol. Candidates include:
- Polygon.io
- Alpaca
- Binance / Coinbase (Crypto)
- AlphaVantage

## 4. Enhanced Indicator Suite
**Current State**: Supports core indicators (SMA, EMA, VWAP, Bollinger Bands).
**Improvement**: Expand the indicator engine to calculate advanced oscillators and overlays:
- RSI (Relative Strength Index)
- MACD (Moving Average Convergence Divergence)
- ATR (Average True Range)
- Ichimoku Cloud

## 5. User Authentication & Multi-Tenancy
**Current State**: The service is designed for single-tenant internal use, guarded primarily via network isolation or API gateway layers.
**Improvement**: Implement native OAuth2 or JWT-based authentication within the FastAPI layer. Extend the database schema to attach `user_id` or `workspace_id` to charts, allowing for true multi-tenancy and secure public deployments.

## 6. Chart Annotations & Drawing Tools
**Current State**: Visual presentation relies on series data arrays.
**Improvement**: While Lightweight Charts is somewhat limited in drawing tools natively, custom overlay plugins or migrating to the full TradingView Technical Analysis library would allow saving persistent user annotations (trendlines, fibonacci retracements) alongside the chart definition in Postgres.
