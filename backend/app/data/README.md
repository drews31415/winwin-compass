# Data Pipeline

This package collects and transforms Seoul public data for commercial-area analysis.

## Structure

- `collectors/base.py`: shared async HTTP client with retry, Redis cache, and rate limiting.
- `collectors/seoul_api.py`: Seoul Open API adapter and schema normalization entry points.
- `collectors/scheduler.py`: APScheduler jobs for initial seed and recurring updates.
- `processors/transformer.py`: raw API normalization, risk helpers, and population enrichment.

## Development Notes

Keep API-specific field mapping inside collectors/processors. Do not embed raw Seoul API field names in routers or UI code. When `SEOUL_API_KEY` is missing, return deterministic dummy data for development and demos.
