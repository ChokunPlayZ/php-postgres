# PHP 7.4 backports

`php-7.4/` contains all **47** individual patches supplied from the user's
DirectAdmin CustomBuild `patches/php-7.4/` directory (October 27, 2026): `001`–`003`
and `100`–`143`. Each patch is preserved byte-for-byte. The supplied
`7-4patches.tar.gz` was actually an uncompressed tar file, with SHA-256:

```
b7012971fd01dd861ecd12b6c33592c3382c28746e5e1c7a897e1d324d095946
```

No patch tarball is stored in Git. `baseline` declares **PHP 7.4.33** and
`series.sha256` lists every patch's checksum and application order.
`docker/apply-php-patches.sh` checks the exact source baseline and validates the
entire manifest before applying anything, without fuzzy matching or ignored
failures. Missing, modified, duplicate, reordered or unlisted patches fail the
build. Compatibility patches guard the removed OpenSSL constant, select C++17
for ICU 74+, and fix XML/PEAR compatibility with newer libxml2.

All source fixes are retained, including those for optional extensions and SAPIs
not enabled in a particular image. CLI and Apache/PHP-FPM are recompiled, then
extensions are built from the patched tree. The patched tree replaces
`/usr/src/php.tar.xz` for downstream builds.

Patch `143` includes the PHP2Shell mitigation for CVE-2026-109618 and
CVE-2026-109619; do **not** also apply the old standalone 7.4 emergency patch.
The runtime policy requires the full-series ID in
`/usr/local/share/php-postgres/php2shell-backport`; a per-patch SHA-256 inventory is
written to `/usr/local/share/php-postgres/php74-patches.sha256` and retained inside
the source archive as `.php-postgres-patches.sha256`.

This series is not applied to PHP 8.x. Maintained branches use patched upstream
releases; 8.0/8.1 still use their branch-specific emergency PHP2Shell backports.
Legacy PHP remains EOL: this supplied series is not a guarantee of comprehensive
or ongoing security support. Patch headers retain their original authorship and
upstream commit references; there is no independently verified DirectAdmin
release signature for the supplied files.

## Updating a series

1. Review new patches for the declared baseline, including overlap with existing
   fixes. Add them as numbered `.patch` files, with zero-padded numbers to preserve
   dependency order (for example, `144-description.patch`). Keep the original
   filenames and authorship of existing patches.
2. Refresh the checksum manifest:

   ```sh
   python3 docker/patches/update-manifest.py docker/patches/php-7.4
   python3 tests/php-patches-test.py
   ```

3. Rebuild and smoke-test **both** flavors. Commit the patches and refreshed
   manifest together.

There are no hard-coded patch counts or patch-set digests to update in scripts or
PHP policy. The compiled runtime's record contains the SHA-256 of the manifest;
the policy derives the expected ID from the bundled manifest, so an old runtime
record cannot satisfy a changed series. The per-patch inventory and patched
source archive are preserved for downstream extension builds.

The application helper accepts any patch directory with this layout. Adding a
series for another PHP baseline also requires explicitly wiring that branch into
the engine rebuild and runtime policy; merely adding a directory must not mark
an unrebuilt runtime as patched.
