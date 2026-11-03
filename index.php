<?php
// Do not expose runtime/database diagnostics on a fresh production deployment.
if (getenv('ENABLE_STARTER_DASHBOARD') !== '1') {
    header('Content-Type: text/plain; charset=UTF-8');
    echo "PHP application container is running.\n";
    return;
}

// PHP PostgreSQL Starter Dashboard
// Dynamically verifies environment setup and provides configuration details.

$php_version = PHP_VERSION;
$server_software = $_SERVER['SERVER_SOFTWARE'] ?? 'PHP';
$is_nginx = stripos($server_software, 'nginx') !== false;
$extensions = get_loaded_extensions();

// Filter for database-related extensions
$pgsql_extensions = array_filter($extensions, function($ext) {
    return strpos(strtolower($ext), 'pgsql') !== false || strpos(strtolower($ext), 'pdo') !== false;
});

// Database connection variables
$db_host = $_ENV['DB_HOST'] ?? getenv('DB_HOST');
$db_port = $_ENV['DB_PORT'] ?? (getenv('DB_PORT') ?: '5432');
$db_name = $_ENV['DB_NAME'] ?? getenv('DB_NAME');
$db_user = $_ENV['DB_USER'] ?? getenv('DB_USER');
$db_pass = $_ENV['DB_PASS'] ?? getenv('DB_PASS');

$db_connected = false;
$db_error = null;
$db_version = null;
$db_time = null;

