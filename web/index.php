<?php
declare(strict_types=1);
// Humanoid – přihlášení jedním heslem a vydání simulátoru. Heslo (otisk) je v soukrome/tajne.php,
// který vytváří workflow „Nasazení na Hetzner“ z tajné hodnoty ROBOT_HESLO. V repozitáři není.

header('X-Robots-Tag: noindex, nofollow, noarchive');
header('Referrer-Policy: same-origin');
header('X-Content-Type-Options: nosniff');

const DNY_PRIHLASENI = 14;
const MAX_POKUSU = 8;        // chybných pokusů z jedné adresy
const OKNO_POKUSU = 900;     // za 15 minut

$soukrome = __DIR__ . '/soukrome';
$tajne = is_file($soukrome . '/tajne.php') ? require $soukrome . '/tajne.php' : null;
if (!is_array($tajne) || empty($tajne['hash'])) {
    http_response_code(503);
    header('Content-Type: text/plain; charset=utf-8');
    exit('Heslo zatím není nastavené. Spusť nasazení z GitHubu s tajnou hodnotou ROBOT_HESLO.');
}

$relace = $soukrome . '/relace';
if (!is_dir($relace)) { @mkdir($relace, 0700, true); }
if (is_dir($relace) && is_writable($relace)) { session_save_path($relace); }
ini_set('session.gc_maxlifetime', (string) (DNY_PRIHLASENI * 86400));
ini_set('session.use_strict_mode', '1');
session_name('ROBOTSID');
// Bez „domain“ – cookie platí jen pro tuto subdoménu, ne pro caribhaus.com ani jiné subdomény.
session_set_cookie_params(['lifetime' => DNY_PRIHLASENI * 86400, 'path' => '/', 'secure' => true, 'httponly' => true, 'samesite' => 'Lax']);
session_start();

function pokusy_soubor(string $soukrome): string { return $soukrome . '/pokusy.json'; }
function pokusy_nacti(string $soukrome): array {
    $d = @json_decode((string) @file_get_contents(pokusy_soubor($soukrome)), true);
    $d = is_array($d) ? $d : [];
    $ted = time();
    foreach ($d as $k => $casy) { $d[$k] = array_values(array_filter((array) $casy, fn($t) => $ted - (int) $t < OKNO_POKUSU)); if (!$d[$k]) unset($d[$k]); }
    return $d;
}
$klic = sha1((string) ($_SERVER['REMOTE_ADDR'] ?? '?'));
$chyba = '';

if (isset($_GET['odhlasit'])) {
    $_SESSION = [];
    session_destroy();
    header('Location: ./');
    exit;
}

if (($_SERVER['REQUEST_METHOD'] ?? 'GET') === 'POST' && empty($_SESSION['ok'])) {
    $pokusy = pokusy_nacti($soukrome);
    if (count($pokusy[$klic] ?? []) >= MAX_POKUSU) {
        $chyba = 'Příliš mnoho chybných pokusů. Zkus to znovu za čtvrt hodiny.';
    } elseif (!hash_equals((string) ($_SESSION['csrf'] ?? ''), (string) ($_POST['csrf'] ?? ''))) {
        $chyba = 'Formulář vypršel, zkus to znovu.';
    } elseif (password_verify((string) ($_POST['heslo'] ?? ''), (string) $tajne['hash'])) {
        session_regenerate_id(true);
        $_SESSION['ok'] = true;
        unset($pokusy[$klic]);
        @file_put_contents(pokusy_soubor($soukrome), json_encode($pokusy), LOCK_EX);
        header('Location: ./');
        exit;
    } else {
        usleep(700000);
        $pokusy[$klic][] = time();
        @file_put_contents(pokusy_soubor($soukrome), json_encode($pokusy), LOCK_EX);
        $chyba = 'Heslo nesouhlasí.';
    }
}

if (!empty($_SESSION['ok'])) {
    $soubor = __DIR__ . '/app/emil-h22.html';
    if (!is_file($soubor)) { http_response_code(500); exit('Soubor simulátoru na serveru chybí.'); }
    header('Content-Type: text/html; charset=utf-8');
    header('Cache-Control: private, max-age=300');
    readfile($soubor);
    exit;
}

if (empty($_SESSION['csrf'])) { $_SESSION['csrf'] = bin2hex(random_bytes(16)); }
header('Cache-Control: no-store');
?><!doctype html>
<html lang="cs"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex, nofollow"><title>Přihlášení · Humanoid</title>
<style>body{margin:0;min-height:100vh;display:grid;place-items:center;background:#f4f1ea;color:#1f2a30;font:16px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}
form{width:min(340px,calc(100vw - 48px));background:#fffdf8;border:1px solid #d9d2c4;border-radius:14px;padding:24px}
h1{font-size:20px;margin:0 0 16px}label{display:block;font-weight:600;margin-bottom:6px}
input{width:100%;box-sizing:border-box;font:inherit;padding:10px;border:1px solid #c9c1b2;border-radius:8px}
button{margin-top:14px;width:100%;font:600 16px/1 inherit;padding:12px;border:0;border-radius:8px;background:#1f2a30;color:#fff;cursor:pointer}
p{color:#8a3a2a;margin:12px 0 0}input:focus-visible,button:focus-visible{outline:2px solid #ad653a;outline-offset:2px}</style></head>
<body><form method="post" action="./" autocomplete="on">
<h1>Humanoid · simulátor</h1>
<label for="heslo">Heslo</label>
<input type="password" id="heslo" name="heslo" autocomplete="current-password" required autofocus>
<input type="hidden" name="csrf" value="<?= htmlspecialchars((string) $_SESSION['csrf'], ENT_QUOTES) ?>">
<button type="submit">Přihlásit se</button>
<?php if ($chyba !== ''): ?><p role="alert"><?= htmlspecialchars($chyba, ENT_QUOTES) ?></p><?php endif; ?>
</form></body></html>
