# Deployment Guide

The Chart Service is designed to be self-hosted via Docker Compose, utilizing a proxy tier (Caddy), the backend application (FastAPI), a persistent data store (PostgreSQL), and a headless browser engine (Browserless/Playwright).

## Prerequisites

- **Docker & Docker Compose**: Installed and running on the host machine.
- **Public DNS**: A domain name pointing to the public IP of your host machine (e.g., `charts.example.com`).
- **Data Provider Keys (Optional)**: If you plan to use EODHD or Interactive Brokers.

## Quick Start

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd chart-service
   ```

2. **Configure Environment Variables:**
   ```bash
   cp .env.example .env
   ```
   Open `.env` and fill in the necessary fields. Pay special attention to:
   - `BASE_URL`: The public URL where the service will be accessible (e.g., `https://charts.example.com`).
   - `APP_ENV`: Set to `production` to sanitize error outputs.
   - Provider variables like `EODHD_API_KEY` and `IB_HOST` if you're using them.

3. **Configure the Proxy:**
   Edit the `Caddyfile` located in the root of the project to replace the dummy domains with your actual public domain.

4. **Build and Run:**
   ```bash
   docker compose build
   docker compose up -d
   ```

5. **Initialize Database:**
   Once the containers are running, apply the initial database migrations:
   ```bash
   docker exec -it chart_app alembic upgrade head
   ```

6. **Verify:**
   Navigate to `https://<your-domain>/health` in your browser. You should receive an `ok` status indicating the application and database are successfully connected.

## Architecture Security & Hardening

The provided `docker-compose.yml` and `Caddyfile` include several best practices for production environments:

- **Rate Limiting**: (Note: uncomment the relevant lines in the Caddyfile if you have built Caddy with the `caddy-ratelimit` module). Prevents abuse on API endpoints.
- **Payload Size Limits**: Middleware restricts incoming payloads on `/api/*` to 10MB to mitigate memory exhaustion from excessively large direct data pushes.
- **Security Headers**: Standard headers such as `X-Content-Type-Options`, `Referrer-Policy`, and HSTS are included in Caddy.
- **Error Sanitization**: In `APP_ENV=production`, stack traces and underlying exceptions are heavily sanitized, returning generic 500 responses for internal server errors.

## Database Migrations & Backups

### Migrations
When upgrading the chart-service version, you may need to apply database schema updates using Alembic. You can run migrations via the app container:

```bash
docker exec -it chart_app alembic upgrade head
```
*(Ensure the exact container name matches what is defined in your compose stack)*

### Backups
Chart definitions are stored in PostgreSQL. You should set up a regular backup cadence. An example daily cron job:

```bash
0 3 * * * docker exec chart-postgres pg_dump --format=custom -U chart chart_db \
  > /backups/chart_$(date +\%F).pgdump && \
  find /backups -name 'chart_*.pgdump' -mtime +35 -delete
```

## Scaling the Service

- **Horizontal Scaling**: The FastAPI app is stateless (state lives in Postgres and external providers). You can scale the `app` container by increasing its replica count and load balancing via Caddy.
- **Headless Browser Resources**: The browser container consumes significant memory and CPU during PNG exports. Adjust the memory limit in `docker-compose.yml` based on your instance size and export volume.
