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
    // přepočty spuštěné mimo aplikaci (ručně v GitHubu, Claude/GPT) nejsou v evidenci serveru – doplnit z větve prepocty
    $zname = array_column(evidence_nacti($evidence), 'id');
    [$k3, $v3] = gh('GET', '/contents/prepocty?ref=prepocty', $token);
    $cizi = [];
    if ($k3 === 200) {
        foreach ((json_decode($v3, true) ?: []) as $f) {
            $n = (string) ($f['name'] ?? '');
            if (($f['type'] ?? '') === 'dir' && preg_match('/^(\d{8})-(\d{6})-[0-9a-f]{6}$/', $n) && !in_array($n, $zname, true)) { $cizi[] = $n; }
        }
    }
    rsort($cizi);
    foreach (array_slice($cizi, 0, 6) as $id) {
        [$ka, $va] = gh('GET', '/contents/prepocty/' . rawurlencode($id) . '/vysledek.json?ref=prepocty', $token, null, 'application/vnd.github.raw+json');
        [$kb, $vb] = gh('GET', '/contents/prepocty/' . rawurlencode($id) . '/uprava.json?ref=prepocty', $token, null, 'application/vnd.github.raw+json');
        $vys = $ka === 200 ? json_decode($va, true) : null; $upr = $kb === 200 ? json_decode($vb, true) : null;
        if (!is_array($vys)) { continue; }
        $cas = DateTime::createFromFormat('Ymd-His', substr($id, 0, 15), new DateTimeZone('UTC'));
        $out[] = ['id' => $id, 'cas' => $cas ? $cas->getTimestamp() : 0, 'upravy' => is_array($upr) ? ($upr['upravy'] ?? []) : [], 'rychle' => !empty($vys['rychla']),
            'stav' => 'completed', 'zaver' => !empty($vys['proslo']) ? 'success' : 'failure', 'odkaz' => null, 'vysledek' => $vys, 'mimo_aplikaci' => true];
    }
    usort($out, fn($a, $b) => $b['cas'] <=> $a['cas']);
    odpoved(200, ['prepocty' => array_slice($out, 0, 20)]);
}
// ---------- vydání: nová revize a nasazení přímo z aplikace (jen majitel po přihlášení) ----------
function gh_behy(string $wf, string $token, int $n = 10): array {
    [$kod, $body] = gh('GET', '/actions/workflows/' . $wf . '/runs?per_page=' . $n, $token);
    if ($kod !== 200) { return []; }
    return array_map(fn($r) => ['nazev' => (string) $r['display_title'], 'stav' => (string) $r['status'], 'zaver' => $r['conclusion'] ?? null,
        'commit' => substr((string) $r['head_sha'], 0, 40), 'cas' => strtotime((string) $r['created_at']), 'odkaz' => (string) $r['html_url']],
        json_decode($body, true)['workflow_runs'] ?? []);
}
function gh_main(string $token): array {
    [$kod, $body] = gh('GET', '/commits/main', $token);
    $c = $kod === 200 ? json_decode($body, true) : [];
    return ['commit' => (string) ($c['sha'] ?? ''), 'zprava' => mb_substr(strtok((string) ($c['commit']['message'] ?? ''), "\n"), 0, 140), 'cas' => strtotime((string) ($c['commit']['committer']['date'] ?? '')) ?: null];
}
function posledni(array $behy, string $rezim, ?string $commit = null): ?array {
    foreach ($behy as $b) { if (str_contains($b['nazev'], '· ' . $rezim) && ($commit === null || $b['commit'] === $commit)) { return $b; } }
    return null;
}

if ($akce === 'vydani') {
    $main = gh_main($token); $nas = gh_behy('nasazeni.yml', $token); $rev = gh_behy('nova-revize.yml', $token, 5);
    $ostre = null; foreach ($nas as $b) { if (str_contains($b['nazev'], '· nasazeni') && $b['zaver'] === 'success') { $ostre = $b; break; } }
    $zk = posledni($nas, 'zkouska', $main['commit']);
    odpoved(200, ['main' => $main, 'nasazeno' => $ostre, 'zkouska' => $zk, 'bezi' => array_values(array_filter($nas, fn($b) => $b['stav'] !== 'completed')),
        'nasazeni' => array_slice($nas, 0, 5), 'revize' => $rev]);
}

