<?php
declare(strict_types=1);
// Společné jádro: přihlášení (relace), otisk hesla a token pro přepočet z soukrome/tajne.php (vzniká při nasazení).
const DNY_PRIHLASENI = 14;
const REPO = 'zajirA1/humanoid';
function robot_tajne(): ?array {
    $f = __DIR__ . '/tajne.php';
    $t = is_file($f) ? require $f : null;
    return is_array($t) && !empty($t['hash']) ? $t : null;
}
function robot_relace(): void {
    $relace = __DIR__ . '/relace';
    if (!is_dir($relace)) { @mkdir($relace, 0700, true); }
    if (is_dir($relace) && is_writable($relace)) { session_save_path($relace); }
    ini_set('session.gc_maxlifetime', (string) (DNY_PRIHLASENI * 86400));
    ini_set('session.use_strict_mode', '1');
    session_name('ROBOTSID');
    // Bez „domain“ – cookie platí jen pro tuto subdoménu.
    session_set_cookie_params(['lifetime' => DNY_PRIHLASENI * 86400, 'path' => '/', 'secure' => true, 'httponly' => true, 'samesite' => 'Lax']);
    session_start();
}
function robot_hlavicky(): void {
    header('X-Robots-Tag: noindex, nofollow, noarchive');
    header('Referrer-Policy: same-origin');
    header('X-Content-Type-Options: nosniff');
}
