#!/usr/bin/env python3
"""TechFlow host observer.

The observer stores only allow-listed health, metric, and alert fields. It never
stores raw application log lines, flow payloads, identifiers, or credentials.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from typing import Any


SERVICES = ("postgres", "redis", "app", "worker", "event-gateway", "ingress")
STATE_DIR = pathlib.Path(os.getenv("TECHFLOW_OBSERVER_STATE_DIR", "/var/lib/ablestack-techflow/observability"))
LOG_DIR = pathlib.Path(os.getenv("TECHFLOW_OBSERVER_LOG_DIR", "/var/log/ablestack-techflow/observability"))
NOW = dt.datetime.now(dt.timezone.utc)


def run(command: list[str], *, input_text: str | None = None, timeout: int = 20) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        input=input_text,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )


def compose(*args: str, input_text: str | None = None, timeout: int = 20) -> subprocess.CompletedProcess[str]:
    return run(["docker", "compose", "--env-file", ".env", *args], input_text=input_text, timeout=timeout)


def iso_now() -> str:
    return NOW.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def atomic_json(path: pathlib.Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temp_name, 0o640)
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def atomic_text(path: pathlib.Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(value)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temp_name, 0o640)
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def http_probe(url: str, name: str) -> dict[str, Any]:
    started = time.monotonic()
    status = 0
    error = "none"
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "techflow-observer/1"})
        with urllib.request.urlopen(request, timeout=5) as response:
            status = int(response.status)
    except urllib.error.HTTPError as exc:
        status = int(exc.code)
        error = "http_error"
    except (urllib.error.URLError, TimeoutError, OSError):
        error = "connection_error"
    return {
        "name": name,
        "up": status == 200,
        "http_status": status,
        "duration_ms": round((time.monotonic() - started) * 1000),
        "error": error,
    }


def disk_and_memory() -> dict[str, Any]:
    disk = shutil.disk_usage("/")
    memory: dict[str, int] = {}
    with open("/proc/meminfo", encoding="utf-8") as stream:
        for line in stream:
            key, value = line.split(":", 1)
            memory[key] = int(value.strip().split()[0]) * 1024
    with open("/proc/uptime", encoding="utf-8") as stream:
        uptime = int(float(stream.read().split()[0]))
    return {
        "disk_total_bytes": disk.total,
        "disk_used_bytes": disk.used,
        "disk_available_bytes": disk.free,
        "disk_used_ratio": round(disk.used / disk.total, 6),
        "memory_total_bytes": memory.get("MemTotal", 0),
        "memory_available_bytes": memory.get("MemAvailable", 0),
        "memory_available_ratio": round(memory.get("MemAvailable", 0) / max(memory.get("MemTotal", 1), 1), 6),
        "uptime_seconds": uptime,
    }


def collect_services() -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for service in SERVICES:
        container = compose("ps", "-q", service).stdout.strip()
        state = "missing"
        health = "missing"
        restarts = 0
        if container:
            inspected = run(
                ["docker", "inspect", "--format", "{{.State.Status}}|{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}|{{.RestartCount}}", container]
            )
            if inspected.returncode == 0:
                parts = inspected.stdout.strip().split("|")
                if len(parts) == 3:
                    state, health, restart_text = parts
                    restarts = int(restart_text or 0)
        result.append(
            {
                "service": service,
                "state": state,
                "health": health,
                "healthy": state == "running" and health == "healthy",
                "restart_count": restarts,
            }
        )
    return result


def parse_key_values(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in text.splitlines():
        if ":" in line and not line.startswith("#"):
            key, value = line.split(":", 1)
            values[key] = value
    return values


def load_public_settings() -> dict[str, str]:
    """Load only non-secret observer settings from the deployment environment."""
    allowed = {
        "AP_BIND_ADDRESS": "172.16.0.231",
        "AP_HTTP_PORT": "8080",
        "TECHFLOW_PUBLIC_URL": "",
        "TECHFLOW_BACKUP_DIR": "/var/backups/ablestack-techflow/state",
    }
    path = pathlib.Path(".env")
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line or line.lstrip().startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            if key in allowed:
                allowed[key] = value.strip().strip('"').strip("'")
    for key in allowed:
        if key in os.environ:
            allowed[key] = os.environ[key]
    return allowed


def collect_redis() -> dict[str, Any]:
    command = compose(
        "exec",
        "-T",
        "redis",
        "sh",
        "-c",
        'REDISCLI_AUTH="$AP_REDIS_PASSWORD" redis-cli --raw INFO',
    )
    if command.returncode != 0:
        return {"up": False}
    values = parse_key_values(command.stdout)

    def number(key: str) -> int:
        try:
            return int(values.get(key, "0"))
        except ValueError:
            return 0

    return {
        "up": True,
        "connected_clients": number("connected_clients"),
        "blocked_clients": number("blocked_clients"),
        "used_memory_bytes": number("used_memory"),
        "used_memory_peak_bytes": number("used_memory_peak"),
        "rejected_connections": number("rejected_connections"),
        "instantaneous_ops_per_sec": number("instantaneous_ops_per_sec"),
        "rdb_last_bgsave_status": values.get("rdb_last_bgsave_status", "unknown"),
        "aof_enabled": number("aof_enabled"),
        "aof_last_bgrewrite_status": values.get("aof_last_bgrewrite_status", "unknown"),
    }


def psql(sql: str) -> subprocess.CompletedProcess[str]:
    return compose(
        "exec",
        "-T",
        "postgres",
        "sh",
        "-c",
        'psql -X -q -U "$POSTGRES_USER" -d "$POSTGRES_DB" -At -F "|"',
        input_text=sql,
    )


def collect_database() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    summary = psql(
        """
