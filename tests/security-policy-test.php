<?php
require getenv('PHP_SECURITY_POLICY') ?: '/usr/local/lib/php-postgres/security-policy.php';

$accepted = ['8.2.35', '8.3.36', '8.4.27', '8.5.12', '8.4.28'];
foreach ($accepted as $version) {
    validatePhpRuntime($version);
}
$backports = [
    '7.4.33' => '712e60f9edfd03f0960fc4fc3c2c375f42b90aa2',
    '8.0.30' => '82f8f31b16a035c1b67cc253e79f7cc288f4cc20',
    '8.1.34' => '1d7dec178a094e6e75b229ce22754045f8c6070a',
];
foreach ($backports as $version => $commit) {
    validatePhpRuntime($version, "$version $commit\n");
}
foreach (['7.3.33', '7.4.32', '7.4.33', '8.0.30', '8.1.34', '8.2.34', '8.3.35',
    '8.4.26', '8.5.11', '8.4.27RC1', '8.6.0RC4', '9.0.0', 'invalid'] as $version) {
    try {
        validatePhpRuntime($version);
    } catch (RuntimeException $expected) {
        continue;
    }
    throw new RuntimeException('Policy incorrectly accepted ' . $version);
}
try {
    validatePhpRuntime('7.4.33', '7.4.33 82f8f31b16a035c1b67cc253e79f7cc288f4cc20');
    throw new LogicException('Policy accepted the wrong backport');
} catch (RuntimeException $expected) {
    // Wrong-branch backports must never pass.
}
echo "Runtime policy tests passed.\n";
