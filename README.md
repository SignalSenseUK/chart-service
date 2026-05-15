# Chart Service

A self-hosted chart rendering service that accepts chart definitions, persists them under short opaque IDs, and renders financial charts using TradingView Lightweight Charts. Includes hosted/embed pages, server-side indicators, EODHD and Interactive Brokers providers, and synchronous PNG export via a headless browser sidecar.

## Quick start

Requirements: Docker + Docker Compose, a public DNS name pointed at the host.

```bash
cp .env.example .env
# Edit .env to set DATABASE_URL, BASE_URL, EODHD_API_KEY, IB_* if needed.
# Edit Caddyfile to set your domain (replace charts.example.com).
docker compose build
docker compose up -d
```

Open `https://<your-domain>/health` to confirm the app is up, then create a chart via `POST /api/charts`.

## API endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET    | `/health` | App + database readiness probe. |
| POST   | `/api/charts` | Create a chart definition; returns view/embed/api URLs. |
| GET    | `/api/charts` | Paginated chart listing; supports `page`, `limit`, `source_kind`. |
| GET    | `/api/charts/{id}` | Resolved normalized payload (`payload.series`, `meta`, `instrument`, `warnings`). |
| PUT    | `/api/charts/{id}` | Replace the definition (cannot change `source_kind`). |
| DELETE | `/api/charts/{id}` | Soft-delete; subsequent GETs return 410. |
| GET    | `/api/charts/{id}/png?width&height` | Synchronous PNG export. |
| GET    | `/charts/{id}` | Hosted chart page. |
| GET    | `/embed/{id}` | Iframe-friendly embed page (sets `Content-Security-Policy: frame-ancestors *`). |

All `/api/*` responses include `Access-Control-Allow-Origin: *`. Direct charts must include inline OHLCV/OHLC/value data; provider-backed charts (`eodhd`, `ib`) must include a `range` and pass an upstream validation fetch before being persisted.

## Environment variables

See `.env.example`. Key entries:

- `DATABASE_URL` - async SQLAlchemy URL (asyncpg).
- `BASE_URL` - public URL the service is reachable at, used to construct chart URLs.
- `APP_ENV` - `development`, `staging`, or `production` (controls error sanitization).
- `EODHD_API_KEY`, `EODHD_TIMEOUT_MS` - EODHD provider credentials and timeout.
- `IB_HOST`, `IB_PORT`, `IB_CLIENT_ID`, `IB_TIMEOUT_MS` - IB Gateway connection settings.
- `EXPORT_BROWSER_WS_ENDPOINT`, `EXPORT_TIMEOUT_MS` - CDP websocket URL for the browser sidecar (e.g. `ws://browser:3000`) and screenshot timeout.
- `PNG_MIN_*`, `PNG_MAX_*` - PNG export dimension bounds.
- `DB_POOL_SIZE`, `DB_MAX_OVERFLOW` - SQLAlchemy pool sizing.

## Architecture

```
              +-------------+        +--------------+
client  --->  |   proxy     |  ----> |     app      |
              |  (Caddy)    |        |  (FastAPI)   |
              +-------------+        +--------------+
                                          |
                              +---------- + ----------+
                              |                       |
                              v                       v
                       +-------------+        +---------------+
                       |  postgres   |        |   browser     |
                       |  (charts)   |        |  (browserless)|
                       +-------------+        +---------------+
```

Application internals follow the modules outlined in `specs/self_hosted_chart_service_spec.md`: API routes, domain schemas/services, provider adapters, normalization + indicator engine, render-payload builder, and browser exporter.

## Local development

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
DATABASE_URL=sqlite+aiosqlite:///:memory: .venv/bin/uvicorn app.main:create_app --factory --reload
```

Run migrations against a real Postgres:

```bash
DATABASE_URL=postgresql+asyncpg://USER:PASSWORD@host/db .venv/bin/alembic upgrade head
```

Run tests:

```bash
.venv/bin/pytest -q
```

## Backups

Charts live forever unless soft-deleted, so Postgres backups are required. Example daily cron:

```cron
0 3 * * * docker exec chart-postgres pg_dump --format=custom -U chart chart_db \
  > /backups/chart_$(date +\%F).pgdump && \
  find /backups -name 'chart_*.pgdump' -mtime +35 -delete
```

Recommended retention: 7 daily + 4 weekly snapshots, periodically restored to a scratch database to confirm integrity.

## Notes

- Lightweight Charts is loaded from a CDN in `chart.html` / `embed.html`. Vendor it if you need offline operation.
- Caddy rate-limit snippets in `Caddyfile` require the `caddy-ratelimit` module; uncomment after rebuilding the image with that module.
- The IB adapter requires a remote IB Gateway with a unique `IB_CLIENT_ID` per application instance.