SELECT pg_database_size(current_database()),
       (SELECT count(*) FROM pg_stat_activity WHERE datname = current_database()),
       current_setting('max_connections')::int;
"""
    )
    if summary.returncode != 0 or not summary.stdout.strip():
        return {"up": False}, []
    try:
        database_bytes, connections, max_connections = [int(part) for part in summary.stdout.strip().split("|")]
    except (ValueError, TypeError):
        return {"up": False}, []

    flows = psql(
        """
SELECT '15m', status::text, count(*)
FROM flow_run
WHERE "created" >= now() - interval '15 minutes'
GROUP BY status
UNION ALL
SELECT '24h', status::text, count(*)
FROM flow_run
WHERE "created" >= now() - interval '24 hours'
GROUP BY status
ORDER BY 1, 2;
"""
    )
    flow_counts: list[dict[str, Any]] = []
    if flows.returncode == 0:
        for line in flows.stdout.splitlines():
            parts = line.split("|")
            if len(parts) == 3 and re.fullmatch(r"[A-Z_]+", parts[1]):
                flow_counts.append({"window": parts[0], "status": parts[1], "count": int(parts[2])})

    durations = psql(
        """
SELECT COALESCE(round(avg(extract(epoch FROM ("finishTime" - "startTime")) * 1000))::bigint, 0),
       COALESCE(round(percentile_cont(0.95) WITHIN GROUP
         (ORDER BY extract(epoch FROM ("finishTime" - "startTime")) * 1000))::bigint, 0)
FROM flow_run
WHERE "created" >= now() - interval '24 hours'
  AND "startTime" IS NOT NULL
  AND "finishTime" IS NOT NULL;
