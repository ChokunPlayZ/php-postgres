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

    def test_nginx_uses_fpm_dockerfile_and_flavor_tags(self):
        result = self.run_build("--flavor", "nginx", "--no-cache")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("build --pull --no-cache -f Dockerfile.nginx --build-arg PHP_VERSION=8.4 -t php-postgres:8.4-nginx .", self.commands())
        self.assertIn("tag php-postgres:8.4-nginx php-postgres:latest-nginx", self.commands())
        self.assertNotIn("tag php-postgres:8.4-nginx php-postgres:latest", self.commands())

    def test_nondefault_nginx_does_not_replace_latest(self):
        result = self.run_build("--tag", "7.4", "--flavor", "nginx")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("build --pull -f Dockerfile.nginx --build-arg PHP_VERSION=7.4 -t php-postgres:7.4-nginx .", self.commands())
        self.assertFalse(any(line.startswith("tag ") for line in self.commands()))

    def test_explicit_apache_is_backwards_compatible(self):
        result = self.run_build("--flavor", "apache")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("build --pull -f Dockerfile --build-arg PHP_VERSION=8.4 -t php-postgres:8.4 .", self.commands())

    def test_custom_dockerfile_is_not_overridden_by_flavor(self):
        result = self.run_build("--dockerfile", "Dockerfile", "--flavor", "nginx")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("build --pull -f Dockerfile --build-arg PHP_VERSION=8.4 -t php-postgres:8.4-nginx .", self.commands())

    def test_invalid_flavor_fails_before_docker(self):
        result = self.run_build("--flavor", "invalid")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Unsupported flavor", result.stdout)
        self.assertEqual(self.commands(), [])

    def test_missing_option_values_fail_before_docker(self):
        for args in [("--tag",), ("--name",), ("--dockerfile",), ("--flavor",),
                     ("--tag", "--no-cache"), ("--flavor", "--no-cache")]:
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
