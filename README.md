# Google Find My Tools Prometheus Exporter

This exporter uses the `GoogleFindMyTools` submodule to expose device location data to Prometheus.

## Requirements

- Python 3.10+
- `GoogleFindMyTools` submodule present in this repository
- Google account authentication data

## Authentication File Setup (Important)

This exporter uses `GoogleFindMyTools/Auth/secrets.json`.

You can prepare it in one of these ways:

1. Generate it
Run the authentication flow from `GoogleFindMyTools` once, then confirm that `GoogleFindMyTools/Auth/secrets.json` is created.

2. Copy an existing file
If you already have a valid `secrets.json` from another environment, place it at `GoogleFindMyTools/Auth/secrets.json`.

Note: You may see `Auth/secret.json` in some places, but this project uses `secrets.json` (plural).

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python prometheus_exporter.py
```

After startup, check metrics at `http://127.0.0.1:9824/metrics`.

## Environment Variables

- `EXPORTER_HOST` (default: `0.0.0.0`)
- `EXPORTER_PORT` (default: `9824`)
- `LOCATION_TIMEOUT_SECONDS` (default: `30`)
- `LOG_LEVEL` (default: `INFO`)

## Behavior

- Loads and caches device list once at startup
- On every `/metrics` request, calls `get_location_data_for_device` for all devices and exports the latest values

## Main Metrics

- `google_find_my_device_latitude_degrees`
- `google_find_my_device_longitude_degrees`
- `google_find_my_device_altitude_meters`
- `google_find_my_device_report_timestamp_seconds`
- `google_find_my_device_status`
- `google_find_my_device_is_own_report`
- `google_find_my_device_report_age_seconds`
- `google_find_my_device_reports_total`
- `google_find_my_device_scrape_success`

## Prometheus Config Example

```yaml
scrape_configs:
  - job_name: google_find_my_tools
    scrape_interval: 10m
    static_configs:
      - targets: ["127.0.0.1:9824"]
```