"""
    )
    avg_ms = p95_ms = 0
    if durations.returncode == 0 and durations.stdout.strip():
        try:
            avg_ms, p95_ms = [int(part) for part in durations.stdout.strip().split("|")]
        except (ValueError, TypeError):
            pass
    return {
        "up": True,
        "database_bytes": database_bytes,
        "connections": connections,
        "max_connections": max_connections,
        "connection_ratio": round(connections / max(max_connections, 1), 6),
        "flow_duration_24h_avg_ms": avg_ms,
        "flow_duration_24h_p95_ms": p95_ms,
    }, flow_counts


def collect_backup() -> dict[str, Any]:
    backup_dir = pathlib.Path(load_public_settings()["TECHFLOW_BACKUP_DIR"])
    archives = sorted(backup_dir.glob("techflow-state-*.tar.gz"), key=lambda item: item.stat().st_mtime, reverse=True)
    latest_age = -1
    latest_bytes = 0
    if archives:
        latest_age = max(0, int(NOW.timestamp() - archives[0].stat().st_mtime))
        latest_bytes = archives[0].stat().st_size
    timer = run(["systemctl", "is-active", "techflow-state-backup.timer"])
    result = run(["systemctl", "show", "techflow-state-backup.service", "-p", "Result", "-p", "ExecMainStatus"])
    values = dict(line.split("=", 1) for line in result.stdout.splitlines() if "=" in line)
    return {
        "timer_active": timer.returncode == 0 and timer.stdout.strip() == "active",
        "last_result": values.get("Result", "unknown"),
        "last_exit_status": int(values.get("ExecMainStatus", "-1")),
        "latest_age_seconds": latest_age,
        "latest_bytes": latest_bytes,
    }


def count_log_events(service: str, since: str, structured: bool) -> dict[str, int]:
    container = compose("ps", "-q", service).stdout.strip()
    if not container:
        return {}
    command = run(["docker", "logs", "--since", since, container], timeout=20)
    counts: dict[str, int] = {}
    for line in (command.stdout + "\n" + command.stderr).splitlines():
        if structured:
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            level = str(record.get("level", "unknown")).lower()
            message = str(record.get("message", "unknown"))
            reason = str(record.get("reason", "none"))
            if not re.fullmatch(r"[a-z0-9_-]{1,64}", level):
                continue
            if not re.fullmatch(r"[a-z0-9_-]{1,64}", message):
                continue
            if not re.fullmatch(r"[a-z0-9_-]{1,64}", reason):
                reason = "other"
            key = f"{level}|{message}|{reason}"
            counts[key] = counts.get(key, 0) + 1
        elif re.search(r"\b(error|fatal|panic|exception|failed)\b", line, re.IGNORECASE):
            counts["error_lines"] = counts.get("error_lines", 0) + 1
    return counts


def alert(key: str, severity: str, component: str, summary: str) -> dict[str, str]:
    return {"key": key, "severity": severity, "component": component, "summary": summary}


def evaluate(snapshot: dict[str, Any]) -> list[dict[str, str]]:
    alerts: list[dict[str, str]] = []
    host = snapshot["host"]
    if host["disk_used_ratio"] >= 0.95:
        alerts.append(alert("disk_critical", "critical", "host", "Root filesystem usage is at or above 95%."))
    elif host["disk_used_ratio"] >= 0.85:
        alerts.append(alert("disk_warning", "warning", "host", "Root filesystem usage is at or above 85%."))
    if host["memory_available_ratio"] < 0.05:
        alerts.append(alert("memory_critical", "critical", "host", "Available memory is below 5%."))
    elif host["memory_available_ratio"] < 0.15:
        alerts.append(alert("memory_warning", "warning", "host", "Available memory is below 15%."))

    for service in snapshot["services"]:
        if not service["healthy"]:
            alerts.append(alert(f"service_{service['service']}", "critical", service["service"], "Service is absent, stopped, or unhealthy."))
        elif service["restart_count"] >= 3:
            alerts.append(alert(f"restarts_{service['service']}", "warning", service["service"], "Service restart count is at least 3."))

    for endpoint in snapshot["endpoints"]:
        if not endpoint["up"]:
            severity = "warning" if endpoint["name"] == "public_app" else "critical"
            alerts.append(alert(f"endpoint_{endpoint['name']}", severity, endpoint["name"], "Health endpoint did not return HTTP 200."))

    database = snapshot["database"]
    if not database.get("up"):
        alerts.append(alert("postgres_unreachable", "critical", "postgres", "PostgreSQL health and metric query failed."))
    elif database["connection_ratio"] >= 0.80:
        alerts.append(alert("postgres_connections", "warning", "postgres", "PostgreSQL connections are at or above 80%."))

    redis = snapshot["redis"]
    if not redis.get("up"):
        alerts.append(alert("redis_unreachable", "critical", "redis", "Redis health and metric query failed."))
    else:
        if redis["rejected_connections"] > 0:
            alerts.append(alert("redis_rejected_connections", "warning", "redis", "Redis reports rejected connections."))
        if redis["rdb_last_bgsave_status"] != "ok" or (redis["aof_enabled"] and redis["aof_last_bgrewrite_status"] != "ok"):
            alerts.append(alert("redis_persistence", "critical", "redis", "Redis persistence reports a failed operation."))

    backup = snapshot["backup"]
    if not backup["timer_active"] or backup["last_result"] != "success" or backup["last_exit_status"] != 0:
        alerts.append(alert("backup_scheduler", "critical", "backup", "Scheduled state backup is inactive or last execution failed."))
    if backup["latest_age_seconds"] < 0 or backup["latest_age_seconds"] > 26 * 3600:
        alerts.append(alert("backup_freshness", "critical", "backup", "Latest state backup is missing or older than 26 hours."))

    failure_statuses = {"FAILED", "TIMEOUT", "INTERNAL_ERROR"}
    flow_failures = sum(
        item["count"] for item in snapshot["flow_counts"]
        if item["window"] == "15m" and item["status"] in failure_statuses
    )
    if flow_failures >= 5:
        alerts.append(alert("flow_failures_critical", "critical", "activepieces", "At least 5 flow runs failed in the last 15 minutes."))
    elif flow_failures > 0:
        alerts.append(alert("flow_failures_warning", "warning", "activepieces", "A flow run failed in the last 15 minutes."))

    rejected = sum(
        count for key, count in snapshot["log_counts"]["event_gateway"].items()
        if "|webhook_rejected|" in key
    )
    if rejected >= 10:
        alerts.append(alert("webhook_rejections", "warning", "event-gateway", "Webhook rejections reached 10 in the last 15 minutes."))
    return sorted(alerts, key=lambda item: item["key"])


def metric_line(name: str, value: int | float, **labels: str) -> str:
    label_text = ""
    if labels:
        escaped = [f'{key}="{value.replace(chr(92), chr(92) * 2).replace(chr(34), chr(92) + chr(34))}"' for key, value in sorted(labels.items())]
        label_text = "{" + ",".join(escaped) + "}"
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        value = 0
    return f"{name}{label_text} {value}"


def render_prometheus(snapshot: dict[str, Any], alerts: list[dict[str, str]]) -> str:
    lines = [
        "# HELP techflow_observer_up TechFlow observer completed a collection.",
        "# TYPE techflow_observer_up gauge",
        metric_line("techflow_observer_up", 1),
        metric_line("techflow_host_disk_used_ratio", snapshot["host"]["disk_used_ratio"]),
        metric_line("techflow_host_memory_available_ratio", snapshot["host"]["memory_available_ratio"]),
        metric_line("techflow_host_uptime_seconds", snapshot["host"]["uptime_seconds"]),
    ]
    for item in snapshot["services"]:
        lines.append(metric_line("techflow_service_healthy", int(item["healthy"]), service=item["service"]))
        lines.append(metric_line("techflow_service_restart_count", item["restart_count"], service=item["service"]))
    for item in snapshot["endpoints"]:
        lines.append(metric_line("techflow_endpoint_up", int(item["up"]), endpoint=item["name"]))
        lines.append(metric_line("techflow_endpoint_duration_milliseconds", item["duration_ms"], endpoint=item["name"]))
    database = snapshot["database"]
    lines.append(metric_line("techflow_postgres_up", int(database.get("up", False))))
    if database.get("up"):
        lines.extend(
            [
                metric_line("techflow_postgres_database_bytes", database["database_bytes"]),
                metric_line("techflow_postgres_connections", database["connections"]),
                metric_line("techflow_postgres_max_connections", database["max_connections"]),
                metric_line("techflow_flow_duration_24h_milliseconds", database["flow_duration_24h_avg_ms"], quantile="avg"),
                metric_line("techflow_flow_duration_24h_milliseconds", database["flow_duration_24h_p95_ms"], quantile="p95"),
            ]
        )
    for item in snapshot["flow_counts"]:
        lines.append(metric_line("techflow_flow_runs", item["count"], window=item["window"], status=item["status"]))
    redis = snapshot["redis"]
    lines.append(metric_line("techflow_redis_up", int(redis.get("up", False))))
    if redis.get("up"):
        for key in ("connected_clients", "blocked_clients", "used_memory_bytes", "used_memory_peak_bytes", "rejected_connections", "instantaneous_ops_per_sec"):
            lines.append(metric_line(f"techflow_redis_{key}", redis[key]))
    backup = snapshot["backup"]
    lines.append(metric_line("techflow_backup_timer_active", int(backup["timer_active"])))
    lines.append(metric_line("techflow_backup_latest_age_seconds", backup["latest_age_seconds"]))
    lines.append(metric_line("techflow_backup_latest_bytes", backup["latest_bytes"]))
    for source, counts in snapshot["log_counts"].items():
        for key, count in counts.items():
            if source == "event_gateway":
                level, message, reason = key.split("|", 2)
                lines.append(metric_line("techflow_log_events_15m", count, source=source, level=level, event=message, reason=reason))
            else:
                lines.append(metric_line("techflow_log_error_lines_15m", count, source=source))
    for severity in ("warning", "critical"):
        lines.append(metric_line("techflow_active_alerts", sum(1 for item in alerts if item["severity"] == severity), severity=severity))
    return "\n".join(lines) + "\n"


def update_alert_transitions(current: list[dict[str, str]], *, drill_id: str | None) -> None:
    previous_path = STATE_DIR / "current-alerts.json"
    previous: list[dict[str, Any]] = []
    if previous_path.exists():
        try:
            previous = json.loads(previous_path.read_text(encoding="utf-8")).get("alerts", [])
        except (json.JSONDecodeError, OSError):
            previous = []
    previous_by_key = {item["key"]: item for item in previous}
    current_by_key = {item["key"]: item for item in current}
    transitions: list[dict[str, Any]] = []
    for key in sorted(current_by_key.keys() - previous_by_key.keys()):
        item = current_by_key[key]
        transitions.append({"time": iso_now(), "transition": "opened", **item, **({"drill_id": drill_id} if drill_id else {})})
    for key in sorted(previous_by_key.keys() - current_by_key.keys()):
        item = previous_by_key[key]
        transitions.append({"time": iso_now(), "transition": "resolved", "key": key, "severity": item["severity"], "component": item["component"], "summary": item["summary"], **({"drill_id": drill_id} if drill_id else {})})
    if transitions:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        with (LOG_DIR / "alerts.jsonl").open("a", encoding="utf-8") as stream:
            for item in transitions:
                line = json.dumps(item, ensure_ascii=False, sort_keys=True)
                stream.write(line + "\n")
                print(line)
        os.chmod(LOG_DIR / "alerts.jsonl", 0o640)
    atomic_json(previous_path, {"generated_at": iso_now(), "alerts": current})


def collect(drill_id: str | None) -> tuple[dict[str, Any], list[dict[str, str]]]:
    host = disk_and_memory()
    settings = load_public_settings()
    bind = settings["AP_BIND_ADDRESS"]
    port = settings["AP_HTTP_PORT"]
    public_url = settings["TECHFLOW_PUBLIC_URL"].rstrip("/")
    endpoints = [
        http_probe(f"http://{bind}:{port}/api/v1/health", "internal_app"),
        http_probe(f"http://{bind}:{port}/techflow/hooks/healthz", "internal_gateway"),
    ]
    if public_url:
        endpoints.append(http_probe(f"{public_url}/api/v1/health", "public_app"))
    database, flow_counts = collect_database()
    snapshot = {
        "schema_version": 1,
        "generated_at": iso_now(),
        **({"drill_id": drill_id} if drill_id else {}),
        "host": host,
        "services": collect_services(),
        "endpoints": endpoints,
        "database": database,
        "flow_counts": flow_counts,
        "redis": collect_redis(),
        "backup": collect_backup(),
        "log_counts": {
            "event_gateway": count_log_events("event-gateway", "15m", True),
            "app": count_log_events("app", "15m", False),
            "worker": count_log_events("worker", "15m", False),
        },
    }
    alerts = evaluate(snapshot)
    update_alert_transitions(alerts, drill_id=drill_id)
    atomic_json(STATE_DIR / "status.json", {**snapshot, "alert_summary": {
        "warning": sum(1 for item in alerts if item["severity"] == "warning"),
        "critical": sum(1 for item in alerts if item["severity"] == "critical"),
    }})
    atomic_text(STATE_DIR / "metrics.prom", render_prometheus(snapshot, alerts))
    return snapshot, alerts


def print_status() -> int:
    try:
        status = json.loads((STATE_DIR / "status.json").read_text(encoding="utf-8"))
        alerts = json.loads((STATE_DIR / "current-alerts.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        print("observer=unknown reason=status_unavailable")
        return 1
    summary = status["alert_summary"]
    print(
        f"observer=ready generated_at={status['generated_at']} "
        f"critical={summary['critical']} warning={summary['warning']} "
        f"services_healthy={sum(1 for item in status['services'] if item['healthy'])}/{len(status['services'])}"
    )
    for item in alerts["alerts"]:
        print(f"alert={item['key']} severity={item['severity']} component={item['component']}")
    return 2 if summary["critical"] else 0


def notify(source: str) -> int:
    try:
        alerts = json.loads((STATE_DIR / "current-alerts.json").read_text(encoding="utf-8")).get("alerts", [])
    except (OSError, json.JSONDecodeError):
        alerts = []
    record = {
        "time": iso_now(),
        "event": "observer_notification",
        "source": re.sub(r"[^a-zA-Z0-9_.@:-]", "_", source)[:128],
        "critical": sum(1 for item in alerts if item.get("severity") == "critical"),
        "warning": sum(1 for item in alerts if item.get("severity") == "warning"),
    }
    print(json.dumps(record, sort_keys=True))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="ABLESTACK TechFlow host observer")
    subparsers = parser.add_subparsers(dest="command", required=True)
    collect_parser = subparsers.add_parser("collect")
    collect_parser.add_argument("--strict", action="store_true")
    collect_parser.add_argument("--drill-id")
    subparsers.add_parser("status")
    notify_parser = subparsers.add_parser("notify")
    notify_parser.add_argument("--source", required=True)
    args = parser.parse_args()
    if args.command == "status":
        return print_status()
    if args.command == "notify":
        return notify(args.source)
    _, alerts = collect(args.drill_id)
    critical = sum(1 for item in alerts if item["severity"] == "critical")
    warning = sum(1 for item in alerts if item["severity"] == "warning")
    print(f"observer=collected critical={critical} warning={warning}")
    return 2 if args.strict and critical else 0


if __name__ == "__main__":
    sys.exit(main())
