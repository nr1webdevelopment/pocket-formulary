<?php
/* NomadCeuticals admin: the page shell. Everything else happens in app.js via api.php. */
define('NC_ADMIN', 1);
require __DIR__ . '/_inc.php';
nc_security_headers();
header("Content-Security-Policy: default-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src https://fonts.gstatic.com; img-src 'self' data:; frame-ancestors 'none'; form-action 'self'; base-uri 'none'");
if (!nc_config()) { header('Location: setup.php'); exit; }
$v = substr(md5((string)@filemtime(__DIR__ . '/app.js') . @filemtime(__DIR__ . '/app.css')), 0, 8);
?><!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow"><title>Admin · NomadCeuticals</title>
<link rel="icon" href="/assets/logo-icon.svg">
<link rel="stylesheet" href="app.css?v=<?= $v ?>"></head>
<body>
<header class="bar" id="bar" hidden><div class="in">
  <a class="brand" href="#inbox">NomadCeuticals admin</a>
  <nav aria-label="Admin">
    <a href="#inbox" data-nav="inbox">Inbox<span class="badge" id="newcount" hidden></span></a>
    <a href="#listings" data-nav="listings">Listings</a>
    <a href="#settings" data-nav="settings">Settings</a>
  </nav>
  <div class="who"><span id="who"></span><a href="/" style="color:#fff">View site</a><button type="button" id="logout">Log out</button></div>
</div></header>
<main id="app"><p class="muted">Loading…</p></main>
<div id="toast" class="toast" hidden></div>
<script src="app.js?v=<?= $v ?>"></script>
</body></html>
