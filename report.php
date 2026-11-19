<?php
/*
 * NomadCeuticals: receives "Report a problem" messages from the website and puts them in the admin inbox.
 * POST /report.php  JSON {category, details, email?, about?, record_id?, page?, lang?, website (honeypot)}
 * Stored in the private SQLite database (see admin/_inc.php), and emailed to the admin if set up.
 */
define('NC_ADMIN', 1);
require __DIR__ . '/admin/_inc.php';
header('X-Robots-Tag: noindex');

if ($_SERVER['REQUEST_METHOD'] !== 'POST') nc_json(['error' => 'method_not_allowed'], 405);

// Same-origin only: the browser sends Origin on POST; refuse other websites.
$origin = $_SERVER['HTTP_ORIGIN'] ?? '';
$host = $_SERVER['HTTP_HOST'] ?? '';
if ($origin !== '' && parse_url($origin, PHP_URL_HOST) !== preg_replace('/:\d+$/', '', $host)) nc_json(['error' => 'forbidden'], 403);

$in = nc_body();
// Honeypot: real people never fill this hidden field. Pretend it worked.
if (!empty($in['website'])) nc_json(['ok' => true]);

try {
    if (nc_hits('report', 600) >= 5 || nc_hits('report', 86400) >= 20) nc_json(['error' => 'too_many'], 429);

    $cats = ['wrong_info', 'closed', 'site_bug', 'suggestion', 'other'];
    $cat = in_array($in['category'] ?? '', $cats, true) ? $in['category'] : 'other';
    $clean = fn($v, $n) => mb_substr(trim(preg_replace('/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/u', '', (string)($v ?? ''))), 0, $n);
    $details = $clean($in['details'] ?? '', 4000);
    if (mb_strlen($details) < 3) nc_json(['error' => 'details_required'], 400);
    $email = $clean($in['email'] ?? '', 200);
    if ($email !== '' && !filter_var($email, FILTER_VALIDATE_EMAIL)) nc_json(['error' => 'bad_email'], 400);
    $rid = $clean($in['record_id'] ?? '', 100);
    if ($rid !== '' && !preg_match('/^[a-z0-9-]+$/', $rid)) $rid = '';
    $line = fn($v, $n) => preg_replace('/\s+/u', ' ', $clean($v, $n));  // single-line fields
    $row = [nc_now(), $cat, $line($in['about'] ?? '', 200), $rid, $line($in['page'] ?? '', 500), $line($in['lang'] ?? '', 10), $details, $email ?: null];

    nc_db()->prepare('INSERT INTO reports (created, category, about, record_id, page, lang, details, email) VALUES (?, ?, ?, ?, ?, ?, ?, ?)')->execute($row);
    $id = (int)nc_db()->lastInsertId();
    nc_hit('report');
} catch (Throwable $e) {
    error_log('report.php: ' . $e->getMessage());
    nc_json(['error' => 'server'], 500);
}

// Email the admin (never blocks the visitor's success message).
$cfg = nc_config();
if ($cfg && !empty($cfg['notify_email'])) {
    $labels = ['wrong_info' => 'Wrong or out-of-date information', 'closed' => 'Closed, moved or no longer offers this',
               'site_bug' => 'Something on the site doesn\'t work', 'suggestion' => 'Suggestion', 'other' => 'Something else'];
    $site = 'https://' . preg_replace('/[^a-z0-9.:-]/i', '', $host);
    $subject = 'NomadCeuticals report #' . $id . ': ' . $labels[$cat] . ($row[2] !== '' ? ' · ' . $row[2] : '');
    $body = "New report #$id\n\nType: {$labels[$cat]}\n" . ($row[2] !== '' ? "About: {$row[2]}\n" : '') . ($rid !== '' ? "Listing: $rid\n" : '')
          . ($row[4] !== '' ? "Page: {$row[4]}\n" : '') . ($row[5] !== '' ? "Language: {$row[5]}\n" : '') . "\n$details\n\n"
          . ($email !== '' ? "Reply to: $email\n" : "No reply address given.\n") . "\nOpen the inbox: $site/admin/#report-$id\n";
    [$sent, $why] = nc_send_mail($cfg['notify_email'], $subject, $body, $email !== '' ? $email : null);
    if (!$sent) { error_log("report.php: email failed: $why"); nc_audit('report_email_failed', $why); }
}
nc_json(['ok' => true]);
