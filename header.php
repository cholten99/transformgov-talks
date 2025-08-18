<?php
  // header.php — full document head + page wrapper + site header
  if (!isset($title)) { $title = "TransformGov Talks"; }
?>
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title><?php echo htmlspecialchars($title); ?></title>
  <link rel="stylesheet" href="/styles.css" />
  <link rel="icon" type="image/png" href="/images/logo.png" />
</head>
<body>
  <div class="page"><!-- PAGE GRID START -->

    <header role="banner" aria-label="Site header">
      <div class="header-inner">
        <!-- Logo -->
        <a href="/" class="logo-link" aria-label="Home">
          <img src="/images/logo.png" alt="TransformGov Talks logo" class="logo" />
        </a>

        <!-- Site Title -->
        <h1><a href="/">TransformGov Talks</a></h1>

        <!-- Main Navigation -->
        <nav class="main-nav" aria-label="Main navigation">
          <a href="/about">About</a>
          <a href="https://medium.com/@transformgovtalks" target="_blank" rel="noopener">Blog</a>
          <a href="https://www.youtube.com/@TransformGovTalks" target="_blank" rel="noopener">Videos</a>
          <a href="https://sites.libsyn.com/534749" target="_blank" rel="noopener">Audio</a>
        </nav>

        <!-- Newsletter -->
        <a href="https://transformgov-talks.ck.page/b6dac7cdd5" target="_blank" rel="noopener" class="newsletter-button">Newsletter</a>

        <!-- Social / Contact Icons -->
        <div class="social-icons" aria-label="Social links">
          <a href="mailto:transformgovtalks@gmail.com" aria-label="Email">
            <img src="/images/icons/email.svg" alt="">
          </a>
          <a href="https://www.threads.net/@transformgovt" target="_blank" rel="noopener" aria-label="Threads">
            <img src="/images/icons/threads.svg" alt="">
          </a>
          <a href="https://bsky.app/profile/transformgovtalks.bsky.social" target="_blank" rel="noopener" aria-label="Bluesky">
            <img src="/images/icons/bluesky.svg" alt="">
          </a>
          <a href="https://www.facebook.com/profile.php?id=61557565844725" target="_blank" rel="noopener" aria-label="Facebook">
            <img src="/images/icons/facebook.svg" alt="">
          </a>
          <a href="https://www.linkedin.com/company/transformgov-talks/about/" target="_blank" rel="noopener" aria-label="LinkedIn">
            <img src="/images/icons/linkedin.svg" alt="">
          </a>
          <a href="https://mastodon.social/@transformgovtalks" target="_blank" rel="me noopener" aria-label="Mastodon">
            <img src="/images/icons/mastodon.svg" alt="">
          </a>
        </div>
      </div>
    </header>
