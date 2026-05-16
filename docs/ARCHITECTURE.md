# Architecture

The Chart Service is built as a modular, domain-driven application prioritizing performance, composability, and clear boundaries. It is designed to act as a self-hosted rendering engine capable of processing financial data from multiple upstream providers and rendering it into both interactive web charts and static images.

## High-Level Architecture

The service consists of four main architectural tiers running as distinct services within a Docker Compose stack:

1. **Proxy Layer (Caddy)**: Handles TLS termination, rate-limiting, and payload size enforcement. It routes external traffic to the application backend.
2. **Application Server (FastAPI)**: The core service orchestrating data ingestion, normalization, storage, indicator computation, and rendering payload construction.
3. **Database (PostgreSQL)**: Persists chart definitions and metadata. It uses a high-performance async driver (`asyncpg`) to manage connections.
4. **Browser Sidecar (Browserless/Playwright)**: A headless Chromium instance responsible for rendering charts in a simulated DOM and exporting them as PNG images.

## Core Application Modules

The application itself is built with FastAPI and organized into the following distinct domains:

### 1. API & Routing Layer
Defines HTTP and Web endpoints. Contains the controllers that validate incoming requests against Pydantic schemas, handle dependency injection, and map exceptions to standardized JSON error responses.

- `/api/charts`: Chart CRUD operations.
- `/api/charts/{id}/png`: Sync/Async image export trigger.
- `/charts/{id}` & `/embed/{id}`: Interactive HTML/JS endpoints serving TradingView Lightweight Charts.

### 2. Domain Services
These are the business logic engines, strictly decoupled from external data dependencies and HTTP concerns.

- **Chart Service**: Orchestrates the creation and retrieval of chart metadata and definitions.
- **Normalization Service**: Ensures incoming data—whether direct or via providers—is rigorously sorted, deduplicated, and formatted (e.g., OHLCV bar extraction).
- **Indicator Engine**: A localized calculation service that derives server-side indicators such as SMA, EMA, VWAP, and Bollinger Bands using a highly optimized, O(n) rolling-window approach.
- **Render Payload Builder**: Takes normalized bars and computed indicators, constructing the final structured JSON object used by the frontend JS renderer.

### 3. Provider Adapters
To support various sources of truth for historical pricing, the service abstracts data ingestion into a generic `MarketDataAdapter` protocol.

- **Direct Adapter**: Ingests inline data arrays provided directly within the `POST` payload.
- **EODHD Adapter**: Connects to the EODHD REST API.
- **Interactive Brokers (IB) Adapter**: Uses `ib_async` to maintain a persistent, backoff-enabled connection to an IB Gateway for institutional-grade historical data.

### 4. Export Engine
The `BrowserExporter` coordinates with the browser sidecar via the Chrome DevTools Protocol (CDP). When a PNG request is made, the exporter instructs the sidecar to load the chart's embed URL, await the `data-chart-ready="true"` signal in the DOM, and capture a screenshot.

## Data Flow

1. **Creation**: A request arrives containing either inline data or a directive to use a provider. The app determines the series, delegates to a provider if necessary for initial validation, and stores the chart definition.
2. **Retrieval**: On access, the Render Payload Builder orchestrates data fetching (or pulls inline data), runs the normalization and indicator passes, and serves the result to the client.
3. **Rendering**: The client browser or headless sidecar initializes the Lightweight Charts instance, applies a color palette, and renders the specific series types (candlestick, bar, line, etc.) based on the requested definition.