if ($db_host && $db_name && $db_user) {
    try {
        $dsn = "pgsql:host={$db_host};port={$db_port};dbname={$db_name}";
        $pdo = new PDO($dsn, $db_user, $db_pass, [
            PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
            PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
            PDO::ATTR_TIMEOUT => 3 // short timeout for responsiveness
        ]);
        $db_connected = true;
        
        $db_version = $pdo->query('SELECT version()')->fetchColumn();
        $db_time = $pdo->query('SELECT NOW() as current_time')->fetch()['current_time'];
    } catch (PDOException $e) {
        error_log('Starter dashboard database connection failed.');
        $db_error = 'Connection failed. Check the database configuration and server logs.';
    }
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PHP <?php echo $php_version; ?> + PostgreSQL Environment</title>
    
    <!-- Google Fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
    
    <style>
        :root {
            --bg-primary: #090d16;
            --bg-secondary: rgba(17, 24, 39, 0.7);
            --bg-card: rgba(30, 41, 59, 0.4);
            --border-color: rgba(255, 255, 255, 0.08);
            --text-primary: #f3f4f6;
            --text-secondary: #9ca3af;
            --accent-blue: #3b82f6;
            --accent-purple: #8b5cf6;
            --accent-green: #10b981;
            --accent-red: #ef4444;
            --glow-blue: rgba(59, 130, 246, 0.15);
            --glow-purple: rgba(139, 92, 246, 0.15);
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: 'Plus Jakarta Sans', sans-serif;
            background-color: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            line-height: 1.5;
            background-image: 
                radial-gradient(circle at 10% 20%, var(--glow-blue) 0%, transparent 40%),
                radial-gradient(circle at 90% 80%, var(--glow-purple) 0%, transparent 40%);
            background-attachment: fixed;
        }

        header {
            padding: 2.5rem 2rem;
            max-width: 1200px;
            margin: 0 auto;
            width: 100%;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--border-color);
        }

        .logo-section {
            display: flex;
            align-items: center;
            gap: 1rem;
        }

        .logo-badge {
            background: linear-gradient(135deg, var(--accent-blue), var(--accent-purple));
            width: 3.5rem;
            height: 3.5rem;
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.8rem;
            box-shadow: 0 8px 20px rgba(59, 130, 246, 0.3);
        }

        h1 {
            font-size: 1.5rem;
            font-weight: 700;
            background: linear-gradient(to right, #ffffff, #9ca3af);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .server-badge {
            background-color: rgba(255, 255, 255, 0.05);
            border: 1px solid var(--border-color);
            padding: 0.5rem 1rem;
            border-radius: 9999px;
            font-size: 0.85rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
            color: var(--text-secondary);
        }

        .badge-dot {
            width: 8px;
            height: 8px;
            background-color: var(--accent-green);
            border-radius: 50%;
            display: inline-block;
            box-shadow: 0 0 8px var(--accent-green);
        }

        main {
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem;
            width: 100%;
            flex: 1;
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 2rem;
        }

        @media (max-width: 968px) {
            main {
                grid-template-columns: 1fr;
            }
            header {
                flex-direction: column;
                gap: 1rem;
                align-items: flex-start;
            }
        }

        .card {
            background-color: var(--bg-card);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 2rem;
            transition: transform 0.2s ease, border-color 0.2s ease;
        }

        .card:hover {
            border-color: rgba(255, 255, 255, 0.15);
        }

        .card-title {
            font-size: 1.2rem;
            font-weight: 600;
            margin-bottom: 1.5rem;
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }

        .card-title svg {
            color: var(--accent-blue);
        }

        /* Tech Badges Grid */
        .badges-grid {
            display: flex;
            flex-wrap: wrap;
            gap: 0.75rem;
        }

        .tech-badge {
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid var(--border-color);
            padding: 0.5rem 0.85rem;
            border-radius: 8px;
            font-size: 0.85rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
            transition: all 0.2s ease;
        }

        .tech-badge:hover {
            background: rgba(255, 255, 255, 0.08);
            transform: translateY(-2px);
        }

        .tech-badge.active {
            border-color: rgba(16, 185, 129, 0.3);
            background: rgba(16, 185, 129, 0.05);
        }

        .status-indicator {
            font-size: 0.75rem;
            padding: 0.15rem 0.4rem;
            border-radius: 4px;
            font-weight: 600;
        }

        .status-indicator.success {
            background-color: rgba(10, 200, 100, 0.15);
            color: var(--accent-green);
        }

        /* Database Tester Section */
        .db-status-box {
            padding: 1.25rem;
            border-radius: 12px;
            margin-bottom: 1.5rem;
            display: flex;
            flex-direction: column;
            gap: 0.75rem;
            border: 1px solid var(--border-color);
        }

        .db-status-box.connected {
            background: rgba(16, 185, 129, 0.04);
            border-color: rgba(16, 185, 129, 0.2);
        }

        .db-status-box.failed {
            background: rgba(239, 68, 68, 0.04);
            border-color: rgba(239, 68, 68, 0.2);
        }

        .db-status-box.not-configured {
            background: rgba(255, 255, 255, 0.02);
            border-color: var(--border-color);
        }

        .db-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-weight: 600;
            font-size: 1rem;
        }

        .db-details {
            font-size: 0.85rem;
            color: var(--text-secondary);
            display: flex;
            flex-direction: column;
            gap: 0.35rem;
        }

        .error-message {
            background: rgba(239, 68, 68, 0.08);
            border-left: 3px solid var(--accent-red);
            padding: 0.75rem;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.8rem;
            border-radius: 0 8px 8px 0;
            overflow-x: auto;
            color: #fca5a5;
        }

        /* Environment variables table */
        .env-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.85rem;
        }

        .env-table tr {
            border-bottom: 1px solid var(--border-color);
        }

        .env-table tr:last-child {
            border-bottom: none;
        }

        .env-table td {
            padding: 0.75rem 0.5rem;
        }

        .env-table td.var-name {
            font-family: 'JetBrains Mono', monospace;
            color: var(--text-primary);
            font-weight: 500;
        }

        .env-table td.var-val {
            font-family: 'JetBrains Mono', monospace;
            color: var(--text-secondary);
            text-align: right;
        }

        /* Code Block */
        .code-container {
            position: relative;
            margin-top: 1rem;
        }

        pre {
            background-color: rgba(10, 15, 26, 0.8);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 1.25rem;
            overflow-x: auto;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.85rem;
            color: #e5e7eb;
        }

        .copy-btn {
            position: absolute;
            top: 0.75rem;
            right: 0.75rem;
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid var(--border-color);
            color: var(--text-secondary);
            padding: 0.35rem 0.75rem;
            border-radius: 6px;
            font-size: 0.75rem;
            cursor: pointer;
            transition: all 0.2s ease;
        }

        .copy-btn:hover {
            background: rgba(255, 255, 255, 0.1);
            color: #fff;
        }

        footer {
            text-align: center;
            padding: 2.5rem;
            font-size: 0.8rem;
            color: var(--text-secondary);
            border-top: 1px solid var(--border-color);
            max-width: 1200px;
            margin: 0 auto;
            width: 100%;
        }

        a {
            color: var(--accent-blue);
            text-decoration: none;
        }

        a:hover {
            text-decoration: underline;
        }
    </style>
