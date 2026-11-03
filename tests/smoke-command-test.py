"""Test smoke-test container permissions without a Docker daemon."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SmokeCommandTest(unittest.TestCase):
    def test_both_flavors_keep_worker_signal_permission_without_privileged_mode(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            log = path / "docker.jsonl"
            docker = path / "docker"
            docker.write_text(
                '#!/usr/bin/env python3\n'
                'import json, os, sys\n'
                'args = sys.argv[1:]\n'
                'with open(os.environ["DOCKER_TEST_LOG"], "a") as log:\n'
                '    log.write(json.dumps(args) + "\\n")\n'
                'if args[0] == "run" and "--name" in args:\n'
                '    sys.exit(99)  # Stop before making any HTTP requests.\n'
                'if "-r" in args:\n'
                '    print("8.4")\n'
            )
            docker.chmod(0o755)
            env = dict(os.environ, PATH=f"{path}:{os.environ['PATH']}",
                       DOCKER_TEST_LOG=str(log))
            for flavor in ("apache", "nginx"):
                with self.subTest(flavor=flavor):
                    log.write_text("")
                    result = subprocess.run(["bash", "tests/smoke.sh", "fixture", flavor],
                                            cwd=ROOT, env=env, capture_output=True,
                                            text=True, timeout=10)
                    self.assertEqual(result.returncode, 99, result.stderr)
                    commands = [json.loads(line) for line in log.read_text().splitlines()]
                    start, = [args for args in commands if args[0] == "run" and "--name" in args]
                    caps = {start[i + 1] for i, arg in enumerate(start) if arg == "--cap-add"}
                    self.assertEqual(caps, {"CHOWN", "SETUID", "SETGID", "KILL", "NET_BIND_SERVICE"})
                    self.assertEqual(start[start.index("--cap-drop") + 1], "ALL")
                    self.assertEqual(start[start.index("--security-opt") + 1], "no-new-privileges:true")
                    self.assertNotIn("--privileged", start)


if __name__ == "__main__":
    unittest.main()
