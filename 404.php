<?php
http_response_code(404);
$title = "Page Not Found · TransformGov Talks";
include "header.php";
?>

<main id="content" class="fullwidth">
  <h2>Page Not Found (404)</h2>
  <p>
    Sorry, the page you’re looking for doesn’t exist. 
    It might have been moved or deleted.
  </p>
  <p>
    👉 <a href="index.php" class="button-link">Back to Home</a>
  </p>
</main>

<?php include "footer.php"; ?>
