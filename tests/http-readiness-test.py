"""Test HTTP startup retries against a local server, without Docker."""
import http.server
import os
from pathlib import Path
import shutil
import socket
import struct
import subprocess
import tempfile
import threading
import unittest

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which("curl"), "HTTP readiness tests require curl")
class HttpReadinessTest(unittest.TestCase):
    def setUp(self):
        self.responses = [(200, b"OK\n")]
        self.requests = 0
        fixture = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                response = fixture.responses[min(fixture.requests, len(fixture.responses) - 1)]
                fixture.requests += 1
                if response in ("reset", "empty", "partial"):
                    if response == "partial":
                        self.send_response(200)
                        self.send_header("Content-Length", "100")
                        self.end_headers()
                        self.wfile.write(b"incomplete response\n")
                        self.wfile.flush()
                    if response != "empty":
                        self.connection.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER,
                                                   struct.pack("ii", 1, 0))
                    self.close_connection = True
                    return
                status, body = response
                self.send_response(status)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        self.server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever,
                                       kwargs={"poll_interval": 0.05}, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop_server)
        self.url = f"http://127.0.0.1:{self.server.server_port}/healthz"

    def stop_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)

    def probe(self, **env):
        return subprocess.run(["bash", str(ROOT / "tests/wait-http.sh"), self.url],
                              env=dict(os.environ, **env), capture_output=True,
                              text=True, timeout=10)

    def test_ready_endpoint_passes(self):
        result = self.probe()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.requests, 1)

    def test_startup_transport_errors_are_retried(self):
        for error in ("reset", "empty", "partial"):
            with self.subTest(error=error):
                self.responses = [error, (200, b"OK\n")]
                self.requests = 0
                result = self.probe()
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(self.requests, 2)

    def test_unavailable_endpoint_is_retried(self):
        self.responses = [(503, b"starting\n"), (200, b"OK\n")]
        result = self.probe()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.requests, 2)

    def test_wrong_health_body_is_rejected(self):
        for body in (b"not ready\n", b"not ready\nOK\n", b""):
            with self.subTest(body=body):
                self.responses = [(200, body)]
                self.requests = 0
                self.assertNotEqual(self.probe().returncode, 0)
                self.assertEqual(self.requests, 1)

    def test_retries_are_bounded_and_curl_failure_is_not_ignored(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            log = path / "curl.args"
            curl = path / "curl"
            curl.write_text('#!/bin/sh\nprintf "%s\\n" "$@" > "$CURL_TEST_LOG"\nexit 56\n')
            curl.chmod(0o755)
            result = self.probe(PATH=f"{path}:{os.environ['PATH']}", CURL_TEST_LOG=str(log))
            self.assertEqual(result.returncode, 56)
            args = log.read_text().splitlines()
            self.assertIn("--retry-all-errors", args)
            self.assertIn("--fail", args)
            for option, maximum in (("--retry", 30), ("--retry-max-time", 60),
                                    ("--connect-timeout", 2), ("--max-time", 3)):
                value = int(args[args.index(option) + 1])
                self.assertGreater(value, 0)
                self.assertLessEqual(value, maximum)
            self.assertFalse(Path(args[args.index("--output") + 1]).exists())


if __name__ == "__main__":
    unittest.main()
