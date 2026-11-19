<?php
/*
 * NomadCeuticals admin API (JSON). Used by admin/app.js.
 *   GET  ?a=me                         who is logged in (+ CSRF token)
 *   POST ?a=login {username,password}  log in (5 failed tries per 15 minutes, then locked)
 *   POST ?a=logout
 *   GET  ?a=reports&status=new|in_progress|done|all
 *   POST ?a=report_update {id,status?,note?}
 *   POST ?a=report_delete {id}
 *   GET  ?a=cities                     cities with provider files
 *   GET  ?a=providers&city=bkk         that city's providers, read live from GitHub (+ file sha)
 *   POST ?a=provider_save {city, sha, original_id|null, record}   commit to GitHub
 *   GET  ?a=settings                   email + token settings (never returns secrets)
 *   POST ?a=save_email {notify_email, smtp_user, smtp_pass?, smtp_host, smtp_port}
 *   POST ?a=test_email                 send a test, returns the server's error if it fails
 *   POST ?a=replace_token {password, token}
 *   POST ?a=change_password {current, new}
 * Every POST except login needs the X-CSRF-Token header.
 */
define('NC_ADMIN', 1);
require __DIR__ . '/_inc.php';
nc_security_headers();

$cfg = nc_config();
if (!$cfg) nc_json(['error' => 'not_set_up'], 503);
nc_session();
$a = $_GET['a'] ?? '';
$post = $_SERVER['REQUEST_METHOD'] === 'POST';

if ($a === 'me') {
    if (empty($_SESSION['user'])) nc_json(['user' => null]);
    $new = (int)nc_db()->query("SELECT COUNT(*) FROM reports WHERE status = 'new'")->fetchColumn();
    nc_json(['user' => $_SESSION['user'], 'csrf' => $_SESSION['csrf'], 'newReports' => $new, 'repo' => $cfg['github_repo']]);
}

if ($a === 'login' && $post) {
    if (nc_hits('login_fail', 900) >= 5) nc_json(['error' => 'locked'], 429);
    $in = nc_body();
    $ok = hash_equals($cfg['admin_user'], (string)($in['username'] ?? '')) & password_verify((string)($in['password'] ?? ''), $cfg['password_hash']);
    if (!$ok) { nc_hit('login_fail'); usleep(400000); nc_json(['error' => 'wrong_login'], 401); }
    session_regenerate_id(true);
    $_SESSION = ['user' => $cfg['admin_user'], 'csrf' => bin2hex(random_bytes(32)), 'started' => time(), 'seen' => time()];
    nc_audit('login');
    nc_json(['ok' => true, 'user' => $_SESSION['user'], 'csrf' => $_SESSION['csrf']]);
}

nc_require_login();
if (!$post && !in_array($a, ['reports', 'cities', 'providers', 'settings'], true)) nc_json(['error' => 'post_only'], 405);
if ($post) nc_require_csrf();

