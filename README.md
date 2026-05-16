# Chart Service

![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.12+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111+-green.svg)

A self-hosted, modular chart rendering service designed to act as a robust engine for displaying financial time-series data. It accepts chart definitions, securely retrieves data via extensible provider adapters, calculates server-side indicators, and outputs interactive web charts or high-fidelity static images.

Built with Python (FastAPI, asyncpg) and [TradingView Lightweight Charts](https://tradingview.github.io/lightweight-charts/), optimized for performance and self-hostability.

---

## 📖 Documentation

For full details on how the service is built and operated, refer to our comprehensive documentation:
- [Features](docs/FEATURES.md) - Learn what the Chart Service can do out-of-the-box.
- [Architecture](docs/ARCHITECTURE.md) - Deep dive into the core application modules and data flow.
- [Deployment](docs/DEPLOYMENT.md) - Instructions for running the stack locally and deploying to production.
- [Future Improvements](docs/FUTURE_IMPROVEMENTS.md) - A roadmap for upcoming features.

## 🚀 Quick Start

The easiest way to get started is using Docker Compose.

**Requirements:** Docker + Docker Compose, and a public DNS name pointed at the host.

```bash
git clone https://github.com/SignalSense/chart-service.git
cd chart-service

cp .env.example .env
# Edit .env to set DATABASE_URL, BASE_URL, and provider API keys
# Edit Caddyfile to set your domain (replace charts.example.com)

docker compose build
docker compose up -d
```

Open `https://<your-domain>/health` to confirm the application is up, then create a chart via a `POST /api/charts` request. 
For further details, consult the [Deployment Guide](docs/DEPLOYMENT.md).

## 🔌 API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET    | `/health` | Application & database readiness probe. |
| POST   | `/api/charts` | Create a chart definition; returns view/embed/api URLs. |
| GET    | `/api/charts` | Paginated chart listing; supports `page`, `limit`, `source_kind`. |
| GET    | `/api/charts/{id}` | Resolved normalized payload (`payload.series`, `meta`, `instrument`, `warnings`). |
| PUT    | `/api/charts/{id}` | Replace the definition (cannot change `source_kind`). |
| DELETE | `/api/charts/{id}` | Soft-delete; subsequent GETs return 410. |
| GET    | `/api/charts/{id}/png?width&height` | Synchronous headless PNG export. |
| GET    | `/charts/{id}` | Hosted chart viewing page. |
| GET    | `/embed/{id}` | Iframe-friendly embed page (sets `Content-Security-Policy: frame-ancestors *`). |

All `/api/*` responses include `Access-Control-Allow-Origin: *`.

## 💻 Local Development

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt

# Run locally using an in-memory SQLite database
DATABASE_URL=sqlite+aiosqlite:///:memory: uvicorn app.main:create_app --factory --reload
```

Run tests:
```bash
pytest -q
```

## 🤝 Contributing

We welcome contributions! Please follow standard fork-and-pull-request workflows.
Ensure that your code passes all tests (`pytest`) and formatters before submitting. 

## 📝 License

This project is licensed under the MIT License - see the `pyproject.toml` file for details.
