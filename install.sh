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

echo
echo "✅ Brag Book installed."
echo
echo "Next, open a NEW Terminal window (so it picks up the new command) and run:"
echo "    bragbook check"
echo "    bragbook autostart install"
echo
echo "Or use it right now in this window with the full path:"
echo "    $BIN_DIR/bragbook check"