switch ($a) {
case 'logout':
    nc_audit('logout');
    $_SESSION = [];
    session_destroy();
    nc_json(['ok' => true]);

case 'reports':
    $st = $_GET['status'] ?? 'new';
    $db = nc_db();
    if ($st === 'all') $q = $db->query('SELECT * FROM reports ORDER BY id DESC LIMIT 500');
    else { $q = $db->prepare('SELECT * FROM reports WHERE status = ? ORDER BY id DESC LIMIT 500'); $q->execute([$st]); }
    $counts = [];
    foreach ($db->query('SELECT status, COUNT(*) n FROM reports GROUP BY status') as $r) $counts[$r['status']] = (int)$r['n'];
    nc_json(['reports' => $q->fetchAll(PDO::FETCH_ASSOC), 'counts' => $counts]);

case 'report_update':
    $in = nc_body();
    $id = (int)($in['id'] ?? 0);
    $sets = []; $vals = [];
    if (isset($in['status'])) {
        if (!in_array($in['status'], ['new', 'in_progress', 'done'], true)) nc_json(['error' => 'bad_status'], 400);
        $sets[] = 'status = ?'; $vals[] = $in['status'];
    }
    if (array_key_exists('note', $in)) { $sets[] = 'note = ?'; $vals[] = mb_substr((string)$in['note'], 0, 4000); }
    if (!$sets) nc_json(['error' => 'nothing_to_change'], 400);
    $sets[] = 'updated = ?'; $vals[] = nc_now(); $vals[] = $id;
    nc_db()->prepare('UPDATE reports SET ' . implode(', ', $sets) . ' WHERE id = ?')->execute($vals);
    nc_audit('report_update', "#$id " . ($in['status'] ?? ''));
    nc_json(['ok' => true]);

case 'report_delete':
    $id = (int)(nc_body()['id'] ?? 0);
    nc_db()->prepare('DELETE FROM reports WHERE id = ?')->execute([$id]);
    nc_audit('report_delete', "#$id");
    nc_json(['ok' => true]);

case 'cities':
    nc_json(['cities' => array_values(nc_cities())]);

case 'providers':
    $cities = nc_cities();
    $city = $cities[$_GET['city'] ?? ''] ?? null;
    if (!$city) nc_json(['error' => 'unknown_city'], 404);
    try {
        [$doc, $sha] = nc_repo_read('data/providers/' . $city['file']);
    } catch (Throwable $e) {
        nc_json(['error' => 'github', 'message' => $e->getMessage()], 502);
    }
    nc_json(['city' => $city, 'sha' => $sha, 'providers' => $doc->providers ?? []]);

case 'provider_save':
    // Decode as objects so empty {} stays {} in the file.
    $in = json_decode(file_get_contents('php://input', false, null, 0, 1048576));
    if (!($in instanceof stdClass) || !($in->record ?? null) instanceof stdClass) nc_json(['error' => 'bad_request'], 400);
    $cities = nc_cities();
    $city = $cities[$in->city ?? ''] ?? null;
    if (!$city) nc_json(['error' => 'unknown_city'], 404);
    $rec = $in->record;
    $rec->updated = nc_today();
    $problems = nc_validate_provider($rec, $city);
    if ($problems) nc_json(['error' => 'invalid', 'problems' => $problems], 422);
    $path = 'data/providers/' . $city['file'];
    try {
        [$doc, $sha, $text] = nc_repo_read($path);
    } catch (Throwable $e) {
        nc_json(['error' => 'github', 'message' => $e->getMessage()], 502);
    }
    if (($in->sha ?? '') !== $sha) nc_json(['error' => 'changed', 'message' => 'This city was changed since you opened it. Reload and try again.'], 409);
    $orig = $in->original_id ?? null;
    $found = false;
    foreach ($doc->providers as $i => $p) {
        if ($orig !== null && $p->id === $orig) { $doc->providers[$i] = $rec; $found = true; }
        elseif ($p->id === $rec->id) nc_json(['error' => 'invalid', 'problems' => ["/id: {$rec->id} is already used by another listing"]], 422);
    }
    if ($orig !== null && !$found) nc_json(['error' => 'changed', 'message' => 'That listing is no longer in the file. Reload.'], 409);
    if ($orig === null) $doc->providers[] = $rec;
    $verb = $orig === null ? 'add' : (($in->action ?? '') === 'verify' ? 'verify' : (($in->action ?? '') === 'close' ? 'mark closed' : 'update'));
    $r = nc_repo_write($path, nc_json_text($doc, $text), $sha, "Admin: $verb {$rec->id}");
    if ($r['code'] === 409 || $r['code'] === 422 && str_contains(json_encode($r['body']), 'sha')) nc_json(['error' => 'changed', 'message' => 'This city was changed since you opened it. Reload and try again.'], 409);
    if ($r['code'] !== 200 && $r['code'] !== 201) {
        nc_audit('save_failed', "{$rec->id} GitHub {$r['code']}");
        nc_json(['error' => 'github', 'message' => 'GitHub said ' . $r['code'] . ': ' . ($r['body']['message'] ?? $r['error'])], 502);
    }
    nc_audit("provider_$verb", $rec->id);
    nc_json(['ok' => true, 'sha' => $r['body']['content']['sha'], 'commit' => $r['body']['commit']['html_url'] ?? null, 'record' => $rec]);

case 'settings':
    nc_json(['notify_email' => $cfg['notify_email'] ?? '', 'smtp_user' => $cfg['smtp_user'] ?? '', 'smtp_host' => $cfg['smtp_host'] ?? 'smtp.hostinger.com',
             'smtp_port' => (int)($cfg['smtp_port'] ?? 465), 'smtp_pass_set' => !empty($cfg['smtp_pass']), 'token_updated' => $cfg['token_updated'] ?? ($cfg['created'] ?? null)]);

case 'save_email':
    $in = nc_body();
    $notify = trim((string)($in['notify_email'] ?? ''));
    $user = trim((string)($in['smtp_user'] ?? ''));
    if (!filter_var($notify, FILTER_VALIDATE_EMAIL)) nc_json(['error' => 'bad_input', 'message' => 'Enter the address where report emails should go.'], 400);
    if ($user !== '' && !filter_var($user, FILTER_VALIDATE_EMAIL)) nc_json(['error' => 'bad_input', 'message' => 'The sending mailbox must be a full email address.'], 400);
    $host = preg_replace('/[^a-z0-9.-]/i', '', (string)($in['smtp_host'] ?? 'smtp.hostinger.com')) ?: 'smtp.hostinger.com';
    $port = (int)($in['smtp_port'] ?? 465);
    if (!in_array($port, [465, 587], true)) nc_json(['error' => 'bad_input', 'message' => 'Port must be 465 (SSL) or 587 (STARTTLS).'], 400);
    $changes = ['notify_email' => $notify, 'smtp_user' => $user, 'smtp_host' => $host, 'smtp_port' => $port];
    if (($in['smtp_pass'] ?? '') !== '') $changes['smtp_pass'] = (string)$in['smtp_pass'];
    if ($user === '') $changes['smtp_pass'] = '';
    if (!nc_save_config($changes)) nc_json(['error' => 'server', 'message' => "Couldn't write the settings file."], 500);
    nc_audit('save_email', $user ?: 'mail()');
    nc_json(['ok' => true]);

case 'test_email':
    $cfg = nc_config();
    $to = $cfg['notify_email'] ?? '';
    if (!$to) nc_json(['error' => 'no_email'], 400);
    $via = !empty($cfg['smtp_user']) ? "the mailbox {$cfg['smtp_user']}" : "PHP mail() (no sending mailbox set)";
    [$ok, $why] = nc_send_mail($to, 'NomadCeuticals admin: test email', "This is a test from the NomadCeuticals admin, sent through $via.\nIf you can read this, report emails will reach you.\n");
    nc_audit('test_email', $ok ? 'sent' : "failed: $why");
    nc_json(['ok' => $ok, 'message' => $why, 'via' => $via]);

case 'replace_token':
    $in = nc_body();
    if (!password_verify((string)($in['password'] ?? ''), $cfg['password_hash'])) { nc_hit('login_fail'); nc_json(['error' => 'bad_input', 'message' => 'Your current password is wrong.'], 400); }
    $token = trim((string)($in['token'] ?? ''));
    $base = getenv('NC_GITHUB_API') ?: 'https://api.github.com';
    $ch = curl_init($base . '/repos/' . $cfg['github_repo']);
    curl_setopt_array($ch, [CURLOPT_RETURNTRANSFER => true, CURLOPT_TIMEOUT => 20, CURLOPT_HTTPHEADER => [
        'Accept: application/vnd.github+json', 'User-Agent: nomadceuticals-admin', 'Authorization: Bearer ' . $token]]);
    $res = json_decode((string)curl_exec($ch), true);
    $code = (int)curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);
    if ($code === 401) nc_json(['error' => 'bad_input', 'message' => "GitHub didn't accept that token. Check you copied all of it."], 400);
    if ($code !== 200) nc_json(['error' => 'bad_input', 'message' => "The token can't see {$cfg['github_repo']} (GitHub said $code)."], 400);
    if (empty($res['permissions']['push'])) nc_json(['error' => 'bad_input', 'message' => "That token's account can't change {$cfg['github_repo']}."], 400);
    if (!nc_save_config(['github_token' => $token, 'token_updated' => nc_now()])) nc_json(['error' => 'server', 'message' => "Couldn't write the settings file."], 500);
    nc_audit('replace_token');
    nc_json(['ok' => true]);

case 'change_password':
    $in = nc_body();
    if (!password_verify((string)($in['current'] ?? ''), $cfg['password_hash'])) { nc_hit('login_fail'); nc_json(['error' => 'bad_input', 'message' => 'Your current password is wrong.'], 400); }
    $new = (string)($in['new'] ?? '');
    if (mb_strlen($new) < 12) nc_json(['error' => 'bad_input', 'message' => 'The new password needs at least 12 characters.'], 400);
    if (!nc_save_config(['password_hash' => password_hash($new, PASSWORD_DEFAULT)])) nc_json(['error' => 'server', 'message' => "Couldn't write the settings file."], 500);
    nc_audit('change_password');
    nc_json(['ok' => true]);
}
nc_json(['error' => 'unknown_action'], 404);
