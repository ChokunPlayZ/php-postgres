"""Test APT source preparation without root access, networking or Docker."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class AptSourcesTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        self.etc = self.path / "etc"
        (self.etc / "apt/sources.list.d").mkdir(parents=True)
        self.os_release("bullseye")
        self.script = self.path / "prepare-apt.sh"
        # Map the script's system files into a disposable fixture filesystem.
        self.script.write_text((ROOT / "docker/prepare-apt.sh").read_text()
                               .replace("/etc/", f"{self.etc}/"))
        self.log = self.path / "apt.log"
        apt = self.path / "apt-get"
        apt.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$APT_TEST_LOG"\n'
                       'exit "${APT_TEST_EXIT:-0}"\n')
        apt.chmod(0o755)
        self.env = dict(os.environ, PATH=f"{self.path}:{os.environ['PATH']}",
                        APT_TEST_LOG=str(self.log))

    def os_release(self, codename):
        (self.etc / "os-release").write_text(f"ID=debian\nVERSION_CODENAME={codename}\n")

    def source(self, name, contents):
        source = self.etc / "apt" / name
        source.write_text(contents)
        return source

    def prepare(self, **env):
        return subprocess.run(["sh", str(self.script)], env=dict(self.env, **env),
                              text=True, capture_output=True, timeout=5)

    def test_bullseye_list_redirects_only_security_repository(self):
        main = "deb http://deb.debian.org/debian bullseye main\n"
        updates = "deb http://deb.debian.org/debian bullseye-updates main\n"
        source = self.source("sources.list", main + updates +
                             "deb http://deb.debian.org/debian-security bullseye-security main\n"
                             "deb-src https://security.debian.org/debian-security/ bullseye-security main\n")
        result = self.prepare()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(source.read_text(), main + updates +
                         "deb https://archive.debian.org/debian-security bullseye-security main\n"
                         "deb-src https://archive.debian.org/debian-security bullseye-security main\n")
        self.assertIn("no ongoing OS security updates", result.stderr)

    def test_bullseye_deb822_preserves_signature_settings(self):
        before = ("Types: deb\nURIs: https://deb.debian.org/debian-security\n"
                  "Suites: bullseye-security\nComponents: main\n"
                  "Signed-By: /usr/share/keyrings/debian-archive-keyring.gpg\n")
        source = self.source("sources.list.d/debian.sources", before)
        result = self.prepare()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(source.read_text(), before.replace("deb.debian.org", "archive.debian.org"))

    def test_list_fragments_are_updated_but_other_hosts_are_untouched(self):
        other = "deb https://example.com/debian-security bullseye-security main\n"
        source = self.source("sources.list.d/security.list", other +
                             "deb https://security.debian.org/debian-security bullseye-security main\n")
        result = self.prepare()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(source.read_text(), other +
                         "deb https://archive.debian.org/debian-security bullseye-security main\n")

    def test_maintained_releases_are_unchanged(self):
        for codename in ("bookworm", "trixie"):
            with self.subTest(codename=codename):
                self.os_release(codename)
                before = f"deb http://deb.debian.org/debian-security {codename}-security main\n"
                source = self.source("sources.list", before)
                result = self.prepare()
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(source.read_text(), before)
                self.assertEqual(result.stderr, "")

    def test_preparation_is_idempotent(self):
        source = self.source("sources.list", "deb http://deb.debian.org/debian-security bullseye-security main\n")
        first = self.prepare()
        self.assertEqual(first.returncode, 0, first.stderr)
        contents = source.read_text()
        second = self.prepare()
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(source.read_text(), contents)

    def test_update_is_strict_and_retries_transient_failures(self):
        result = self.prepare()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.log.read_text().splitlines(),
                         ["update -o APT::Update::Error-Mode=any -o Acquire::Retries=3"])

    def test_update_failure_is_not_ignored(self):
        result = self.prepare(APT_TEST_EXIT="100")
        self.assertEqual(result.returncode, 100)


if __name__ == "__main__":
    unittest.main()
