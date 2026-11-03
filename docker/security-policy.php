<?php
// PHP 7.4-compatible so the same fail-closed policy runs on every image branch.
function phpSourcePatchsetId($branch)
{
    if (!preg_match('/^\d+\.\d+$/D', $branch)) {
        return '';
    }
    $manifest = __DIR__ . '/patches/php-' . $branch . '/series.sha256';
    return is_file($manifest) ? 'patchset-sha256:' . hash_file('sha256', $manifest) : '';
}

function validatePhpRuntime($version, $backport = '')
{
    $minimums = ['8.2' => '8.2.35', '8.3' => '8.3.36', '8.4' => '8.4.27', '8.5' => '8.5.12'];
    $legacy = [
        '7.4.33' => phpSourcePatchsetId('7.4'),
        '8.0.30' => '82f8f31b16a035c1b67cc253e79f7cc288f4cc20',
        '8.1.34' => '1d7dec178a094e6e75b229ce22754045f8c6070a',
    ];
    $branch = implode('.', array_slice(explode('.', $version), 0, 2));
    if (isset($minimums[$branch]) && preg_match('/^\d+\.\d+\.\d+$/D', $version)
        && version_compare($version, $minimums[$branch], '>=')) {
        return;
    }
    if (!empty($legacy[$version]) && trim($backport) === $version . ' ' . $legacy[$version]) {
        return;
    }
    throw new RuntimeException('Unpatched or unsupported PHP runtime: ' . $version);
}

if (realpath($_SERVER['SCRIPT_FILENAME'] ?? '') === __FILE__) {
    $marker = '/usr/local/share/php-postgres/php2shell-backport';
    try {
        validatePhpRuntime(PHP_VERSION, is_file($marker) ? file_get_contents($marker) : '');
    } catch (RuntimeException $error) {
        fwrite(STDERR, $error->getMessage() . PHP_EOL);
        exit(1);
    }
}
