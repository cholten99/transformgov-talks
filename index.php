<?php
$title = "TransformGov Talks";
include "header.php";
?>

<main id="content">
  <h2>
    TransformGov Talks: Innovating <span class="highlight">Together</span>
  </h2>
  <p>
    We provide a space for people who care about making government work better 
    to meet, whether they're inside or outside government.
  </p>
  <p>
    Each monthly meet-up features presentations and discussions about innovation 
    in the public sector or great examples of impactful delivery of policy or services. 
    This is followed by plenty of time to chat after — with free pizza!
  </p>
  <p>
    Sign up to our newsletter above ☝️ to receive links to video and audio 
    recordings of our meetups and stay informed about upcoming events.
  </p>

  <?php
    // Robust: pick a valid speaker image and output it (or nothing if none)
    $speakerDir = __DIR__ . '/images/speakers';
    $speakerFiles = [];
    if (is_dir($speakerDir)) {
      $speakerFiles = glob($speakerDir . '/*.{jpg,jpeg,png,webp,avif,gif,JPG,JPEG,PNG,WEBP,AVIF,GIF}', GLOB_BRACE);
      $speakerFiles = array_values(array_filter($speakerFiles, 'is_file'));
    }

    $picked = null;
    if (!empty($speakerFiles)) {
      $maxTries = min(10, count($speakerFiles));
      for ($i = 0; $i < $maxTries; $i++) {
        $candidate = $speakerFiles[array_rand($speakerFiles)];
        if (@is_readable($candidate) && @getimagesize($candidate) !== false) {
          $picked = $candidate;
          break;
        }
      }
    }

    if ($picked) {
      $src = '/images/speakers/' . rawurlencode(basename($picked));
      echo '<div class="featured-speaker">';
      echo '<img src="' . htmlspecialchars($src) . '" alt="Past TransformGov Talks speaker" loading="lazy" decoding="async" />';
      echo '</div>';
    }
  ?>
</main>

<aside aria-label="Sidebar" id="sidebar">
  <!-- Top sidebar box -->
  <section class="sidebar-card" id="event-box">
    <h3>Our next event!</h3>
    <p>
      Next month, because many people are away enjoying the summer break, 
      we'll be doing something a bit different.
    </p>
    <p>
      Join us on the <strong>27th of August</strong> at the Buckingham Arms for 
      <em>TGT's first Summer Drinks!</em>
    </p>
    <p>
      <a href="https://lu.ma/sdzpnfl9" 
         class="button-link" 
         target="_blank" 
         rel="noopener noreferrer">
         Register now!
      </a>
    </p>
  </section>

  <!-- Bottom sidebar box with video -->
  <section class="sidebar-card" id="video-box">
    <h3>Watch our latest event</h3>
    <div style="position:relative; padding-bottom:56.25%; height:0; overflow:hidden; border-radius:6px;">
      <iframe src="https://www.youtube.com/embed/70xjXI_R6wo" 
              title="YouTube video player" 
              frameborder="0" 
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" 
              allowfullscreen
              style="position:absolute; top:0; left:0; width:100%; height:100%;">
      </iframe>
    </div>
  </section>
</aside>

<?php include 'footer.php'; ?>

