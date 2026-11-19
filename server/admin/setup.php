<?php
/*
 * NomadCeuticals admin: one-time setup. Creates nc-private/config.php (outside the website folder) with your
 * login and GitHub token. Only works while no config exists, and only with a GitHub token that belongs to an
 * account allowed to push to the repository, so nobody else can claim the admin.
 * To start over (e.g. forgotten password): delete nc-private/config.php in Hostinger's File Manager, then open this page again.
 */
define('NC_ADMIN', 1);
require __DIR__ . '/_inc.php';
nc_security_headers();
header("Content-Security-Policy: default-src 'none'; style-src 'self' https://fonts.googleapis.com; font-src https://fonts.gstatic.com; img-src 'self'; form-action 'self'; frame-ancestors 'none'");

const NC_REPO = 'nr1webdevelopment/pocket-formulary';
$h = fn($s) => htmlspecialchars((string)$s, ENT_QUOTES, 'UTF-8');
$errors = [];
$done = false;
$already = nc_config() !== null;
$host = preg_replace('/^www\./', '', preg_replace('/:\d+$/', '', $_SERVER['HTTP_HOST'] ?? 'nomadceuticals.com'));
$in = ['username' => '', 'email' => ''];

if (!$already && $_SERVER['REQUEST_METHOD'] === 'POST') {
    if (nc_hits('setup', 3600) >= 10) { $errors[] = 'Too many attempts. Try again in an hour.'; }
    else {
        nc_hit('setup');
        $in['username'] = trim($_POST['username'] ?? '');
        $in['email'] = trim($_POST['email'] ?? '');
        $pw = (string)($_POST['password'] ?? '');
        $token = trim($_POST['token'] ?? '');
        if (!preg_match('/^[A-Za-z0-9._@-]{3,60}$/', $in['username'])) $errors[] = 'Username: 3–60 letters, numbers, dots, dashes or @.';
        if (mb_strlen($pw) < 12) $errors[] = 'Password: at least 12 characters.';
        if ($pw !== (string)($_POST['password2'] ?? '')) $errors[] = 'The two passwords don\'t match.';
        if (!filter_var($in['email'], FILTER_VALIDATE_EMAIL)) $errors[] = 'Enter the email address where report notifications should go.';
        if ($token === '') $errors[] = 'Paste your GitHub token.';
        if (!$errors) {
            $base = getenv('NC_GITHUB_API') ?: 'https://api.github.com';
            $ch = curl_init($base . '/repos/' . NC_REPO);
            curl_setopt_array($ch, [CURLOPT_RETURNTRANSFER => true, CURLOPT_TIMEOUT => 20, CURLOPT_HTTPHEADER => [
                'Accept: application/vnd.github+json', 'User-Agent: nomadceuticals-admin', 'Authorization: Bearer ' . $token]]);
            $res = json_decode((string)curl_exec($ch), true);
            $code = (int)curl_getinfo($ch, CURLINFO_HTTP_CODE);
            curl_close($ch);
            if ($code === 401) $errors[] = 'GitHub didn\'t accept that token. Check you copied all of it and that it hasn\'t expired.';
            elseif ($code !== 200) $errors[] = "The token can't see the repository " . NC_REPO . " (GitHub said $code). Make sure it has access to that repository.";
            elseif (empty($res['permissions']['push'])) $errors[] = 'That token belongs to an account that can\'t change ' . NC_REPO . '.';
        }
        if (!$errors) {
            $dir = nc_private_dir();
            if (!is_dir($dir) && !@mkdir($dir, 0700, true)) $errors[] = "Couldn't create the private folder $dir. Create a folder called nc-private next to public_html in File Manager, then try again.";
            else {
                $config = [
                    'admin_user' => $in['username'],
                    'password_hash' => password_hash($pw, PASSWORD_DEFAULT),
                    'github_token' => $token,
                    'github_repo' => NC_REPO,
                    'github_branch' => 'main',
                    'notify_email' => $in['email'],
                    'mail_from' => 'noreply@' . $host,
                    'salt' => bin2hex(random_bytes(16)),
                    'created' => nc_now(),
                ];
                $php = "<?php\n// NomadCeuticals admin settings. Written by admin/setup.php. Keep private: never upload to GitHub.\nreturn " . var_export($config, true) . ";\n";
                $file = "$dir/config.php";
                $fh = @fopen($file, 'x');  // 'x' fails if it already exists
                if (!$fh) $errors[] = "Couldn't write $file (or it already exists).";
                else { fwrite($fh, $php); fclose($fh); @chmod($file, 0600); @file_put_contents("$dir/.htaccess", "Require all denied\nDeny from all\n"); $done = true; nc_db(); }
            }
        }
    }
}
?><!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow"><title>Set up admin · NomadCeuticals</title>
<link rel="stylesheet" href="app.css"></head>
<body class="setup"><main class="card narrow">
<h1>NomadCeuticals admin setup</h1>
<?php if ($done): ?>
  <p class="msg ok">Done. Your admin account is set up.</p>
  <p><a class="btn primary" href="./">Go to the admin and log in</a></p>
<?php elseif ($already): ?>
  <p>The admin is already set up. <a href="./">Log in</a>.</p>
  <p class="muted">Forgot your password? In Hostinger's File Manager, delete <code>nc-private/config.php</code> (the folder next to public_html), then come back to this page.</p>
<?php else: ?>
  <p>Do this once. Your password is stored only as a secure hash, and everything is kept in a private folder outside the website.</p>
  <?php foreach ($errors as $e): ?><p class="msg err"><?= $h($e) ?></p><?php endforeach; ?>
  <form method="post" autocomplete="off" class="stack">
    <label>Username<input name="username" required value="<?= $h($in['username']) ?>" autocomplete="username"></label>
    <label>Password <small>at least 12 characters</small><input type="password" name="password" required minlength="12" autocomplete="new-password"></label>
    <label>Password again<input type="password" name="password2" required minlength="12" autocomplete="new-password"></label>
    <label>Email for new reports <small>never shown on the website</small><input type="email" name="email" required value="<?= $h($in['email']) ?>"></label>
    <label>GitHub token <small>fine-grained token with Contents: read and write on <?= $h(NC_REPO) ?> only</small><input type="password" name="token" required autocomplete="off"></label>
    <button class="btn primary" type="submit">Set up admin</button>
  </form>
<?php endif; ?>
</main></body></html>
