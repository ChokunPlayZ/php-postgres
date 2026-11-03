"""Test build command safety without requiring a Docker daemon."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class BuildScriptTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        self.log = self.path / "docker.log"
        docker = self.path / "docker"
        docker.write_text(
            '#!/bin/bash\n'
            'printf "%s\\n" "$*" >> "$DOCKER_TEST_LOG"\n'
            'if [[ "$1" == inspect ]]; then echo 1024; fi\n'
        )
        docker.chmod(0o755)
        self.env = dict(os.environ, PATH=f"{self.path}:{os.environ['PATH']}",
                        DOCKER_TEST_LOG=str(self.log))

    def run_build(self, *args):
        return subprocess.run(["bash", "build.sh", *args], cwd=ROOT, env=self.env,
                              text=True, capture_output=True)

    def commands(self):
        return self.log.read_text().splitlines() if self.log.exists() else []

    def test_default_pulls_and_tags_default_only(self):
        result = self.run_build()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("build --pull -f Dockerfile --build-arg PHP_VERSION=8.4 -t php-postgres:8.4 .", self.commands())
        self.assertIn("tag php-postgres:8.4 php-postgres:latest", self.commands())

    def test_legacy_clean_build_does_not_replace_latest(self):
        result = self.run_build("--tag", "7.4", "--no-cache")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("build --pull --no-cache -f Dockerfile --build-arg PHP_VERSION=7.4 -t php-postgres:7.4 .", self.commands())
        self.assertFalse(any(line.startswith("tag ") for line in self.commands()))

    def test_missing_option_values_fail_before_docker(self):
        for args in [("--tag",), ("--name",), ("--dockerfile",), ("--tag", "--no-cache")]:
            with self.subTest(args=args):
                result = self.run_build(*args)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("requires a value", result.stdout)
        self.assertEqual(self.commands(), [])

    def test_help_does_not_require_docker(self):
        result = self.run_build("--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("default: 8.4", result.stdout)
        self.assertEqual(self.commands(), [])


if __name__ == "__main__":
    unittest.main()
