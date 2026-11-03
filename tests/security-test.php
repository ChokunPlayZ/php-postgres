<?php
require '/usr/local/lib/php-postgres/security-policy.php';
$marker = '/usr/local/share/php-postgres/php2shell-backport';
validatePhpRuntime(PHP_VERSION, is_file($marker) ? file_get_contents($marker) : '');

$errors = [];
foreach (['expose_php', 'display_errors', 'display_startup_errors', 'allow_url_include',
    'enable_dl', 'session.upload_progress.enabled'] as $setting) {
    if (!in_array(strtolower((string) ini_get($setting)), ['', '0', 'off'], true)) {
        $errors[] = $setting . ' must be disabled';
    }
}
foreach (['log_errors', 'session.use_strict_mode', 'session.use_only_cookies',
    'session.cookie_httponly'] as $setting) {
    if (!filter_var(ini_get($setting), FILTER_VALIDATE_BOOLEAN)) {
        $errors[] = $setting . ' must be enabled';
    }
}
foreach (['memory_limit' => '128M', 'post_max_size' => '32M', 'upload_max_filesize' => '16M',
    'max_input_nesting_level' => '32', 'session.cookie_samesite' => 'Lax'] as $setting => $value) {
    if (ini_get($setting) !== $value) {
        $errors[] = 'Unexpected ' . $setting;
    }
}
foreach (['bcmath', 'bz2', 'calendar', 'exif', 'gd', 'gettext', 'intl', 'mbstring', 'mysqli',
    'pcntl', 'PDO', 'pdo_mysql', 'pdo_pgsql', 'pgsql', 'redis', 'soap', 'sockets', 'xml',
    'zip', 'curl', 'openssl', 'sodium', 'Zend OPcache'] as $extension) {
    if (!extension_loaded($extension)) {
        $errors[] = 'Missing extension: ' . $extension;
    }
}
if (PHP_SAPI !== 'cli') {
    if (is_writable('/var/www/html/index.php')) {
        $errors[] = 'Web worker can overwrite application code';
    }
    @ini_set('session.upload_progress.enabled', '1');
    if (filter_var(ini_get('session.upload_progress.enabled'), FILTER_VALIDATE_BOOLEAN)) {
        $errors[] = 'Application can re-enable session upload progress';
    }
}
header('Content-Type: application/json');
http_response_code($errors ? 500 : 200);
echo json_encode(['ok' => !$errors, 'errors' => $errors]);
exit($errors ? 1 : 0);
