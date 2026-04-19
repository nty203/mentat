#!/usr/bin/env bash
set -euo pipefail

REPO="nty203/mentat"
INSTALL_DIR="${HOME}/.local/share/mentat"
BIN_DIR="${HOME}/.local/bin"

echo "mentat installer"
echo ""

# Step 1: uv
if ! command -v uv >/dev/null 2>&1; then
  echo "Installing uv..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="${HOME}/.cargo/bin:${HOME}/.local/bin:${PATH}"
fi

# Step 2: Python 3.12
uv python install 3.12 2>/dev/null || true

# Step 3: clone or update (shallow)
if [ -d "${INSTALL_DIR}/.git" ]; then
  echo "Updating mentat..."
  git -C "${INSTALL_DIR}" fetch --depth 1
  git -C "${INSTALL_DIR}" reset --hard origin/main
else
  echo "Installing mentat to ${INSTALL_DIR}..."
  git clone --depth 1 "https://github.com/${REPO}.git" "${INSTALL_DIR}"
fi

# Step 4: uv sync
cd "${INSTALL_DIR}"
uv sync --python 3.12

# Step 5: mentat wrapper
mkdir -p "${BIN_DIR}"
cat > "${BIN_DIR}/mentat" << 'WRAPPER'
#!/usr/bin/env bash
INSTALL_DIR="${HOME}/.local/share/mentat"
exec "${INSTALL_DIR}/.venv/bin/python" -m mentat.cli.main "$@"
WRAPPER
chmod +x "${BIN_DIR}/mentat"

# Step 6: PATH auto-add
case ":${PATH}:" in
  *":${BIN_DIR}:"*) ;;
  *)
    EXPORT_LINE="export PATH=\"${BIN_DIR}:\${PATH}\""
    SHELL_NAME=$(basename "${SHELL:-/bin/bash}")
    case "$SHELL_NAME" in
      zsh)  RC_FILE="$HOME/.zshrc" ;;
      fish) RC_FILE="$HOME/.config/fish/config.fish"; EXPORT_LINE="set -x PATH \"${BIN_DIR}\" \$PATH" ;;
      *)    RC_FILE="$HOME/.bashrc" ;;
    esac
    if [ -f "$RC_FILE" ] && ! grep -qF "$BIN_DIR" "$RC_FILE" 2>/dev/null; then
      echo "$EXPORT_LINE" >> "$RC_FILE"
      echo "  PATH added to ${RC_FILE}. Run: source ${RC_FILE}"
    fi
    ;;
esac

echo ""
echo "mentat installed. Get started: mentat bootstrap"
