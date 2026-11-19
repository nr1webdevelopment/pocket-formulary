<?php
/*
 * NomadCeuticals admin: shared code (config, database, sessions, GitHub). Included by report.php and admin/*.php.
 *
 * Private files live OUTSIDE the public website folder, next to public_html on Hostinger:
 *   nc-private/config.php    settings + password hash + GitHub token (written once by admin/setup.php)
 *   nc-private/nomad.sqlite  reports inbox, login attempts, audit log
 * Override the folder with the NC_PRIVATE_DIR environment variable (used for local testing).
 */
if (!defined('NC_ADMIN')) { http_response_code(404); exit; }

function nc_private_dir(): string {
    $env = getenv('NC_PRIVATE_DIR');
    if ($env) return rtrim($env, '/');
    $docroot = rtrim($_SERVER['DOCUMENT_ROOT'] ?? dirname(__DIR__), '/');
    return dirname($docroot) . '/nc-private';
}

function nc_config(): ?array {
    static $cfg = false;
    if ($cfg === false) {
        $f = nc_private_dir() . '/config.php';
        $cfg = is_file($f) ? require $f : null;
    }
    return $cfg;
}

function nc_db(): PDO {
    static $db = null;
    if ($db) return $db;
    $dir = nc_private_dir();
    if (!is_dir($dir)) { @mkdir($dir, 0700, true); }
    if (is_dir($dir) && !is_file("$dir/.htaccess")) { @file_put_contents("$dir/.htaccess", "Require all denied\nDeny from all\n"); }
    $db = new PDO('sqlite:' . $dir . '/nomad.sqlite', null, null, [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]);
    $db->exec('PRAGMA journal_mode=WAL; PRAGMA busy_timeout=5000;');
    $db->exec("CREATE TABLE IF NOT EXISTS reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT, created TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'new',
        category TEXT, about TEXT, record_id TEXT, page TEXT, lang TEXT, details TEXT NOT NULL, email TEXT,
        note TEXT, updated TEXT)");
    $db->exec("CREATE TABLE IF NOT EXISTS hits (kind TEXT NOT NULL, who TEXT NOT NULL, at INTEGER NOT NULL)");
    $db->exec("CREATE INDEX IF NOT EXISTS hits_idx ON hits(kind, who, at)");
    $db->exec("CREATE TABLE IF NOT EXISTS audit (at TEXT NOT NULL, user TEXT, action TEXT NOT NULL, detail TEXT)");
    return $db;
}

function nc_today(): string { return gmdate('Y-m-d'); }
function nc_now(): string { return gmdate('Y-m-d\TH:i:s\Z'); }

/* Who is calling, without storing IP addresses: a salted hash. */
function nc_client_hash(): string {
    $cfg = nc_config() ?? [];
    return hash('sha256', ($cfg['salt'] ?? 'nc') . '|' . ($_SERVER['REMOTE_ADDR'] ?? ''));
}

/* Rate limiting: count recent events of a kind for this client. */
function nc_hits(string $kind, int $window): int {
    $db = nc_db();
    $db->prepare('DELETE FROM hits WHERE at < ?')->execute([time() - 86400]);
    $q = $db->prepare('SELECT COUNT(*) FROM hits WHERE kind = ? AND who = ? AND at > ?');
    $q->execute([$kind, nc_client_hash(), time() - $window]);
    return (int)$q->fetchColumn();
}
function nc_hit(string $kind): void {
    nc_db()->prepare('INSERT INTO hits (kind, who, at) VALUES (?, ?, ?)')->execute([$kind, nc_client_hash(), time()]);
}

function nc_audit(string $action, string $detail = ''): void {
    nc_db()->prepare('INSERT INTO audit (at, user, action, detail) VALUES (?, ?, ?, ?)')
        ->execute([nc_now(), $_SESSION['user'] ?? null, $action, mb_substr($detail, 0, 500)]);
}

