"""Offline contract tests; HTTP traffic stays on a loopback test server."""
import contextlib
import http.client
import http.server
import importlib
import importlib.util
import io
import json
import ssl
import threading
import unittest
from unittest import mock


class LocalHTTP(unittest.TestCase):
    def setUp(self):
        self.routes = {}
        self.requests = []
        owner = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                owner.requests.append((self.command, self.path, dict(self.headers), b""))
                self.respond()

            def do_POST(self):
                body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
                owner.requests.append((self.command, self.path, dict(self.headers), body))
                self.respond()

            def respond(self):
                status, body, headers = owner.routes.get(self.path, (404, b"", {}))
                self.send_response(status)
                for name, value in headers.items():
                    self.send_header(name, value)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                try:
                    self.wfile.write(body)
                except (BrokenPipeError, ConnectionResetError):
                    pass

            def log_message(self, *_args):
                pass

        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.daemon_threads = True
        self.thread = threading.Thread(target=self.server.serve_forever,
                                       kwargs={"poll_interval": 0.01}, daemon=True)
        self.thread.start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.thread.join, 2)
        self.addCleanup(self.server.shutdown)

    def module(self):
        self.assertIsNotNone(importlib.util.find_spec("monitoring.probe"),
                             "monitoring.probe must implement the fixed HTTP monitor")
        return importlib.import_module("monitoring.probe")

    def local_https(self, host, port=None, *, timeout, context):
        self.assertEqual(host, "ihospitalutility.allandeba.dev.br")
        self.assertIn(port, (None, 443))
        self.assertEqual(timeout, 5)
        self.assertTrue(context.check_hostname)
        self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
        return http.client.HTTPConnection("127.0.0.1", self.server.server_port,
                                          timeout=timeout)

    def test_home_checks_fixed_https_url_without_cookies(self):
        probe = self.module()
        self.routes["/"] = (200, b'<script src="_framework/blazor.webassembly.js"></script>',
                            {"Set-Cookie": "private_cookie=SECRET"})
        with mock.patch.object(probe, "HTTPSConnection", side_effect=self.local_https):
            result = probe.run_check("home")
        self.assertEqual((result.check, result.success, result.http_status, result.error_code),
                         ("home", 1, 200, "ok"))
        self.assertGreaterEqual(result.duration, 0)
        self.assertEqual([(r[0], r[1]) for r in self.requests], [("GET", "/")])
        self.assertNotIn("Cookie", self.requests[0][2])

    def test_all_three_checks_validate_content_without_dynamic_urls(self):
        probe = self.module()
        cases = [
            ("home", "/", b"blazor.webassembly.js", 1),
            ("home", "/", b"<html>login SECRET</html>", 0),
            ("blazor", "/_framework/blazor.boot.json", b'{"resources":{"runtime":{}}}', 1),
            ("blazor", "/_framework/blazor.boot.json", b'{"resources":{"assembly":{}}}', 1),
            ("blazor", "/_framework/blazor.boot.json", b'{"resources":{}}', 0),
            ("blazor", "/_framework/blazor.boot.json", b'{"resources":{"runtime":null}}', 0),
            ("blazor", "/_framework/blazor.boot.json", b'[]', 0),
            ("blazor", "/_framework/blazor.boot.json", b'not JSON SECRET', 0),
            ("pwa", "/service-worker-assets.js", b'self.assetsManifest = {"assets": []};', 1),
            ("pwa", "/service-worker-assets.js", b'<html>fallback</html>', 0),
        ]
        with mock.patch.object(probe, "HTTPSConnection", side_effect=self.local_https):
            for check, path, body, success in cases:
                with self.subTest(check=check, body=body):
                    self.routes[path] = (200, body, {})
                    result = probe.run_check(check)
                    self.assertEqual((result.success, result.error_code),
                                     (success, "ok" if success else "content"))
                    self.assertEqual(self.requests[-1][1], path)
            calls = len(self.requests)
            with self.assertRaises(KeyError):
                probe.run_check("https://private.invalid/token?SECRET")
            self.assertEqual(len(self.requests), calls)
        self.assertEqual(set(probe.CHECK_PATHS), {"home", "blazor", "pwa"})

    def test_rejects_redirects_http_errors_and_oversized_content(self):
        probe = self.module()
        cases = [(201, b"blazor.webassembly.js", "http"),
                 (204, b"", "http"), (301, b"", "http"), (302, b"", "http"), (307, b"", "http"),
                 (500, b"SECRET", "http"),
                 (200, b"blazor.webassembly.js" + b"x" * probe.MAX_BODY_BYTES, "content")]
        with mock.patch.object(probe, "HTTPSConnection", side_effect=self.local_https):
            for status, body, code in cases:
                with self.subTest(status=status, code=code):
                    self.routes["/"] = (status, body, {"Location": "https://external.invalid/SECRET"})
                    result = probe.run_check("home")
                    self.assertEqual((result.success, result.http_status, result.error_code),
                                     (0, status, code))
        self.assertEqual(len(self.requests), len(cases))
        self.assertTrue(all(request[1] == "/" for request in self.requests))
        response = mock.MagicMock(status=200)
        response.read.return_value = b"x" * (probe.MAX_BODY_BYTES + 1)
        connection = mock.MagicMock()
        connection.getresponse.return_value = response
        with mock.patch.object(probe, "HTTPSConnection", return_value=connection):
            self.assertEqual(probe.run_check("home").error_code, "content")
        response.read.assert_called_once_with(256 * 1024 + 1)
        connection.close.assert_called_once()

    def test_network_and_tls_failures_have_only_bounded_codes(self):
        probe = self.module()
        for failure, code in [(OSError("SECRET url?token=x"), "network"),
                              (TimeoutError("SECRET slow"), "network"),
                              (ssl.SSLCertVerificationError("SECRET bad cert"), "tls")]:
            with self.subTest(code=code), mock.patch.object(probe, "HTTPSConnection", side_effect=failure):
                result = probe.run_check("home")
                self.assertEqual((result.success, result.http_status, result.error_code), (0, 0, code))
                self.assertNotIn("SECRET", repr(result))

    def test_real_network_failure_is_sanitized(self):
        probe = self.module()
        self.server.shutdown()
        self.server.server_close()
        with mock.patch.object(probe, "HTTPSConnection", side_effect=self.local_https):
            result = probe.run_check("home")
        self.assertEqual((result.success, result.http_status, result.error_code), (0, 0, "network"))

    def test_deadline_bounds_entire_request_not_each_read(self):
        probe = self.module()
        self.assertTrue(callable(getattr(probe, "request_deadline", None)),
                        "a wall-clock deadline is required, not only socket timeout")
        import time
        start = time.monotonic()
        with self.assertRaises(TimeoutError):
            with probe.request_deadline(0.05):
                time.sleep(1)
        self.assertLess(time.monotonic() - start, 0.5)
        with mock.patch.object(probe, "request_deadline", wraps=probe.request_deadline) as deadline:
            with mock.patch.object(probe, "HTTPSConnection", side_effect=TimeoutError("SECRET")):
                self.assertEqual(probe.run_check("home").error_code, "network")
        deadline.assert_called_once_with(5)

    def test_tls_expiry_uses_verified_public_certificate_of_fixed_host(self):
        probe = self.module()
        self.assertTrue(callable(getattr(probe, "read_tls_expiry", None)))
        context = mock.MagicMock()
        tls = context.wrap_socket.return_value.__enter__.return_value
        tls.getpeercert.return_value = {"notAfter": "Jan  1 00:00:00 2030 GMT"}
        with mock.patch.object(probe.ssl, "create_default_context", return_value=context) as factory:
            with mock.patch.object(probe.socket, "create_connection") as connect:
                expiry = probe.read_tls_expiry()
        factory.assert_called_once_with()
        connect.assert_called_once_with(("ihospitalutility.allandeba.dev.br", 443), timeout=5)
        context.wrap_socket.assert_called_once_with(connect.return_value.__enter__.return_value,
                                                   server_hostname="ihospitalutility.allandeba.dev.br")
        self.assertEqual(expiry, ssl.cert_time_to_seconds("Jan  1 00:00:00 2030 GMT"))

    def test_tls_expiry_failure_exports_unknown_zero_without_exception_text(self):
        probe = self.module()
        self.assertTrue(callable(getattr(probe, "read_tls_expiry", None)))
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            with mock.patch.object(probe.socket, "create_connection",
                                   side_effect=ssl.SSLCertVerificationError("SECRET")):
                self.assertEqual(probe.read_tls_expiry(), 0)
        self.assertEqual(output.getvalue(), "")

    def test_otlp_payload_preserves_exact_metric_names_and_has_no_private_data(self):
        probe = self.module()
        self.assertTrue(callable(getattr(probe, "metrics_payload", None)))
        results = [probe.CheckResult("home", 1, 200, 0.125, "ok"),
                   probe.CheckResult("blazor", 0, 503, 0.25, "http"),
                   probe.CheckResult("pwa", 0, 0, 5.0, "network")]
        now_ns = 1_800_000_000_123_456_789
        payload = probe.metrics_payload(results, 1_900_000_000, now_ns)
        resource = payload["resourceMetrics"][0]
        self.assertEqual(resource["resource"]["attributes"], [
            {"key": "service.name", "value": {"stringValue": "ihospitalutility-monitor"}},
            {"key": "deployment.environment.name", "value": {"stringValue": "production"}},
        ])
        metrics = resource["scopeMetrics"][0]["metrics"]
        names = {metric["name"] for metric in metrics}
        self.assertEqual(names, {"ihospital_probe_success", "ihospital_probe_duration_seconds",
                                 "ihospital_probe_http_status_code",
                                 "ihospital_probe_last_run_timestamp_seconds",
                                 "ihospital_probe_tls_cert_expiry_timestamp_seconds"})
        for metric in metrics:
            # Names already include seconds: an OTLP unit must not append another suffix.
            self.assertEqual(metric.get("unit", ""), "")
            points = metric["gauge"]["dataPoints"]
            if "tls_cert_expiry" in metric["name"]:
                self.assertEqual(len(points), 1)
                self.assertEqual(points[0]["asDouble"], 1_900_000_000)
            else:
                self.assertEqual(len(points), 3)
                self.assertEqual({p["attributes"][0]["value"]["stringValue"] for p in points},
                                 {"home", "blazor", "pwa"})
            for point in points:
                self.assertEqual(point["timeUnixNano"], str(now_ns))
                if "last_run" in metric["name"]:
                    self.assertAlmostEqual(point["asDouble"], now_ns / 1_000_000_000)
        encoded = json.dumps(payload)
        for forbidden in ["SECRET", "http://", "https://", "cookie", "blazor.boot.json", "error_code"]:
            self.assertNotIn(forbidden, encoded)

    def test_json_export_uses_post_bounded_read_and_no_redirect(self):
        probe = self.module()
        self.assertTrue(callable(getattr(probe, "send_json", None)))
        endpoint = f"http://127.0.0.1:{self.server.server_port}/metrics"
        self.routes["/metrics"] = (200, b"{}", {})
        self.assertEqual(probe.send_json(endpoint, {"resourceMetrics": []}, otlp=True), "ok")
        method, path, headers, body = self.requests[-1]
        self.assertEqual((method, path), ("POST", "/metrics"))
        self.assertEqual(headers["Content-Type"], "application/json")
        self.assertEqual(json.loads(body), {"resourceMetrics": []})
        for status, body, expected in [
            (503, b"SECRET backend", "http"),
            (302, b"", "http"),
            (200, b'{"partialSuccess":{"rejectedDataPoints":"1","errorMessage":"SECRET"}}', "content"),
            (200, b"not json SECRET", "content"),
            (200, b"x" * (probe.MAX_BODY_BYTES + 1), "content"),
        ]:
            self.routes["/metrics"] = (status, body, {"Location": "https://external.invalid/SECRET"})
            self.assertEqual(probe.send_json(endpoint, {}, otlp=True), expected)
        self.assertTrue(all(r[1] == "/metrics" for r in self.requests))
        self.assertEqual(probe.send_json("file:///SECRET", {}), "content")
        self.assertEqual(probe.send_json("http://user:SECRET@localhost/", {}), "content")
        self.server.shutdown()
        self.server.server_close()
        self.assertEqual(probe.send_json(endpoint, {}), "network")

    def healthy_routes(self):
        self.routes.update({
            "/": (200, b"blazor.webassembly.js SECRET_PRIVATE_BODY", {"Set-Cookie": "SECRET_COOKIE=x"}),
            "/_framework/blazor.boot.json": (200, b'{"resources":{"assembly":{}}}', {}),
            "/service-worker-assets.js": (200, b"self.assetsManifest = {};", {}),
            "/metrics": (200, b"{}", {}),
            "/logs": (204, b"", {}),
        })

    def test_cycle_sends_one_private_loki_summary_and_accepted_metrics_update_heartbeat(self):
        probe = self.module()
        self.assertTrue(callable(getattr(probe, "run_cycle", None)))
        import os
        from pathlib import Path
        import tempfile
        self.healthy_routes()
        base = f"http://127.0.0.1:{self.server.server_port}"
        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR", "/run/monitor")) as directory:
            heartbeat = Path(directory) / "heartbeat"
            with mock.patch.dict(os.environ, {"METRICS_ENDPOINT": base + "/metrics", "LOGS_ENDPOINT": base + "/logs"}):
                with mock.patch.object(probe, "HEARTBEAT_PATH", heartbeat):
                    with mock.patch.object(probe, "HTTPSConnection", side_effect=self.local_https):
                        with mock.patch.object(probe, "read_tls_expiry", return_value=1_900_000_000):
                            output = io.StringIO()
                            with contextlib.redirect_stdout(output):
                                probe.run_cycle()
                            self.assertTrue(heartbeat.exists())
                            self.assertTrue(probe.heartbeat_fresh())
                            self.assertEqual(json.loads(output.getvalue()),
                                             {"metrics_export": "ok", "logs_export": "ok", "heartbeat": "ok"})
                            posts = [r for r in self.requests if r[0] == "POST"]
                            self.assertEqual([r[1] for r in posts], ["/metrics", "/logs"])
                            loki = json.loads(posts[1][3])
                            self.assertEqual(len(loki["streams"]), 1)
                            stream = loki["streams"][0]
                            self.assertEqual(stream["stream"], {
                                "service_name": "ihospitalutility-monitor",
                                "deployment_environment_name": "production"})
                            self.assertEqual(len(stream["values"]), 1)
                            timestamp, message = stream["values"][0]
                            self.assertTrue(timestamp.isdigit())
                            checks = json.loads(message)["checks"]
                            self.assertEqual([c["check"] for c in checks], ["home", "blazor", "pwa"])
                            for check in checks:
                                self.assertEqual(set(check), {"check", "success", "http_status", "duration", "error_code"})
                                self.assertEqual(check["error_code"], "ok")
                            for forbidden in [b"SECRET", b"Set-Cookie", b"blazor.boot.json", b"http://", b"https://"]:
                                self.assertTrue(all(forbidden not in r[3] for r in posts))
                            # Loki failure cannot make an accepted metrics export unhealthy.
                            self.routes["/logs"] = (500, b"SECRET_BACKEND", {})
                            with contextlib.redirect_stdout(io.StringIO()) as failure_output:
                                probe.run_cycle()
                            self.assertTrue(probe.heartbeat_fresh())
                            self.assertEqual(json.loads(failure_output.getvalue())["logs_export"], "http")

    def test_metrics_failure_does_not_refresh_heartbeat_or_replay_old_cycles(self):
        probe = self.module()
        self.assertTrue(callable(getattr(probe, "run_cycle", None)))
        import os
        from pathlib import Path
        import tempfile
        self.healthy_routes()
        self.routes["/metrics"] = (503, b"SECRET backend response", {})
        base = f"http://127.0.0.1:{self.server.server_port}"
        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR", "/run/monitor")) as directory:
            heartbeat = Path(directory) / "heartbeat"
            with mock.patch.dict(os.environ, {"METRICS_ENDPOINT": base + "/metrics", "LOGS_ENDPOINT": base + "/logs"}):
                with mock.patch.object(probe, "HEARTBEAT_PATH", heartbeat):
                    with mock.patch.object(probe, "HTTPSConnection", side_effect=self.local_https):
                        with mock.patch.object(probe, "read_tls_expiry", return_value=0):
                            with contextlib.redirect_stdout(io.StringIO()):
                                probe.run_cycle()
                            self.assertFalse(heartbeat.exists())
                            heartbeat.write_text("old")
                            os.utime(heartbeat, (1, 1))
                            with contextlib.redirect_stdout(io.StringIO()):
                                probe.run_cycle()
                            self.assertEqual(heartbeat.stat().st_mtime, 1)
                            self.assertFalse(probe.heartbeat_fresh())
                            self.routes["/metrics"] = (200, b"{}", {})
                            with contextlib.redirect_stdout(io.StringIO()):
                                probe.run_cycle()
                            self.assertTrue(probe.heartbeat_fresh())
        self.assertEqual(len([r for r in self.requests if r[1] == "/metrics"]), 3)
        self.assertEqual(len([r for r in self.requests if r[1] == "/logs"]), 3)
        self.assertEqual(len([r for r in self.requests if r[0] == "GET"]), 9)

    def test_loop_has_fixed_sixty_second_cadence_and_survives_failure(self):
        probe = self.module()
        self.assertTrue(callable(getattr(probe, "run_forever", None)))
        with mock.patch.object(probe, "run_cycle", side_effect=[OSError("SECRET"), None]) as cycle:
            with mock.patch.object(probe.time, "monotonic", side_effect=[0, 2, 60, 61]):
                with mock.patch.object(probe.time, "sleep", side_effect=[None, KeyboardInterrupt]) as sleep:
                    output = io.StringIO()
                    with contextlib.redirect_stdout(output), self.assertRaises(KeyboardInterrupt):
                        probe.run_forever()
        self.assertEqual(cycle.call_count, 2)
        self.assertEqual(sleep.call_args_list, [mock.call(58), mock.call(59)])
        self.assertEqual(json.loads(output.getvalue()), {"cycle": "network"})

    def test_healthcheck_requires_existing_recent_not_future_file(self):
        probe = self.module()
        self.assertTrue(callable(getattr(probe, "heartbeat_fresh", None)))
        import os
        from pathlib import Path
        import tempfile
        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR", "/run/monitor")) as directory:
            heartbeat = Path(directory) / "heartbeat"
            with mock.patch.object(probe, "HEARTBEAT_PATH", heartbeat), mock.patch.object(probe.time, "time", return_value=1000):
                self.assertFalse(probe.heartbeat_fresh())
                heartbeat.write_text("timestamp")
                for modified, expected in [(1000, True), (820, True), (819, False), (1001, False)]:
                    os.utime(heartbeat, (modified, modified))
                    self.assertEqual(probe.heartbeat_fresh(), expected)


if __name__ == "__main__":
    unittest.main()
