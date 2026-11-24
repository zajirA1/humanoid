<?php
declare(strict_types=1);

// Volá pouze přihlášená větev index.php. Přímý přístup k app/ a soukrome/ má dále zakázaný .htaccess.
function robot_tisk_r16(string $name): void
{
    $root = realpath(__DIR__ . '/../app/tisk/R16');
    $valid = static function ($p): bool {
        return is_string($p) && strlen($p) <= 240
            && preg_match('~^[a-zA-Z0-9_./-]+$~D', $p) === 1
            && $p[0] !== '/' && !str_contains($p, '..');
    };
    if (!$root || !$valid($name)) { http_response_code(404); return; }
    $catalogFile = $root . '/catalog.json';
    if (!is_file($catalogFile)) { http_response_code(404); return; }
    if ($name !== 'catalog.json') {
        $catalog = json_decode((string)file_get_contents($catalogFile), true);
        $files = [];
        foreach (($catalog['parts'] ?? []) as $part) {
            if (empty($part['printable'])) { continue; }
            foreach (($part['files'] ?? []) as $file) {
                if ($valid($file)) { $files[$file] = true; }
            }
            $profile = $part['process']['preset_file'] ?? null;
            if ($valid($profile)) { $files[$profile] = true; }
        }
        foreach (($catalog['profiles'] ?? []) as $profile) {
            $preset = $profile['preset_file'] ?? null;
            if ($valid($preset)) { $files[$preset] = true; }
        }
        if (!isset($files[$name])) { http_response_code(404); return; }
    }
    $path = realpath($root . '/' . $name);
    if (!$path || !str_starts_with($path, $root . DIRECTORY_SEPARATOR) || !is_file($path)) {
        http_response_code(404); return;
    }
    $mime = ['3mf' => 'model/3mf', 'stl' => 'model/stl', 'json' => 'application/json'];
    $ext = strtolower(pathinfo($path, PATHINFO_EXTENSION));
    if (!isset($mime[$ext])) { http_response_code(404); return; }
    header('Content-Type: ' . $mime[$ext]);
    header('Cache-Control: private, no-cache');
    header('X-Content-Type-Options: nosniff');
    if ($name !== 'catalog.json') {
        header('Content-Disposition: attachment; filename="' . basename($path) . '"');
    }
    header('Content-Length: ' . filesize($path));
    session_write_close();
    readfile($path);
}