</head>
<body>

    <header>
        <div class="logo-section">
            <div class="logo-badge">🐘</div>
            <div>
                <h1>PHP <?php echo $php_version; ?> Environment</h1>
                <p style="font-size: 0.85rem; color: var(--text-secondary);">PostgreSQL & Extension Stack</p>
            </div>
        </div>
        <div class="server-badge">
            <span class="badge-dot"></span>
            Server: <?php echo htmlspecialchars($server_software); ?>
        </div>
    </header>

    <main>
        <!-- Left Side: Status and Environment -->
        <div style="display: flex; flex-direction: column; gap: 2rem;">
            <!-- Database Connection Card -->
            <div class="card">
                <h2 class="card-title">
                    <svg width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                        <path d="M4 7V4a2 2 0 012-2h12a2 2 0 012 2v3m-16 0h16M4 7c0 1.66 3.58 3 8 3s8-1.34 8-3M4 14v-3c0 1.66 3.58 3 8 3s8-1.34 8-3m-16 3v3a2 2 0 002 2h12a2 2 0 002-2v-3m-16 0c0 1.66 3.58 3 8 3s8-1.34 8-3"></path>
                    </svg>
                    Database Connection Test
                </h2>
                
                <?php if ($db_connected): ?>
                    <div class="db-status-box connected">
                        <div class="db-header">
                            <span style="color: var(--accent-green);">Connected to PostgreSQL</span>
                            <span class="status-indicator success">ACTIVE</span>
                        </div>
                        <div class="db-details">
                            <p><strong>Host:</strong> <?php echo htmlspecialchars($db_host); ?>:<?php echo htmlspecialchars($db_port); ?></p>
                            <p><strong>Database:</strong> <?php echo htmlspecialchars($db_name); ?></p>
                            <p><strong>Server Version:</strong> <?php echo htmlspecialchars($db_version); ?></p>
                            <p><strong>Database Time:</strong> <?php echo htmlspecialchars($db_time); ?></p>
                        </div>
                    </div>
                <?php elseif ($db_error): ?>
                    <div class="db-status-box failed">
                        <div class="db-header">
                            <span style="color: var(--accent-red);">Connection Failed</span>
                        </div>
                        <div class="db-details" style="margin-bottom: 0.5rem;">
                            <p><strong>Host:</strong> <?php echo htmlspecialchars($db_host); ?>:<?php echo htmlspecialchars($db_port); ?></p>
                            <p><strong>Database:</strong> <?php echo htmlspecialchars($db_name); ?></p>
                        </div>
                        <div class="error-message">
                            <?php echo htmlspecialchars($db_error); ?>
                        </div>
                    </div>
                <?php else: ?>
                    <div class="db-status-box not-configured">
                        <div class="db-header">
                            <span style="color: var(--text-secondary);">No Connection Configured</span>
                        </div>
                        <div class="db-details">
                            <p>Provide environment variables to run a live connection check:</p>
                            <ul style="margin-left: 1.25rem; margin-top: 0.25rem;">
                                <li><code>DB_HOST</code></li>
                                <li><code>DB_NAME</code></li>
                                <li><code>DB_USER</code></li>
                                <li><code>DB_PASS</code></li>
                            </ul>
                        </div>
                    </div>
                <?php endif; ?>

                <table class="env-table">
                    <tr>
                        <td class="var-name">DB_HOST</td>
                        <td class="var-val"><?php echo htmlspecialchars($db_host ?: 'Not Set'); ?></td>
                    </tr>
                    <tr>
                        <td class="var-name">DB_PORT</td>
                        <td class="var-val"><?php echo htmlspecialchars($db_port ?: '5432'); ?></td>
                    </tr>
                    <tr>
                        <td class="var-name">DB_NAME</td>
                        <td class="var-val"><?php echo htmlspecialchars($db_name ?: 'Not Set'); ?></td>
                    </tr>
                    <tr>
                        <td class="var-name">DB_USER</td>
                        <td class="var-val"><?php echo htmlspecialchars($db_user ?: 'Not Set'); ?></td>
                    </tr>
                </table>
            </div>

            <!-- Extensions Card -->
            <div class="card">
                <h2 class="card-title">
                    <svg width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                        <path d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"></path>
                    </svg>
                    Loaded PHP Extensions
                </h2>
                <div class="badges-grid">
                    <?php
                    $critical_extensions = ['pdo_pgsql', 'pgsql', 'pdo_mysql', 'redis', 'gd', 'zip', 'intl', 'opcache', 'bcmath', 'soap', 'xml', 'curl', 'mbstring'];
                    foreach ($critical_extensions as $ext) {
                        $is_loaded = in_array($ext, $extensions);
                        $class = $is_loaded ? 'active' : '';
                        $icon = $is_loaded ? '🟢' : '🔴';
                        echo "<div class='tech-badge {$class}'>";
                        echo "<span>{$icon}</span>";
                        echo "<strong>{$ext}</strong>";
                        echo "</div>";
                    }
                    ?>
                </div>
            </div>
        </div>

        <!-- Right Side: Code Snippets & Guide -->
        <div style="display: flex; flex-direction: column; gap: 2rem;">
            <div class="card">
                <h2 class="card-title">
                    <svg width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                        <path d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"></path>
                    </svg>
                    Sample Connection Code
                </h2>
                <p style="font-size: 0.85rem; color: var(--text-secondary); margin-bottom: 1rem;">
                    You can use this snippet to connect to the PostgreSQL database in your own <code>index.php</code>:
                </p>
                <div class="code-container">
                    <button class="copy-btn" onclick="copyCode()">Copy</button>
                    <pre id="code-snippet"><code>&lt;?php
