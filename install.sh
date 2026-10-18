#!/bin/bash
# One-line installer for Brag Book (macOS / Linux). No pip or git needed, just python3.
#   curl -fsSL https://raw.githubusercontent.com/frenchgal291198-cyber/workmemroyapp/claude/activity-brag-book-tool-9ekn2h/install.sh | bash
set -euo pipefail

REPO="frenchgal291198-cyber/workmemroyapp"
BRANCH="${BRAGBOOK_BRANCH:-claude/activity-brag-book-tool-9ekn2h}"
APP_DIR="$HOME/.bragbook/app"
BIN_DIR="$HOME/.local/bin"

if ! command -v python3 >/dev/null 2>&1 || ! python3 -c "import sys; assert sys.version_info >= (3, 9)" 2>/dev/null; then
  echo "Brag Book needs Python 3.9 or newer."
  if [ "$(uname)" = "Darwin" ]; then
    echo "Run:  xcode-select --install   (click Install in the pop-up), then run this installer again."
  fi
  exit 1
fi

echo "Downloading Brag Book…"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
curl -fsSL "https://github.com/$REPO/archive/refs/heads/$BRANCH.tar.gz" -o "$TMP/bragbook.tar.gz"
tar -xzf "$TMP/bragbook.tar.gz" -C "$TMP"
SRC="$(find "$TMP" -mindepth 1 -maxdepth 1 -type d | head -n 1)"

rm -rf "$APP_DIR"
mkdir -p "$APP_DIR" "$BIN_DIR"
cp -R "$SRC/bragbook" "$APP_DIR/"

cat > "$BIN_DIR/bragbook" <<EOF
#!/bin/bash
PYTHONPATH="$APP_DIR\${PYTHONPATH:+:\$PYTHONPATH}" exec "$(command -v python3)" -m bragbook "\$@"
EOF
chmod +x "$BIN_DIR/bragbook"

# Make sure ~/.local/bin is on PATH for future terminal windows (zsh is the macOS default).
for rc in "$HOME/.zshrc" "$HOME/.bashrc"; do
  if [ "$rc" = "$HOME/.zshrc" ] || [ -f "$rc" ]; then
    grep -q 'BRAGBOOK_PATH' "$rc" 2>/dev/null || \
      printf '\nexport PATH="$HOME/.local/bin:$PATH"  # BRAGBOOK_PATH\n' >> "$rc"
  fi
done

echo "✅ Brag Book installed."

# Restart the background tracker so it runs this version, then open the page.
if [ "$(uname)" = "Darwin" ]; then
  echo "Starting the tracker…"
  "$BIN_DIR/bragbook" autostart install
  for _ in $(seq 1 15); do
    if [ "$(curl -s --max-time 1 http://127.0.0.1:8642/health 2>/dev/null)" = "bragbook" ]; then
      echo
      echo "🎉 Your page is live: http://localhost:8642  (opening it now; bookmark it!)"
      open "http://localhost:8642"
      exit 0
    fi
    sleep 1
  done
  echo
  echo "⚠️  The tracker didn't start. Copy everything below and send it to Claude:"
  echo "----------------------------------------------------------------"
  sw_vers -productVersion 2>/dev/null || true
  python3 --version 2>&1 || true
  launchctl list 2>/dev/null | grep -i bragbook || echo "(not in launchctl list)"
  tail -n 25 "$HOME/.bragbook/tracker.log" 2>/dev/null || echo "(no tracker log)"
  echo "----------------------------------------------------------------"
  echo "Meanwhile, you can still open the page by running:  $BIN_DIR/bragbook dashboard"
  exit 1
fi

echo
echo "Next, open a NEW terminal window and run:  bragbook track"
echo "Then go to http://localhost:8642"
