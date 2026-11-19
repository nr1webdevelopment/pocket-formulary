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
 *   POST ?a=test_email
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

case 'test_email':
    $to = $cfg['notify_email'] ?? '';
    if (!$to) nc_json(['error' => 'no_email'], 400);
    $from = $cfg['mail_from'];
    $ok = @mail($to, 'NomadCeuticals admin: test email', "This is a test from the NomadCeuticals admin. Report emails will look like they come from $from.\n",
                "From: NomadCeuticals <$from>\r\nContent-Type: text/plain; charset=UTF-8", "-f$from");
    nc_audit('test_email', $ok ? 'sent' : 'failed');
    nc_json(['ok' => $ok]);
}
nc_json(['error' => 'unknown_action'], 404);
