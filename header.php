<?php
// Page title for <title>. Override per page: $title = "About · TransformGov Talks";
if (!isset($title)) { $title = "TransformGov Talks"; }
?>
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title><?php echo htmlspecialchars($title); ?></title>
  <link rel="stylesheet" href="/styles.css" />
</head>
<body>
  <div class="page"><!-- PAGE GRID START -->

    <header role="banner" aria-label="Site header">
      <div class="header-inner">
        <!-- Logo + Title -->
        <img src="/images/logo.png" alt="TransformGov Talks logo" class="logo" />
        <h1><a href="/">TransformGov Talks</a></h1>

        <!-- Main nav (to the right of the title) -->
        <nav class="main-nav" aria-label="Main navigation">
          <a href="/about">About</a>
          <a href="https://medium.com/@transformgovtalks/introducing-transformgov-talks-f9b1c3bceb0f" target="_blank" rel="noopener">Blog</a>
          <a href="https://www.youtube.com/@TransformGovTalks" target="_blank" rel="noopener">Videos</a>
          <a href="https://sites.libsyn.com/534749" target="_blank" rel="noopener">Audio</a>
        </nav>

        <!-- Newsletter button + icons -->
        <a href="https://transformgov-talks.ck.page/b6dac7cdd5" target="_blank" rel="noopener" class="newsletter-button">Newsletter</a>

        <div class="social-icons" aria-label="Social & contact">
          <a href="mailto:transformgovtalks@gmail.com" aria-label="Email">
            <img src="/images/bluesky.svg" alt="">
          </a>
          <a href="#" aria-label="Social 1"><img src="/images/bluesky.svg" alt=""></a>
          <a href="#" aria-label="Social 2"><img src="/images/bluesky.svg" alt=""></a>
          <a href="#" aria-label="Social 3"><img src="/images/bluesky.svg" alt=""></a>
          <a href="#" aria-label="Social 4"><img src="/images/bluesky.svg" alt=""></a>
        </div>
      </div>
    </header>
