#!/usr/bin/env python3
import logging
import os
import sys
import time
from typing import Dict, List, Optional, Tuple

from prometheus_client import REGISTRY, start_http_server
from prometheus_client.core import GaugeMetricFamily

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
SUBMODULE_ROOT = os.path.join(REPO_ROOT, "GoogleFindMyTools")
if SUBMODULE_ROOT not in sys.path:
    sys.path.insert(0, SUBMODULE_ROOT)

from NovaApi.ListDevices.nbe_list_devices import request_device_list
from ProtoDecoders.decoder import get_canonic_ids, parse_device_list_protobuf
from NovaApi.ExecuteAction.LocateTracker.location_request import get_location_data_for_device


class FindMyToolsCollector:
    def __init__(self, location_timeout_seconds: float):
        self._location_timeout_seconds = location_timeout_seconds
        self._devices = self._load_devices_once()

    def _load_devices_once(self) -> List[Tuple[str, str]]:
        logging.info("Loading devices once at startup...")
        device_list_hex = request_device_list()
        device_list = parse_device_list_protobuf(device_list_hex)
        devices = get_canonic_ids(device_list)
        if not devices:
            raise RuntimeError("No devices found from list_devices request")
        logging.info("Loaded %d devices", len(devices))
        return devices

    @staticmethod
    def _latest_coordinate_report(reports: List[Dict]) -> Optional[Dict]:
        coordinate_reports = [r for r in reports if r.get("latitude") is not None and r.get("longitude") is not None]
        if not coordinate_reports:
            return None
        return max(coordinate_reports, key=lambda r: r["time"])

    def collect(self):
        labels = ["device_id", "device_name"]
        latitude_metric = GaugeMetricFamily(
            "google_find_my_device_latitude_degrees",
            "Latest latitude for a device",
            labels=labels,
        )
        longitude_metric = GaugeMetricFamily(
            "google_find_my_device_longitude_degrees",
            "Latest longitude for a device",
            labels=labels,
        )
        altitude_metric = GaugeMetricFamily(
            "google_find_my_device_altitude_meters",
            "Latest altitude for a device",
            labels=labels,
        )
        timestamp_metric = GaugeMetricFamily(
            "google_find_my_device_report_timestamp_seconds",
            "Unix timestamp for latest coordinate report",
            labels=labels,
        )
        status_metric = GaugeMetricFamily(
            "google_find_my_device_status",
            "Status value for latest coordinate report",
            labels=labels,
        )
        own_report_metric = GaugeMetricFamily(
            "google_find_my_device_is_own_report",
            "Whether latest coordinate report is own report (1=true,0=false)",
            labels=labels,
        )
        age_metric = GaugeMetricFamily(
            "google_find_my_device_report_age_seconds",
            "Age in seconds of latest coordinate report",
            labels=labels,
        )
        report_count_metric = GaugeMetricFamily(
            "google_find_my_device_reports_total",
            "Number of reports returned for a device in this scrape",
            labels=labels,
        )
        scrape_success_metric = GaugeMetricFamily(
            "google_find_my_device_scrape_success",
            "1 if device scrape succeeded, else 0",
            labels=labels,
        )

        now = time.time()

        for device_name, device_id in self._devices:
            label_values = [device_id, device_name]
            try:
                reports = get_location_data_for_device(
                    device_id,
                    device_name,
                    print_output=False,
                    timeout_seconds=self._location_timeout_seconds,
                )
                latest = self._latest_coordinate_report(reports)

                report_count_metric.add_metric(label_values, len(reports))

                if latest is None:
                    scrape_success_metric.add_metric(label_values, 0)
                    continue

                latitude_metric.add_metric(label_values, latest["latitude"])
                longitude_metric.add_metric(label_values, latest["longitude"])
                altitude_metric.add_metric(label_values, latest["altitude"])
                timestamp_metric.add_metric(label_values, latest["time"])
                status_metric.add_metric(label_values, latest["status"])
                own_report_metric.add_metric(label_values, 1 if latest["is_own_report"] else 0)
                age_metric.add_metric(label_values, max(0.0, now - latest["time"]))
                scrape_success_metric.add_metric(label_values, 1)
            except Exception as exc:
                logging.exception("Failed scraping device '%s' (%s): %s", device_name, device_id, exc)
                report_count_metric.add_metric(label_values, 0)
                scrape_success_metric.add_metric(label_values, 0)

        yield latitude_metric
        yield longitude_metric
        yield altitude_metric
        yield timestamp_metric
        yield status_metric
        yield own_report_metric
        yield age_metric
        yield report_count_metric
        yield scrape_success_metric


def main():
    host = os.getenv("EXPORTER_HOST", "0.0.0.0")
    port = int(os.getenv("EXPORTER_PORT", "9824"))
    timeout_seconds = float(os.getenv("LOCATION_TIMEOUT_SECONDS", "30"))
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()

    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format="%(asctime)s %(levelname)s %(message)s",
    )

    collector = FindMyToolsCollector(location_timeout_seconds=timeout_seconds)
    REGISTRY.register(collector)

    start_http_server(port=port, addr=host)
    logging.info("Prometheus exporter started on http://%s:%d/metrics", host, port)

    while True:
        time.sleep(3600)


if __name__ == "__main__":
    main()
