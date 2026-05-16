# API Reference

The service provides several API endpoints for managing charts. The base URL depends on the deployed instance (e.g., `https://charts.yourdomain.com`).

| Method | Path | Description |
|--------|------|-------------|
| **POST** | `/api/charts` | Create chart. Returns payload with URLs (`view_url`, `embed_url`, `api_url`, `png_url`). |
| **GET** | `/api/charts` | List charts. Supports query params `page`, `limit`, `source_kind`. |
| **GET** | `/api/charts/{id}` | Get full resolved payload, including data arrays. |
| **PUT** | `/api/charts/{id}` | Update existing chart definition. |
| **DELETE** | `/api/charts/{id}` | Soft-delete a chart. |
| **GET** | `/api/charts/{id}/png` | Export PNG. Query params: `width`, `height`. |
| **GET** | `/charts/{id}` | The frontend hosted chart viewing page. |
| **GET** | `/embed/{id}` | The iframe-friendly embed page. |