if (in_array($akce, ['nasadit', 'revize'], true) && ($_SERVER['REQUEST_METHOD'] ?? '') === 'POST') {
    $vstup = json_decode((string) file_get_contents('php://input'), true) ?: [];
    $log = __DIR__ . '/soukrome/vydani.json'; $ev = evidence_nacti($log);
    if (count(array_filter($ev, fn($r) => time() - (int) ($r['cas'] ?? 0) < 3600)) >= 12) { odpoved(429, ['chyba' => 'Za poslední hodinu už bylo spuštěno 12 akcí. Zkus to později.']); }
    if ($akce === 'nasadit') {
        $rezim = (string) ($vstup['rezim'] ?? '');
        if (!in_array($rezim, ['zkouska', 'nasazeni'], true)) { odpoved(400, ['chyba' => 'Neznámý režim.']); }
        $nas = gh_behy('nasazeni.yml', $token);
        if (array_filter($nas, fn($b) => $b['stav'] !== 'completed')) { odpoved(409, ['chyba' => 'Nasazení už běží, počkej na dokončení.']); }
        if ($rezim === 'nasazeni') {
            // ostré nasazení jen po prošlé zkoušce téhož commitu (pravidlo: kontrola → zkouška → nasazení → ověření)
            $main = gh_main($token); $zk = posledni($nas, 'zkouska', $main['commit']);
            if (!$zk || $zk['zaver'] !== 'success') { odpoved(409, ['chyba' => 'Nejdřív musí projít zkouška nasazení pro aktuální verzi.']); }
            if (($vstup['commit'] ?? '') !== $main['commit']) { odpoved(409, ['chyba' => 'Mezitím vznikla nová verze. Načti stav znovu a spusť zkoušku.']); }
        }
        [$kod] = gh('POST', '/actions/workflows/nasazeni.yml/dispatches', $token, ['ref' => 'main', 'inputs' => ['rezim' => $rezim]]);
        if ($kod !== 204) { odpoved(502, ['chyba' => 'GitHub spuštění nepřijal (HTTP ' . $kod . ').']); }
    } else {
        $id = (string) ($vstup['id'] ?? '');
        if (!preg_match('/^[A-Za-z0-9-]{4,40}$/', $id)) { odpoved(400, ['chyba' => 'Neplatné označení přepočtu.']); }
        [$k2, $v] = gh('GET', '/contents/prepocty/' . rawurlencode($id) . '/vysledek.json?ref=prepocty', $token, null, 'application/vnd.github.raw+json');
        $r = $k2 === 200 ? json_decode($v, true) : null;
        if (!$r || empty($r['proslo']) || !empty($r['rychla'])) { odpoved(409, ['chyba' => 'Novou revizi jde udělat jen z prošlé plné kontroly.']); }
        if (array_filter(gh_behy('nova-revize.yml', $token, 5), fn($b) => $b['stav'] !== 'completed')) { odpoved(409, ['chyba' => 'Nová revize už se počítá.']); }
        [$kod] = gh('POST', '/actions/workflows/nova-revize.yml/dispatches', $token, ['ref' => 'main', 'inputs' => ['id' => $id]]);
        if ($kod !== 204) { odpoved(502, ['chyba' => 'GitHub spuštění nepřijal (HTTP ' . $kod . ').']); }
    }
    array_unshift($ev, ['cas' => time(), 'akce' => $akce, 'rezim' => $vstup['rezim'] ?? null, 'id' => $vstup['id'] ?? null]);
    @file_put_contents($log, json_encode(array_slice($ev, 0, 100), JSON_UNESCAPED_UNICODE), LOCK_EX);
    odpoved(200, ['ok' => true]);
}
odpoved(400, ['chyba' => 'Neznámá akce.']);
