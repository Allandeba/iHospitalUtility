"""Private, fixed-target iHospitalUtility monitor (Python standard library only)."""
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from http.client import HTTPConnection, HTTPException, HTTPSConnection
import json
import os
from pathlib import Path
import signal
import sys
import socket
import ssl
import time
from urllib.parse import urlsplit


HOST = "ihospitalutility.allandeba.dev.br"
TIMEOUT_SECONDS = 5
MAX_BODY_BYTES = 256 * 1024
CHECK_PATHS = {
    "home": "/",
    "blazor": "/_framework/blazor.boot.json",
    "pwa": "/service-worker-assets.js",
}


@dataclass(frozen=True)
class CheckResult:
    check: str
    success: int
    http_status: int
    duration: float
    error_code: str


def valid_content(check, body):
    if check == "home":
        return b"blazor.webassembly.js" in body
    if check == "pwa":
        return b"self.assetsManifest" in body
    try:
        document = json.loads(body)
    except (ValueError, UnicodeError, RecursionError):
        return False
    resources = document.get("resources") if isinstance(document, dict) else None
    return isinstance(resources, dict) and any(
        isinstance(resources.get(key), dict) for key in ("runtime", "assembly")
    )


@contextmanager
def request_deadline(seconds):
    """Linux/main-thread deadline, including DNS, TLS and slow response bodies."""
    def expired(_signum, _frame):
        raise TimeoutError

    previous_handler = signal.signal(signal.SIGALRM, expired)
    previous_timer = signal.setitimer(signal.ITIMER_REAL, seconds)
    start = time.monotonic()
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous_handler)
        if previous_timer[0]:
            remaining = max(0.000001, previous_timer[0] - (time.monotonic() - start))
            signal.setitimer(signal.ITIMER_REAL, remaining, previous_timer[1])


def run_check(check):
    """Probe an allowlisted check, never an application-supplied URL."""
    path = CHECK_PATHS[check]
    start = time.monotonic()
    connection = None
    status = 0
    code = "network"
    try:
        with request_deadline(TIMEOUT_SECONDS):
            connection = HTTPSConnection(HOST, timeout=TIMEOUT_SECONDS,
                                         context=ssl.create_default_context())
            connection.request("GET", path, headers={"Accept-Encoding": "identity"})
            response = connection.getresponse()
            status = response.status
            if status != 200:
                code = "http"  # http.client never follows redirects.
            else:
                body = response.read(MAX_BODY_BYTES + 1)
                good = len(body) <= MAX_BODY_BYTES and valid_content(check, body)
                code = "ok" if good else "content"
    except ssl.SSLError:
        code = "tls"
    except (OSError, HTTPException):
        code = "network"
    finally:
        if connection is not None:
            connection.close()
    return CheckResult(check, int(code == "ok"), status, time.monotonic() - start, code)


def read_tls_expiry():
    """Return the verified public leaf certificate's expiry, or zero (unknown)."""
    try:
        with request_deadline(TIMEOUT_SECONDS):
            context = ssl.create_default_context()
            with socket.create_connection((HOST, 443), timeout=TIMEOUT_SECONDS) as raw:
                with context.wrap_socket(raw, server_hostname=HOST) as tls:
                    certificate = tls.getpeercert() or {}
                    not_after = certificate.get("notAfter")
                    return ssl.cert_time_to_seconds(not_after) if isinstance(not_after, str) else 0
    except (OSError, ValueError, KeyError, TypeError):
        return 0


def metrics_payload(results, tls_expiry, now_ns):
    """OTLP/HTTP JSON gauges; metric names carry units to avoid suffix duplication."""
    def point(value, check=None):
        return {
            "attributes": ([] if check is None else [
                {"key": "check", "value": {"stringValue": check}}
            ]),
            "timeUnixNano": str(now_ns),
            "asDouble": float(value),
        }

    metrics = []
    for name, field in (
        ("ihospital_probe_success", "success"),
        ("ihospital_probe_duration_seconds", "duration"),
        ("ihospital_probe_http_status_code", "http_status"),
        ("ihospital_probe_last_run_timestamp_seconds", None),
    ):
        metrics.append({"name": name, "unit": "", "gauge": {"dataPoints": [
            point(getattr(result, field) if field else now_ns / 1_000_000_000, result.check)
            for result in results
        ]}})
    metrics.append({
        "name": "ihospital_probe_tls_cert_expiry_timestamp_seconds", "unit": "",
        "gauge": {"dataPoints": [point(tls_expiry)]},
    })
    return {"resourceMetrics": [{
        "resource": {"attributes": [
            {"key": "service.name", "value": {"stringValue": "ihospitalutility-monitor"}},
            {"key": "deployment.environment.name", "value": {"stringValue": "production"}},
        ]},
        "scopeMetrics": [{"scope": {"name": "ihospitalutility-monitor"}, "metrics": metrics}],
    }]}


