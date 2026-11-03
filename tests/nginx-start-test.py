"""Test process supervision with fake daemons, without Docker (requires Bash 4.3+)."""
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
BASH = os.environ.get("BASH_FOR_TESTS", "bash")
HAS_WAIT_N = "-n" in subprocess.check_output([BASH, "-c", "help wait"], text=True)
DAEMON = """#!/usr/bin/env python3
import os
from pathlib import Path
import signal
import sys

name = Path(sys.argv[0]).name
if '-t' in sys.argv or '--test' in sys.argv:
    sys.exit(1 if os.environ.get('FAIL_CONFIG') == name else 0)
signal.signal(signal.SIGQUIT, lambda *_: sys.exit(0))
signal.signal(signal.SIGTERM, lambda *_: sys.exit(23))
pid = Path(os.environ['STUB_ROOT'], name + '.tmp')
pid.write_text(str(os.getpid()))
pid.rename(pid.with_suffix('.pid'))
while True:
    signal.pause()
"""


@unittest.skipUnless(HAS_WAIT_N, "process lifecycle tests require Bash 4.3+")
class NginxStartTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        for name in ("nginx", "php-fpm"):
            daemon = self.path / name
            daemon.write_text(DAEMON)
            daemon.chmod(0o755)
        self.env = dict(os.environ, PATH=f"{self.path}:{os.environ['PATH']}",
                        STUB_ROOT=str(self.path))

    def cleanup_stack(self, process):
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.communicate(timeout=5)

    def start_stack(self):
        process = subprocess.Popen([BASH, str(ROOT / "docker/nginx-php-fpm.sh")],
                                   env=self.env, start_new_session=True,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.addCleanup(self.cleanup_stack, process)
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if all((self.path / f"{name}.pid").exists() for name in ("nginx", "php-fpm")):
                return process
            if process.poll() is not None:
                self.fail(f"Stack exited before startup: {process.communicate()}")
            time.sleep(0.01)
        self.fail("Timed out waiting for fake daemons")

    def daemon_pid(self, name):
        return int((self.path / f"{name}.pid").read_text())

    def assert_daemons_stopped(self):
        for name in ("nginx", "php-fpm"):
            with self.assertRaises(ProcessLookupError, msg=f"{name} was not reaped"):
                os.kill(self.daemon_pid(name), 0)

    def test_stop_gracefully_reaps_both_daemons(self):
        process = self.start_stack()
        process.terminate()
        process.communicate(timeout=5)
        self.assertEqual(process.returncode, 0)
        self.assert_daemons_stopped()

    def test_fpm_failure_stops_nginx(self):
        process = self.start_stack()
        os.kill(self.daemon_pid("php-fpm"), signal.SIGTERM)
        process.communicate(timeout=5)
        self.assertEqual(process.returncode, 23)
        self.assert_daemons_stopped()

    def test_nginx_failure_stops_fpm(self):
        process = self.start_stack()
        os.kill(self.daemon_pid("nginx"), signal.SIGTERM)
        process.communicate(timeout=5)
        self.assertEqual(process.returncode, 23)
        self.assert_daemons_stopped()

    def test_unexpected_clean_exit_is_still_a_failure(self):
        process = self.start_stack()
        os.kill(self.daemon_pid("nginx"), signal.SIGQUIT)
        process.communicate(timeout=5)
        self.assertEqual(process.returncode, 1)
        self.assert_daemons_stopped()

    def test_invalid_configuration_starts_neither_daemon(self):
        for name in ("nginx", "php-fpm"):
            with self.subTest(name=name):
                result = subprocess.run([BASH, str(ROOT / "docker/nginx-php-fpm.sh")],
                                        env=dict(self.env, FAIL_CONFIG=name),
                                        capture_output=True, text=True, timeout=5)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(list(self.path.glob("*.pid")))


if __name__ == "__main__":
    unittest.main()
