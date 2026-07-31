#!/usr/bin/env python3

import importlib.util
import os
import pathlib
import tempfile
import unittest
from unittest import mock


MODULE_PATH = pathlib.Path(__file__).with_name("observer.py")
SPEC = importlib.util.spec_from_file_location("techflow_observer", MODULE_PATH)
assert SPEC and SPEC.loader
observer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(observer)


def snapshot():
    return {
        "host": {"disk_used_ratio": 0.25, "memory_available_ratio": 0.60, "uptime_seconds": 1},
        "services": [
            {"service": name, "healthy": True, "restart_count": 0}
            for name in observer.SERVICES
        ],
        "endpoints": [
            {"name": "internal_app", "up": True, "duration_ms": 1},
            {"name": "internal_gateway", "up": True, "duration_ms": 1},
            {"name": "public_app", "up": True, "duration_ms": 1},
        ],
        "database": {
            "up": True,
            "connection_ratio": 0.10,
            "database_bytes": 1,
            "connections": 1,
            "max_connections": 10,
            "flow_duration_24h_avg_ms": 0,
            "flow_duration_24h_p95_ms": 0,
        },
        "flow_counts": [],
        "redis": {
            "up": True,
            "rejected_connections": 0,
            "rdb_last_bgsave_status": "ok",
            "aof_enabled": 1,
            "aof_last_bgrewrite_status": "ok",
            "connected_clients": 1,
            "blocked_clients": 0,
            "used_memory_bytes": 1,
            "used_memory_peak_bytes": 1,
            "instantaneous_ops_per_sec": 1,
        },
        "backup": {
            "timer_active": True,
            "last_result": "success",
            "last_exit_status": 0,
            "latest_age_seconds": 60,
            "latest_bytes": 1,
        },
        "log_counts": {"event_gateway": {}, "app": {}, "worker": {}},
    }


class ObserverTests(unittest.TestCase):
    def test_healthy_snapshot_has_no_alert(self):
        self.assertEqual(observer.evaluate(snapshot()), [])

    def test_service_failure_is_critical(self):
        value = snapshot()
        value["services"][0]["healthy"] = False
        alerts = observer.evaluate(value)
        self.assertEqual(alerts[0]["key"], "service_postgres")
        self.assertEqual(alerts[0]["severity"], "critical")

    def test_public_endpoint_failure_is_warning(self):
        value = snapshot()
        value["endpoints"][2]["up"] = False
        alerts = observer.evaluate(value)
        self.assertEqual(alerts[0]["key"], "endpoint_public_app")
        self.assertEqual(alerts[0]["severity"], "warning")

    def test_flow_failure_threshold(self):
        value = snapshot()
        value["flow_counts"] = [{"window": "15m", "status": "FAILED", "count": 5}]
        alerts = observer.evaluate(value)
        self.assertEqual(alerts[0]["key"], "flow_failures_critical")

    def test_prometheus_contains_only_allow_listed_service_label(self):
        value = snapshot()
        text = observer.render_prometheus(value, [])
        self.assertIn('techflow_service_healthy{service="postgres"} 1', text)
        self.assertNotIn("password", text.lower())

    def test_public_settings_ignore_secret_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            previous = pathlib.Path.cwd()
            try:
                os.chdir(directory)
                pathlib.Path(".env").write_text(
                    "TECHFLOW_PUBLIC_URL=https://example.test\n"
                    "AP_POSTGRES_PASSWORD=must-not-be-loaded\n",
                    encoding="utf-8",
                )
                with mock.patch.dict(os.environ, {}, clear=True):
                    settings = observer.load_public_settings()
            finally:
                os.chdir(previous)
        self.assertEqual(settings["TECHFLOW_PUBLIC_URL"], "https://example.test")
        self.assertNotIn("AP_POSTGRES_PASSWORD", settings)

    def test_atomic_json_permissions(self):
        if os.name == "nt":
            self.skipTest("POSIX mode bits are verified on the Ubuntu target.")
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "status.json"
            observer.atomic_json(path, {"ready": True})
            self.assertEqual(path.stat().st_mode & 0o777, 0o640)


if __name__ == "__main__":
    unittest.main()