def send_json(endpoint, payload, *, otlp=False):
    """One bounded POST, no redirects, proxies, cookies, retries or response logging."""
    connection = None
    response = None
    try:
        with request_deadline(TIMEOUT_SECONDS):
            target = urlsplit(endpoint)
            if (target.scheme not in ("http", "https") or not target.hostname
                    or target.username is not None or target.password is not None
                    or target.query or target.fragment):
                return "content"
            if target.scheme == "https":
                connection = HTTPSConnection(target.hostname, target.port, timeout=TIMEOUT_SECONDS,
                                             context=ssl.create_default_context())
            else:
                connection = HTTPConnection(target.hostname, target.port, timeout=TIMEOUT_SECONDS)
            connection.request("POST", target.path or "/",
                               body=json.dumps(payload, separators=(",", ":"), allow_nan=False).encode(),
                               headers={"Content-Type": "application/json", "Accept-Encoding": "identity"})
            response = connection.getresponse()
            if not 200 <= response.status < 300:
                return "http"
            body = response.read(MAX_BODY_BYTES + 1)
            if len(body) > MAX_BODY_BYTES:
                return "content"
            if otlp and body:
                document = json.loads(body)
                if not isinstance(document, dict):
                    return "content"
                partial = document.get("partialSuccess", {})
                if not isinstance(partial, dict) or int(partial.get("rejectedDataPoints", 0)) != 0:
                    return "content"
            return "ok"
    except ssl.SSLError:
        return "tls"
    except (OSError, HTTPException):
        return "network"
    except (ValueError, TypeError, UnicodeError, RecursionError):
        return "content"
    finally:
        if response is not None:
            response.close()
        if connection is not None:
            connection.close()


HEARTBEAT_PATH = Path('/run/monitor/heartbeat')


def heartbeat_fresh():
    try:
        age = time.time() - HEARTBEAT_PATH.stat().st_mtime
        return HEARTBEAT_PATH.is_file() and 0 <= age <= 180
    except OSError:
        return False


def run_cycle():
    results = [run_check(check) for check in CHECK_PATHS]
    expiry = read_tls_expiry()
    now_ns = time.time_ns()
    metrics = send_json(os.environ['METRICS_ENDPOINT'],
                        metrics_payload(results, expiry, now_ns), otlp=True)
    heartbeat = 'stale'
    if metrics == 'ok':
        try:
            HEARTBEAT_PATH.write_text(str(now_ns / 1_000_000_000))
            heartbeat = 'ok'
        except OSError:
            heartbeat = 'write_error'
    logs = send_json(os.environ['LOGS_ENDPOINT'], {'streams': [{
        'stream': {'service_name': 'ihospitalutility-monitor',
                   'deployment_environment_name': 'production'},
        'values': [[str(now_ns), json.dumps({'checks': [asdict(r) for r in results]},
                                           separators=(',', ':'), allow_nan=False)]],
    }]})
    print(json.dumps({'metrics_export': metrics, 'logs_export': logs,
                      'heartbeat': heartbeat}), flush=True)


def run_forever():
    while True:
        started = time.monotonic()
        try:
            run_cycle()
        except (OSError, HTTPException):
            print(json.dumps({'cycle': 'network'}), flush=True)
        time.sleep(max(0, 60 - (time.monotonic() - started)))


if __name__ == '__main__':
    if sys.argv[1:] == ['--healthcheck']:
        sys.exit(0 if heartbeat_fresh() else 1)
    if sys.argv[1:]:
        sys.exit('Usage: python -m monitoring.probe [--healthcheck]')
    for name in ('METRICS_ENDPOINT', 'LOGS_ENDPOINT'):
        if not os.environ.get(name):
            sys.exit('Missing required endpoint: ' + name)
    run_forever()
