Drop the self-hosted font files here before building the zip:

  sora-latin-700-normal.woff2
  hanken-grotesk-latin-400-normal.woff2
  jetbrains-mono-latin-400-normal.woff2

These filenames must match the fontFace src entries in theme.json.
theme/build.py reports any that are missing but still builds the zip.
