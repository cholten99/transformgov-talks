<?php
// router.php for local dev with `php -S localhost:8000 router.php`

$path = parse_url($_SERVER["REQUEST_URI"], PHP_URL_PATH);

// Serve static files directly if they exist (CSS, JS, images, etc.)
if ($path !== "/" && file_exists(__DIR__ . $path)) {
    return false; // let the built-in PHP server handle it
}

// Default to index.php for /
if ($path === "/") {
    include __DIR__ . "/index.php";
    exit;
}

// Try mapping /something → something.php
$slug = trim($path, "/");
$file = __DIR__ . "/" . $slug . ".php";

if ($slug && file_exists($file)) {
    include $file;
    exit;
}

// Otherwise serve 404
http_response_code(404);
include __DIR__ . "/404.php";
exit;
