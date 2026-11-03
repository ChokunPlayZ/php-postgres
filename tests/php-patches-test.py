"""Test patch inventory, extensibility and fail-closed application without Docker."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PATCHES = ROOT / "docker/patches/php-7.4"
UPDATER = ROOT / "docker/patches/update-manifest.py"
APPLIER = ROOT / "docker/apply-php-patches.sh"


class PhpPatchesTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="php patches ")
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        self.source = self.path / "source"
        (self.source / "main").mkdir(parents=True)
        (self.source / "main/php_version.h").write_text('#define PHP_VERSION "7.4.33"\n')
        self.patches = self.path / "patches"
        self.patches.mkdir()
        (self.patches / "baseline").write_text("7.4.33\n")
        (self.patches / "001-first.patch").write_text("first patch\n")
        (self.patches / "002-second.patch").write_text("second patch\n")
        self.refresh()
        self.log = self.path / "patch.jsonl"
        patch = self.path / "patch"
        patch.write_text(
            '#!/usr/bin/env python3\n'
            'import hashlib, json, os, sys\n'
            'from pathlib import Path\n'
            'log = Path(os.environ["PATCH_TEST_LOG"])\n'
            'record = [sys.argv[1:], hashlib.sha256(sys.stdin.buffer.read()).hexdigest()]\n'
            'with log.open("a") as output:\n'
            '    output.write(json.dumps(record) + "\\n")\n'
            'if len(log.read_text().splitlines()) == int(os.getenv("PATCH_FAIL_AT", "0")):\n'
            '    sys.exit(1)\n'
        )
        patch.chmod(0o755)
        # macOS has shasum but not necessarily GNU sha256sum.
        if not shutil.which("sha256sum"):
            sha256sum = self.path / "sha256sum"
            sha256sum.write_text(
                '#!/usr/bin/env python3\n'
                'import hashlib, pathlib, sys\n'
                'assert sys.argv[1:] == ["--check", "--strict", "series.sha256"]\n'
                'for line in pathlib.Path("series.sha256").read_text().splitlines():\n'
                '    digest, name = line.split("  ")\n'
                '    if hashlib.sha256(pathlib.Path(name).read_bytes()).hexdigest() != digest:\n'
                '        sys.exit(1)\n'
            )
            sha256sum.chmod(0o755)
        self.env = dict(os.environ, PATH=f"{self.path}:{os.environ['PATH']}",
                        PATCH_TEST_LOG=str(self.log))

    def refresh(self):
        return subprocess.run(["python3", str(UPDATER), str(self.patches)],
                              check=True, capture_output=True, text=True, timeout=5)

    def apply(self, **env):
        return subprocess.run(["sh", str(APPLIER), str(self.source), str(self.patches)],
                              env=dict(self.env, **env), capture_output=True,
                              text=True, timeout=10)

    def records(self):
        return [json.loads(line) for line in self.log.read_text().splitlines()] if self.log.exists() else []

    def assert_rejected_before_patching(self):
        result = self.apply()
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.records(), [])
        self.assertFalse((self.source / ".php-postgres-patches.sha256").exists())

    def test_supplied_series_is_complete_and_matches_manifest(self):
        patches = sorted(PATCHES.glob("*.patch"))
        required = {"001", "002", "003"} | {str(number) for number in range(100, 144)}
        self.assertTrue(required.issubset({patch.name.split("-", 1)[0] for patch in patches}))
        expected = "".join(f"{hashlib.sha256(patch.read_bytes()).hexdigest()}  {patch.name}\n"
                           for patch in patches)
        self.assertEqual((PATCHES / "series.sha256").read_text(), expected)
        self.assertEqual((PATCHES / "baseline").read_text(), "7.4.33\n")
        self.assertFalse(list((ROOT / "docker/patches").rglob("*.tar*")))

    def test_applies_every_patch_in_order_with_strict_flags(self):
        result = self.apply()
        self.assertEqual(result.returncode, 0, result.stderr)
        expected = [hashlib.sha256(patch.read_bytes()).hexdigest()
                    for patch in sorted(self.patches.glob("*.patch"))]
        self.assertEqual([record[1] for record in self.records()], expected)
        for args, digest in self.records():
            self.assertEqual(args, ["--batch", "--forward", "--fuzz=0", "--no-backup-if-mismatch",
                                    "-p1", "-d", str(self.source)])
        self.assertEqual((self.source / ".php-postgres-patches.sha256").read_bytes(),
                         (self.patches / "series.sha256").read_bytes())

    def test_future_patch_only_needs_a_manifest_refresh(self):
        previous = (self.patches / "series.sha256").read_bytes()
        (self.patches / "003-future.patch").write_text("future patch\n")
        self.assert_rejected_before_patching()
        self.refresh()
        self.assertNotEqual((self.patches / "series.sha256").read_bytes(), previous)
        result = self.apply()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(self.records()), 3)

    def test_last_patch_is_not_skipped_without_a_final_newline(self):
        manifest = self.patches / "series.sha256"
        manifest.write_text(manifest.read_text().rstrip("\n"))
        result = self.apply()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(self.records()), 2)

    def test_modified_patch_fails_before_applying_any_patch(self):
        (self.patches / "002-second.patch").write_text("tampered\n")
        self.assert_rejected_before_patching()

    def test_missing_patch_fails_before_applying_any_patch(self):
        (self.patches / "002-second.patch").unlink()
        self.assert_rejected_before_patching()

    def test_reordered_duplicate_empty_and_unsafe_manifests_fail(self):
        manifest = self.patches / "series.sha256"
        lines = manifest.read_text().splitlines(keepends=True)
        for contents in ("".join(reversed(lines)), "".join(lines + lines[:1]), "",
                         "a" * 64 + "  ../escape.patch\n"):
            with self.subTest(contents=contents):
                manifest.write_text(contents)
                self.assert_rejected_before_patching()

    def test_symlink_is_not_a_patch_file(self):
        second = self.patches / "002-second.patch"
        second.unlink()
        second.symlink_to(self.patches / "001-first.patch")
        self.assert_rejected_before_patching()

    def test_wrong_source_baseline_is_rejected(self):
        for version in ("7.4.32", "8.0.30", "8.4.27"):
            with self.subTest(version=version):
                (self.source / "main/php_version.h").write_text(f'#define PHP_VERSION "{version}"\n')
                self.assert_rejected_before_patching()

    def test_failed_hunk_stops_without_inventory_or_later_patches(self):
        result = self.apply(PATCH_FAIL_AT="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(len(self.records()), 1)
        self.assertFalse((self.source / ".php-postgres-patches.sha256").exists())

    def test_helper_can_apply_another_explicit_baseline(self):
        (self.source / "main/php_version.h").write_text('#define PHP_VERSION "8.0.30"\n')
        (self.patches / "baseline").write_text("8.0.30\n")
        result = self.apply()
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_updater_rejects_unnumbered_files_without_overwriting_manifest(self):
        manifest = self.patches / "series.sha256"
        previous = manifest.read_bytes()
        (self.patches / "unreviewed.patch").write_text("unreviewed\n")
        result = subprocess.run(["python3", str(UPDATER), str(self.patches)],
                                capture_output=True, text=True, timeout=5)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(manifest.read_bytes(), previous)

    def test_updater_requires_an_exact_baseline(self):
        for baseline in ("7.4", "7.4.33RC1", ""):
            with self.subTest(baseline=baseline):
                (self.patches / "baseline").write_text(baseline)
                result = subprocess.run(["python3", str(UPDATER), str(self.patches)],
                                        capture_output=True, text=True, timeout=5)
                self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
