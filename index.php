<?php
// Default index.php file - will be overridden if user mounts their own
echo "<!DOCTYPE html>\n";
echo "<html lang='en'>\n";
echo "<head>\n";
echo "    <meta charset='UTF-8'>\n";
echo "    <meta name='viewport' content='width=device-width, initial-scale=1.0'>\n";
echo "    <title>PHP " . PHP_VERSION . " with PostgreSQL</title>\n";
echo "    <style>\n";
echo "        body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }\n";
echo "        .success { color: #4CAF50; }\n";
echo "        .error { color: #f44336; }\n";
echo "        .info { background: #f0f8ff; padding: 15px; border-left: 4px solid #2196F3; margin: 10px 0; }\n";
echo "        pre { background: #f5f5f5; padding: 10px; overflow-x: auto; }\n";
echo "    </style>\n";
echo "</head>\n";
echo "<body>\n";

echo "<h1>🐘 PHP " . PHP_VERSION . " with PostgreSQL Driver</h1>\n";

echo "<div class='info'>\n";
echo "<p><strong>Container Info:</strong></p>\n";
echo "<ul>\n";
echo "<li>PHP Version: " . PHP_VERSION . "</li>\n";
echo "<li>Server: " . htmlspecialchars($_SERVER['SERVER_SOFTWARE'] ?? 'Apache') . "</li>\n";
echo "<li>Host: " . ($_SERVER['SERVER_NAME'] ?? 'localhost') . "</li>\n";
echo "<li>Port: " . ($_SERVER['SERVER_PORT'] ?? '8080') . "</li>\n";
echo "</ul>\n";
echo "</div>\n";

// Check PostgreSQL extensions
$extensions = get_loaded_extensions();
$pgsql_extensions = array_filter($extensions, function($ext) {
    return strpos(strtolower($ext), 'pgsql') !== false || strpos(strtolower($ext), 'pdo') !== false;
});

echo "<h2>📦 PostgreSQL Extensions</h2>\n";
if (!empty($pgsql_extensions)) {
    echo "<p class='success'>✅ PostgreSQL extensions are loaded:</p>\n";
    echo "<ul>\n";
    foreach ($pgsql_extensions as $ext) {
        echo "<li>" . $ext . "</li>\n";
    }
    echo "</ul>\n";
} else {
    echo "<p class='error'>❌ No PostgreSQL extensions found</p>\n";
}

// Test database connection if environment variables are set
$db_host = $_ENV['DB_HOST'] ?? getenv('DB_HOST');
$db_port = $_ENV['DB_PORT'] ?? getenv('DB_PORT') ?? '5432';
$db_name = $_ENV['DB_NAME'] ?? getenv('DB_NAME');
$db_user = $_ENV['DB_USER'] ?? getenv('DB_USER');
$db_pass = $_ENV['DB_PASS'] ?? getenv('DB_PASS');

echo "<h2>🔗 Database Connection Test</h2>\n";

if ($db_host && $db_name && $db_user) {
    try {
        $dsn = "pgsql:host={$db_host};port={$db_port};dbname={$db_name}";
        $pdo = new PDO($dsn, $db_user, $db_pass, [
            PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
            PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
        ]);
        
        echo "<p class='success'>✅ Successfully connected to PostgreSQL!</p>\n";
        
        // Get PostgreSQL version
        $stmt = $pdo->query('SELECT version()');
        $version = $stmt->fetchColumn();
        echo "<p><strong>PostgreSQL Version:</strong> " . htmlspecialchars($version) . "</p>\n";
        
        // Test a simple query
        $stmt = $pdo->query('SELECT NOW() as current_time');
        $result = $stmt->fetch();
        echo "<p><strong>Current Database Time:</strong> " . $result['current_time'] . "</p>\n";
        
    } catch (PDOException $e) {
        echo "<p class='error'>❌ Database connection failed:</p>\n";
        echo "<pre>" . htmlspecialchars($e->getMessage()) . "</pre>\n";
    }
} else {
    echo "<p>ℹ️ Database connection not configured. Set the following environment variables:</p>\n";
    echo "<ul>\n";
    echo "<li><code>DB_HOST</code> - Database host</li>\n";
    echo "<li><code>DB_PORT</code> - Database port (default: 5432)</li>\n";
    echo "<li><code>DB_NAME</code> - Database name</li>\n";
    echo "<li><code>DB_USER</code> - Database username</li>\n";
    echo "<li><code>DB_PASS</code> - Database password</li>\n";
    echo "</ul>\n";
}

echo "<h2>🔧 Environment Variables</h2>\n";
echo "<table border='1' cellpadding='5' cellspacing='0' style='border-collapse: collapse; width: 100%;'>\n";
echo "<tr><th>Variable</th><th>Value</th></tr>\n";
foreach (['DB_HOST', 'DB_PORT', 'DB_NAME', 'DB_USER', 'PHP_HOST', 'PHP_PORT', 'PHP_DOCROOT'] as $var) {
    $value = $_ENV[$var] ?? getenv($var) ?? 'Not set';
    if ($var === 'DB_PASS') {
        $value = ($value !== 'Not set') ? '***' : 'Not set';
    }
    echo "<tr><td><code>{$var}</code></td><td>" . htmlspecialchars($value) . "</td></tr>\n";
}
echo "</table>\n";

echo "<h2>📝 Sample Code</h2>\n";
echo "<p>Create your own <code>index.php</code> file and mount it to <code>/app</code>:</p>\n";
echo "<pre><?php\n";
echo "// Connect to PostgreSQL\n";
echo "\$pdo = new PDO(\n";
echo "    'pgsql:host=' . \$_ENV['DB_HOST'] . ';dbname=' . \$_ENV['DB_NAME'],\n";
echo "    \$_ENV['DB_USER'],\n";
echo "    \$_ENV['DB_PASS']\n";
echo ");\n\n";
echo "// Your application code here\n";
echo "?></pre>\n";

echo "</body>\n";
echo "</html>\n";
?>