{
  echo '['
  first=1
  # Adjust extensions as needed
  find . -maxdepth 1 -type f \( -iname '*.svg' -o -iname '*.png' -o -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.webp' -o -iname '*.gif' \) -printf '%f\n' \
    | sort -f \
    | while IFS= read -r f; do
        alt="$(printf '%s' "${f%.*}" | tr '_-' ' ' | sed -E 's/(^| )([a-z])/\1\u\2/g')"
        if [ $first -eq 0 ]; then echo ','; fi
        printf '{"src":"/images/slides/%s","alt":"%s"}' "$f" "$alt"
        first=0
      done
  echo
  echo ']'
} > manifest.json