function nc_json($data, int $code = 200): void {
    http_response_code($code);
    header('Content-Type: application/json; charset=utf-8');
    header('Cache-Control: no-store');
    echo json_encode($data, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}

function nc_body(): array {
    $raw = file_get_contents('php://input', false, null, 0, 1048576);
    $d = json_decode($raw ?: '[]', true);
    return is_array($d) ? $d : [];
}

function nc_security_headers(): void {
    header('X-Frame-Options: DENY');
    header('X-Content-Type-Options: nosniff');
    header('Referrer-Policy: same-origin');
    header('X-Robots-Tag: noindex, nofollow');
    header('Cache-Control: no-store');
}

/* ---------- sessions (admin only) ---------- */
function nc_session(): void {
    if (session_status() === PHP_SESSION_ACTIVE) return;
    $secure = (($_SERVER['HTTPS'] ?? '') !== '' && $_SERVER['HTTPS'] !== 'off') || (($_SERVER['HTTP_X_FORWARDED_PROTO'] ?? '') === 'https');
    session_name('NCADMIN');
    session_set_cookie_params(['lifetime' => 0, 'path' => '/admin/', 'secure' => $secure, 'httponly' => true, 'samesite' => 'Strict']);
    session_start();
    // expire after 8 hours, or 2 hours without activity
    $now = time();
    if (!empty($_SESSION['user']) && (($now - ($_SESSION['started'] ?? 0)) > 8 * 3600 || ($now - ($_SESSION['seen'] ?? 0)) > 2 * 3600)) {
        $_SESSION = [];
        session_destroy();
        session_start();
    }
    $_SESSION['seen'] = $now;
}

function nc_require_login(): void {
    if (empty($_SESSION['user'])) nc_json(['error' => 'not_logged_in'], 401);
}

function nc_require_csrf(): void {
    $sent = $_SERVER['HTTP_X_CSRF_TOKEN'] ?? '';
    if (empty($_SESSION['csrf']) || !hash_equals($_SESSION['csrf'], $sent)) nc_json(['error' => 'bad_csrf'], 403);
}

/* ---------- GitHub (saving listings) ---------- */
function nc_github(string $method, string $path, ?array $body = null): array {
    $cfg = nc_config();
    $base = getenv('NC_GITHUB_API') ?: 'https://api.github.com';
    $ch = curl_init($base . $path);
    $headers = ['Accept: application/vnd.github+json', 'User-Agent: nomadceuticals-admin', 'X-GitHub-Api-Version: 2022-11-28',
                'Authorization: Bearer ' . $cfg['github_token']];
    if ($body !== null) $headers[] = 'Content-Type: application/json';
    curl_setopt_array($ch, [CURLOPT_CUSTOMREQUEST => $method, CURLOPT_RETURNTRANSFER => true, CURLOPT_HTTPHEADER => $headers,
                            CURLOPT_TIMEOUT => 30, CURLOPT_POSTFIELDS => $body !== null ? json_encode($body, JSON_UNESCAPED_SLASHES) : null]);
    $out = curl_exec($ch);
    $code = (int)curl_getinfo($ch, CURLINFO_HTTP_CODE);
    $err = curl_error($ch);
    curl_close($ch);
    return ['code' => $code, 'body' => $out === false ? null : json_decode($out, true), 'error' => $err];
}

/* Reads a JSON file from the repository branch; returns [data (objects, so {} stays {}), sha, text] or throws. */
function nc_repo_read(string $path): array {
    $cfg = nc_config();
    $r = nc_github('GET', '/repos/' . $cfg['github_repo'] . '/contents/' . $path . '?ref=' . rawurlencode($cfg['github_branch'] ?? 'main'));
    if ($r['code'] !== 200 || empty($r['body']['content'])) throw new RuntimeException("GitHub read failed ($r[code]) for $path");
    $text = base64_decode(str_replace("\n", '', $r['body']['content']));
    return [json_decode($text), $r['body']['sha'], $text];
}

/* Writes a JSON file to the repository branch (a commit). Fails with 409 if the file changed since $sha. */
function nc_repo_write(string $path, string $text, string $sha, string $message): array {
    $cfg = nc_config();
    return nc_github('PUT', '/repos/' . $cfg['github_repo'] . '/contents/' . $path, [
        'message' => $message, 'content' => base64_encode($text), 'sha' => $sha, 'branch' => $cfg['github_branch'] ?? 'main',
    ]);
}

/* Same formatting as the Python tools: indent like the original file, UTF-8, trailing newline. */
function nc_json_text($data, string $original): string {
    $indent = preg_match('/^\{\n( +)"/', $original, $m) ? strlen($m[1]) : 2;
    $text = json_encode($data, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_PRESERVE_ZERO_FRACTION | JSON_UNESCAPED_LINE_TERMINATORS);
    if ($indent !== 4) {
        $text = preg_replace_callback('/^( +)/m', fn($m) => str_repeat(' ', intdiv(strlen($m[1]), 4) * $indent), $text);
    }
    return $text . "\n";
}

/* ---------- validation (a small JSON Schema subset: what schema/provider.schema.json uses) ---------- */
function nc_type_ok($v, string $t): bool {
    switch ($t) {
        case 'null': return $v === null;
        case 'boolean': return is_bool($v);
        case 'integer': return is_int($v);
        case 'number': return is_int($v) || is_float($v);
        case 'string': return is_string($v);
        case 'array': return is_array($v) && array_is_list($v);
        case 'object': return $v instanceof stdClass;
    }
    return false;
}

function nc_validate($v, array $s, array $root, string $path, array &$errs): void {
    if (isset($s['$ref'])) {
        $ref = $root;
        foreach (explode('/', substr($s['$ref'], 2)) as $k) $ref = $ref[$k];
        nc_validate($v, $ref, $root, $path, $errs);
    }
    if (isset($s['oneOf'])) {
        $ok = 0;
        foreach ($s['oneOf'] as $sub) { $e = []; nc_validate($v, $sub, $root, $path, $e); if (!$e) $ok++; }
        if ($ok !== 1) $errs[] = "$path: not a valid value";
    }
    if (isset($s['type'])) {
        $types = (array)$s['type'];
        $ok = false;
        foreach ($types as $t) if (nc_type_ok($v, $t)) $ok = true;
        if (!$ok) { $errs[] = "$path: should be " . implode(' or ', $types); return; }
    }
    if (array_key_exists('enum', $s) && !in_array($v, $s['enum'], true)) $errs[] = "$path: must be one of " . implode(', ', array_map(fn($x) => $x === null ? 'empty' : $x, $s['enum']));
    if (is_string($v) && isset($s['pattern']) && !preg_match('/' . str_replace('/', '\/', $s['pattern']) . '/u', $v)) $errs[] = "$path: wrong format";
    if ((is_int($v) || is_float($v)) && ((isset($s['minimum']) && $v < $s['minimum']) || (isset($s['maximum']) && $v > $s['maximum']))) $errs[] = "$path: out of range";
    if (is_array($v)) {
        if (isset($s['minItems']) && count($v) < $s['minItems']) $errs[] = "$path: needs at least {$s['minItems']}";
        if (!empty($s['uniqueItems']) && count(array_unique(array_map('json_encode', $v))) !== count($v)) $errs[] = "$path: duplicates";
        if (isset($s['items'])) foreach ($v as $i => $x) nc_validate($x, $s['items'], $root, "$path/$i", $errs);
    }
    if ($v instanceof stdClass) {
        $props = $s['properties'] ?? [];
        foreach ($s['required'] ?? [] as $k) if (!property_exists($v, $k)) $errs[] = "$path/$k: required";
        foreach (get_object_vars($v) as $k => $x) {
            if (isset($props[$k])) nc_validate($x, $props[$k], $root, "$path/$k", $errs);
            elseif (($s['additionalProperties'] ?? true) === false) $errs[] = "$path/$k: unknown field";
            elseif (is_array($s['additionalProperties'] ?? null)) nc_validate($x, $s['additionalProperties'], $root, "$path/$k", $errs);
        }
    }
}

const NC_COND_SERVICES = ['hiv' => ['hivTesting', 'prep', 'pep', 'art'],
                          'adhd' => ['adhdAssessmentChildren', 'adhdAssessmentAdults', 'adhdMedication'],
                          'diabetes' => ['diabetesCare', 'diabetesCareChildren']];

/* Checks one provider record against the schema and the extra rules in scripts/validate.py. Returns a list of problems. */
function nc_validate_provider(stdClass $p, array $city): array {
    $schemaFile = rtrim($_SERVER['DOCUMENT_ROOT'], '/') . '/schema/provider.schema.json';
    $schema = json_decode(file_get_contents($schemaFile), true);
    $errs = [];
    nc_validate($p, $schema, $schema, '', $errs);
    $prefix = strtolower($city['country']) . '-' . $city['code'] . '-';
    if (!str_starts_with($p->id ?? '', $prefix)) $errs[] = "/id: must start with $prefix";
    if (($p->city ?? '') !== $city['code']) $errs[] = "/city: must be {$city['code']}";
    if (($p->location->country ?? '') !== $city['country']) $errs[] = "/location/country: must be {$city['country']}";
    if (empty($p->name->en)) $errs[] = '/name/en: required';
    foreach ($p->conditions ?? [] as $c) foreach (NC_COND_SERVICES[$c] ?? [] as $k)
        if (!property_exists($p->services ?? new stdClass, $k)) $errs[] = "/services/$k: needed for $c (leave as unknown if not sure)";
    $v = $p->verification ?? new stdClass;
    if (($v->status ?? '') === 'verified') foreach (['lastVerified', 'method', 'verifiedBy'] as $k)
        if (empty($v->$k)) $errs[] = "/verification/$k: needed when status is verified";
    return array_values(array_unique($errs));
}

/* City list from the built site (dist/v1/cities.json): code => {code, file, country, name} */
function nc_cities(): array {
    $doc = json_decode(file_get_contents(rtrim($_SERVER['DOCUMENT_ROOT'], '/') . '/dist/v1/cities.json'), true);
    $out = [];
    foreach ($doc['data'] as $c) $out[$c['code']] = ['code' => $c['code'], 'file' => $c['file'], 'country' => $c['country'], 'name' => $c['name']['en']];
    return $out;
}
