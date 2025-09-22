<?php
$title = "Page not found (404) – TransformGov Talks";
include "header.php";

// Friendly path for message
$requested = htmlspecialchars($_SERVER['REQUEST_URI'] ?? '', ENT_QUOTES, 'UTF-8');
?>

<main id="content" class="full-main">
  <h2>Page not found (404)</h2>
  <p>Sorry — we couldn’t find a page at <code><?php echo $requested; ?></code>.</p>

  <p>It may have moved, been renamed, or never existed. Try one of these:</p>
  <ul>
    <li><a href="/">Home</a></li>
    <li><a href="/about">About</a></li>
    <li><a href="https://medium.com/@transformgovtalks" target="_blank" rel="noopener">Blog</a></li>
    <li><a href="https://www.youtube.com/@TransformGovTalks" target="_blank" rel="noopener">Videos</a></li>
    <li><a href="https://sites.libsyn.com/534749" target="_blank" rel="noopener">Audio</a></li>
    <li><a href="https://transformgov-talks.ck.page/b6dac7cdd5" target="_blank" rel="noopener">Newsletter</a></li>
  </ul>

  <p><a class="button-link" href="/">Go to the homepage</a></p>

  <p style="margin-top:0.75rem">
    If you think this is a broken link on our site, please let us know at
    <a href="mailto:transformgovtalks@gmail.com">transformgovtalks@gmail.com</a>.
  </p>
</main>

<?php include 'footer.php'; ?>

