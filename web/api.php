<?php
declare(strict_types=1);
// Humanoid – odeslání úpravy kloubů k automatickému přepočtu v GitHubu a stav přepočtů. Jen po přihlášení.
require __DIR__ . '/soukrome/jadro.php';
robot_hlavicky();
header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');

function odpoved(int $kod, array $data): void { http_response_code($kod); echo json_encode($data, JSON_UNESCAPED_UNICODE); exit; }
$tajne = robot_tajne();
if ($tajne === null) { odpoved(503, ['chyba' => 'Server není nastavený.']); }
robot_relace();
if (empty($_SESSION['ok'])) { odpoved(401, ['chyba' => 'Nejsi přihlášený.']); }
$csrf = (string) ($_SERVER['HTTP_X_ROBOT_CSRF'] ?? '');
if ($csrf === '' || !hash_equals((string) ($_SESSION['csrf'] ?? ''), $csrf)) { odpoved(403, ['chyba' => 'Platnost stránky vypršela, načti ji znovu.']); }
session_write_close();

$token = (string) ($tajne['gh'] ?? '');
if ($token === '') { odpoved(503, ['chyba' => 'Přepočet není zapnutý: v GitHubu chybí secret PREPOCET_TOKEN.']); }
$evidence = __DIR__ . '/soukrome/prepocty.json';

function gh(string $metoda, string $cesta, string $token, ?array $telo = null, string $accept = 'application/vnd.github+json'): array {
    $url = 'https://api.github.com/repos/' . REPO . $cesta;
    $hl = ['Authorization: Bearer ' . $token, 'Accept: ' . $accept, 'X-GitHub-Api-Version: 2022-11-28', 'User-Agent: humanoid-simulator'];
    if ($telo !== null) { $hl[] = 'Content-Type: application/json'; }
    $ch = curl_init($url);
    curl_setopt_array($ch, [CURLOPT_CUSTOMREQUEST => $metoda, CURLOPT_HTTPHEADER => $hl, CURLOPT_RETURNTRANSFER => true, CURLOPT_TIMEOUT => 20,
        CURLOPT_POSTFIELDS => $telo === null ? null : json_encode($telo, JSON_UNESCAPED_UNICODE)]);
    $body = curl_exec($ch); $kod = (int) curl_getinfo($ch, CURLINFO_RESPONSE_CODE); curl_close($ch);
    return [$kod, is_string($body) ? $body : ''];
}
function evidence_nacti(string $f): array { $d = @json_decode((string) @file_get_contents($f), true); return is_array($d) ? $d : []; }

$akce = (string) ($_GET['akce'] ?? '');

if ($akce === 'odeslat' && ($_SERVER['REQUEST_METHOD'] ?? '') === 'POST') {
    $vstup = json_decode((string) file_get_contents('php://input'), true);
    $up = is_array($vstup) ? ($vstup['upravy'] ?? null) : null;
    if (!is_array($up) || !$up) { odpoved(400, ['chyba' => 'Žádná úprava k odeslání.']); }
    $cist = [];
    foreach ($up as $k => $e) {
        $j = (int) $k;
        if ((string) $j !== (string) $k || $j < 2 || $j > 20 || in_array($j, [11], true) || !is_array($e)) { odpoved(400, ['chyba' => "Kloub $k nelze upravit."]); }
        $d = $e['posun_mm'] ?? null;
        if (!is_array($d) || count($d) !== 3) { odpoved(400, ['chyba' => "Kloub $k: chybí posun."]); }
        $d = array_map(fn($v) => is_numeric($v) ? (float) $v : NAN, array_values($d));
        foreach ($d as $v) { if (!is_finite($v) || abs($v) > 40) { odpoved(400, ['chyba' => "Kloub $k: posun musí být v rozsahu ±40 mm."]); } }
        $rt = is_numeric($e['natoceni_serva_deg'] ?? 0) ? (float) ($e['natoceni_serva_deg'] ?? 0) : 0.0;
        $cist[(string) $j] = ['kloub' => mb_substr((string) ($e['kloub'] ?? ''), 0, 80), 'posun_mm' => $d, 'nese_dalsi_dily' => (bool) ($e['nese_dalsi_dily'] ?? false), 'natoceni_serva_deg' => max(-180.0, min(180.0, $rt))];
    }
    $ev = evidence_nacti($evidence);
    $hodina = array_filter($ev, fn($r) => time() - (int) ($r['cas'] ?? 0) < 3600);
    if (count($hodina) >= 10) { odpoved(429, ['chyba' => 'Za poslední hodinu už bylo odesláno 10 přepočtů. Zkus to později.']); }
    ksort($cist);
    $id = gmdate('Ymd-His') . '-' . substr(hash('sha256', json_encode($cist)), 0, 6);
    [$kod, $body] = gh('POST', '/actions/workflows/prepocet.yml/dispatches', $token,
        ['ref' => 'main', 'inputs' => ['uprava' => json_encode(['upravy' => $cist], JSON_UNESCAPED_UNICODE), 'id' => $id, 'rychle' => !empty($vstup['rychle'])]]);
    if ($kod !== 204) { odpoved(502, ['chyba' => 'GitHub přepočet nepřijal (HTTP ' . $kod . ').']); }
    array_unshift($ev, ['id' => $id, 'cas' => time(), 'upravy' => $cist, 'rychle' => !empty($vstup['rychle'])]);
    @file_put_contents($evidence, json_encode(array_slice($ev, 0, 100), JSON_UNESCAPED_UNICODE), LOCK_EX);
    odpoved(200, ['id' => $id]);
}

if ($akce === 'seznam') {
    $ev = array_slice(evidence_nacti($evidence), 0, 20);
    [$kod, $body] = gh('GET', '/actions/workflows/prepocet.yml/runs?per_page=50', $token);
    $behy = [];
    if ($kod === 200) { foreach ((json_decode($body, true)['workflow_runs'] ?? []) as $r) { $behy[(string) $r['display_title']] = $r; } }
    $out = [];
    foreach ($ev as $r) {
        $b = $behy['Přepočet ' . $r['id']] ?? null;
        $polozka = ['id' => $r['id'], 'cas' => $r['cas'], 'upravy' => $r['upravy'], 'rychle' => $r['rychle'] ?? false,
            'stav' => $b ? $b['status'] : 'ceka', 'zaver' => $b['conclusion'] ?? null, 'odkaz' => $b['html_url'] ?? null];
        if ($b && $b['status'] === 'completed') {
            [$k2, $v] = gh('GET', '/contents/prepocty/' . rawurlencode($r['id']) . '/vysledek.json?ref=prepocty', $token, null, 'application/vnd.github.raw+json');
            if ($k2 === 200) { $polozka['vysledek'] = json_decode($v, true); }
        }
        $out[] = $polozka;
    }
    odpoved(200, ['prepocty' => $out]);
}
odpoved(400, ['chyba' => 'Neznámá akce.']);