// Configure credentials via environment variables
$host = getenv('DB_HOST') ?: 'localhost';
$port = getenv('DB_PORT') ?: '5432';
$dbname = getenv('DB_NAME') ?: 'postgres';
$user = getenv('DB_USER') ?: 'postgres';
$password = getenv('DB_PASS');

try {
    $dsn = "pgsql:host=$host;port=$port;dbname=$dbname";
    $pdo = new PDO($dsn, $user, $password, [
        PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION
    ]);
    
    echo "Successfully connected to PostgreSQL!";
} catch (PDOException $e) {
    error_log('Database connection failed.');
    echo "Database unavailable.";
}
?&gt;</code></pre>
                </div>
            </div>

            <div class="card">
                <h2 class="card-title">
                    <svg width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                        <path d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                    </svg>
                    Quick Documentation
                </h2>
                <p style="font-size: 0.9rem; color: var(--text-secondary); margin-bottom: 0.75rem;">
                    To mount your custom code, map a volume to <code>/var/www/html</code> inside the container.
                </p>
                <div style="font-size: 0.85rem; display: flex; flex-direction: column; gap: 0.5rem; color: var(--text-secondary);">
                    <p>🌐 <strong>Port Forwarding:</strong> Map port 80 to access the web server (e.g. <code>-p 8080:80</code>).</p>
                    <?php if ($is_nginx): ?>
                    <p>⚙️ <strong>Nginx Settings:</strong> Front-controller routing is enabled. Configure rewrites in <code>/etc/nginx/conf.d/default.conf</code>; <code>.htaccess</code> is not supported.</p>
                    <?php else: ?>
                    <p>⚙️ <strong>Apache Settings:</strong> Rewrite and authentication rules are supported in <code>.htaccess</code>; PHP overrides are disabled.</p>
                    <?php endif; ?>
                    <p>📦 <strong>Composer:</strong> Available globally in the shell as <code>composer</code>.</p>
                </div>
            </div>
        </div>
    </main>

    <footer>
        <p>PHP PostgreSQL Base Image Stack &bull; Designed beautifully.</p>
    </footer>

    <script>
        function copyCode() {
            const codeText = document.getElementById('code-snippet').textContent;
            navigator.clipboard.writeText(codeText).then(() => {
                const btn = document.querySelector('.copy-btn');
                btn.textContent = 'Copied!';
                setTimeout(() => {
                    btn.textContent = 'Copy';
                }, 2000);
            });
        }
    </script>
</body>
</html>
