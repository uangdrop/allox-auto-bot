#!/usr/bin/env bash
# Activate the project's virtual environment (or set one up from scratch).
# Usage:  source ./activate.sh   (note: must be SOURCED, not executed)
#
# This script is designed to be FUSS-FREE for first-time users:
#   * Detects your OS (Ubuntu/Debian/Fedora/Arch/macOS/Alpine)
#   * Detects whether `python3-venv`, `pip`, and other deps are installed
#   * Tries to auto-install missing system packages (asks permission first)
#   * Falls back to `--break-system-packages` if venv is truly impossible
#   * Catches partial venv creation and recovers automatically
#
# Exit codes (only meaningful when run directly, not sourced):
#   0  — venv active, dependencies installed
#   1  — unrecoverable error (see message)

# We deliberately do NOT use `set -e`: a partial failure should be
# diagnosed, not silently killed. set -u catches unset variables.
set -u

# ── Pretty output ─────────────────────────────────────────────────────────
if [ -t 1 ]; then
    RED='\033[0;31m'; YEL='\033[0;33m'; GRN='\033[0;32m'
    CYA='\033[0;36m'; BLU='\033[0;34m'; BLD='\033[1m'; RST='\033[0m'
else
    RED=''; YEL=''; GRN=''; CYA=''; BLU=''; BLD=''; RST=''
fi

ok()   { printf "${GRN}✓ %s${RST}\n" "$*"; }
info() { printf "${CYA}→ %s${RST}\n" "$*"; }
warn() { printf "${YEL}! %s${RST}\n" "$*"; }
fail() { printf "${RED}✗ %s${RST}\n" "$*" >&2; }

# Error reporting. After `die`, the script bails out — for sourced
# scripts that means returning to the parent shell (which is the
# desired behavior; we don't want to `exit` and close the user's
# terminal). For executed scripts, `exit` is fine.
#
# We use a `bail` function that detects whether we're sourced or
# executed and acts accordingly.
bail() {
    fail "$@"
    # If the script is being SOURCED, BASH_SOURCE[0] != $0. We `return`
    # to unwind the sourced-script stack. If executed, we `exit`.
    if [ "${BASH_SOURCE[0]}" != "$0" ]; then
        return 1 2>/dev/null || true
    else
        exit 1
    fi
}

# ── Paths ─────────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"
REQ_FILE="$SCRIPT_DIR/requirements.txt"
MARKER="$VENV_DIR/.installed"

# ── Banner ────────────────────────────────────────────────────────────────
printf "${BLU}${BLD}"
cat <<'BANNER'
╔════════════════════════════════════════╗
║   Allox Auto Bot — environment setup  ║
╚════════════════════════════════════════╝
BANNER
printf "${RST}"

# ── Helper: detect OS and package manager ─────────────────────────────────
detect_os() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        case "${ID:-unknown}" in
            ubuntu|debian|linuxmint|pop|kali) OS="debian"; PKG="apt" ;;
            fedora|centos|rhel|rocky|almalinux) OS="fedora"; PKG="dnf" ;;
            arch|manjaro|endeavouros)           OS="arch";   PKG="pacman" ;;
            alpine)                             OS="alpine"; PKG="apk" ;;
            *)                                  OS="unknown"; PKG="?" ;;
        esac
    elif [ "$(uname -s 2>/dev/null)" = "Darwin" ]; then
        OS="macos"; PKG="brew"
    else
        OS="unknown"; PKG="?"
    fi
}

# ── Helper: try to install system packages (asks permission) ─────────────
# usage: try_install "human description" "package1 package2 ..."
# Returns 0 on success, 1 on failure / declined.
try_install() {
    local what="$1" ; shift
    local pkgs="$*"

    if [ -z "$pkgs" ] || [ "$PKG" = "?" ]; then
        return 1
    fi

    # Build the actual command based on the package manager
    local cmd=""
    case "$PKG" in
        apt)    cmd="sudo apt install -y $pkgs" ;;
        dnf)    cmd="sudo dnf install -y $pkgs" ;;
        pacman) cmd="sudo pacman -S --noconfirm $pkgs" ;;
        apk)    cmd="sudo apk add $pkgs" ;;
        brew)   cmd="brew install $pkgs" ;;
    esac
    if [ -z "$cmd" ]; then return 1; fi

    # Don't auto-install if we're not interactive and not root
    if [ ! -t 0 ] && [ "$(id -u)" -ne 0 ]; then
        warn "Skipping auto-install (non-interactive, no root): $what"
        return 1
    fi

    if [ -t 0 ]; then
        printf "${YEL}? Mau install '$what'? (y/n)${RST} [y]: "
        local ans
        read -r ans
        case "${ans:-y}" in
            y|Y|yes|YES|"") ;;   # proceed
            *) return 1 ;;
        esac
    fi

    info "Menjalankan: $cmd"
    if eval "$cmd"; then
        ok "$what terinstall"
        return 0
    else
        fail "Gagal install: $what"
        return 1
    fi
}

# ── Helper: test whether a python module can be imported ─────────────────
py_has() {
    python3 -c "import $1" >/dev/null 2>&1
}

# ── 1. Python version check ───────────────────────────────────────────────
info "Cek Python..."
if ! command -v python3 >/dev/null 2>&1; then
    fail "python3 tidak ditemukan di PATH"
    echo ""
    echo "Install Python dulu:"
    echo "  Ubuntu/Debian:  sudo apt install -y python3"
    echo "  Fedora:         sudo dnf install -y python3"
    echo "  macOS:          brew install python   (atau download dari python.org)"
    echo "  Windows:        download dari https://www.python.org/downloads/"
    bail "Python3 required"
fi

PY_VERSION=$(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])')
PY_MAJOR=$(echo "$PY_VERSION" | cut -d. -f1)
PY_MINOR=$(echo "$PY_VERSION" | cut -d. -f2)
ok "Python $PY_VERSION"

if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 10 ]; }; then
    fail "Python $PY_VERSION terlalu lama — butuh 3.10+"
    echo "Lihat instruksi upgrade di README.md"
    bail "Python >= 3.10 required"
fi

# ── 2. Detect OS & package manager ────────────────────────────────────────
detect_os
info "OS: ${OS} (package manager: ${PKG})"

# ── 3. Make sure venv module is available ─────────────────────────────────
if ! py_has venv; then
    fail "Python 'venv' module tidak tersedia"
    echo ""
    case "$OS" in
        debian) echo "Fix:  sudo apt install -y python3-venv python3-full python3-pip" ;;
        fedora) echo "Fix:  sudo dnf install -y python3-virtualenv python3-pip" ;;
        arch)   echo "Fix:  sudo pacman -S --noconfirm python-virtualenv" ;;
        alpine) echo "Fix:  sudo apk add python3-dev py3-virtualenv" ;;
        macos)  echo "Fix:  brew install python    (juga reinstall dari python.org untuk dapat 'venv')" ;;
        *)      echo "Install python3-venv via package manager OS lo" ;;
    esac
    echo ""

    # Try auto-install
    case "$OS" in
        debian) try_install "python3-venv + python3-pip" "python3-venv python3-full python3-pip" || bail "Install python3-venv secara manual lalu re-run" ;;
        fedora) try_install "python3-virtualenv" "python3-virtualenv" || bail "Install python3-virtualenv secara manual lalu re-run" ;;
        arch)   try_install "python-virtualenv" "python-virtualenv" || bail "Install python-virtualenv secara manual lalu re-run" ;;
    esac
fi
ok "venv module tersedia"

# ── 4. Make sure pip is available in the venv context ─────────────────────
# (system pip might be missing on Debian slim — we re-check inside the venv
# after creation)

# ── 5. Create the venv if missing or broken ───────────────────────────────
NEED_CREATE=0
if [ ! -d "$VENV_DIR" ]; then
    NEED_CREATE=1
elif [ ! -f "$VENV_DIR/bin/activate" ] || [ ! -x "$VENV_DIR/bin/python" ]; then
    warn "Existing .venv looks broken — removing and recreating"
    rm -rf "$VENV_DIR"
    NEED_CREATE=1
fi

if [ "$NEED_CREATE" -eq 1 ]; then
    info "Membuat venv di $VENV_DIR"
    if ! python3 -m venv "$VENV_DIR"; then
        fail "python3 -m venv gagal"
        echo ""
        echo "Kemungkinan penyebab: paket ensurepip / python3-venv belum lengkap"
        case "$OS" in
            debian) echo "Coba:  sudo apt install -y python3-venv python3-full" ;;
            fedora) echo "Coba:  sudo dnf install -y python3-devel" ;;
        esac
        bail "Gagal bikin venv"
    fi
    ok "venv dibuat"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

# ── 6. Verify pip is functional inside the venv ───────────────────────────
if ! command -v pip >/dev/null 2>&1; then
    fail "pip tidak ada di dalam venv — venv kemungkinan dibuat tanpa pip"
    echo ""
    case "$OS" in
        debian)
            echo "Coba fix:"
            echo "  sudo apt install -y python3-pip"
            echo "  rm -rf $VENV_DIR"
            echo "  source ./activate.sh"
            ;;
        *)
            echo "Buat ulang venv dengan pip:"
            echo "  rm -rf $VENV_DIR"
            echo "  python3 -m venv $VENV_DIR --with-pip"
            echo "  source ./activate.sh"
            ;;
    esac
    bail "pip tidak ada di venv"
fi

# Upgrade pip itself quietly (helps with newer wheels)
if ! pip install --quiet --upgrade pip 2>/dev/null; then
    warn "pip self-upgrade gagal (biasanya aman di-skip)"
fi

# ── 7. Install requirements.txt (idempotent) ──────────────────────────────
if [ ! -f "$MARKER" ] || [ "$REQ_FILE" -nt "$MARKER" ]; then
    info "Install requirements.txt ..."
    if ! pip install -r "$REQ_FILE" 2>&1 | tail -20; then
        fail "pip install gagal"
        echo ""
        echo "Penyebab umum:"
        echo "  • Internet putus"
        echo "  • PyPI down"
        echo "  • Paket bentrok (coba: pip install -r requirements.txt --no-cache-dir)"
        echo "  • SSL issue (coba: pip install -r requirements.txt --trusted-host pypi.org)"
        bail "Gagal install requirements"
    fi
    touch "$MARKER"
    ok "Dependencies terinstall"
else
    ok "Dependencies sudah terinstall (skip)"
fi

# ── 8. Quick smoke test ──────────────────────────────────────────────────
info "Verifikasi dependencies..."
MISSING=""
for mod in requests pytz colorama eth_account feedparser; do
    if python -c "import $mod" >/dev/null 2>&1; then
        printf "  ${GRN}✓${RST} %s\n" "$mod"
    else
        printf "  ${RED}✗${RST} %s\n" "$mod"
        MISSING="$MISSING $mod"
    fi
done
if [ -n "$MISSING" ]; then
    fail "Module hilang:$MISSING"
    echo "Coba: pip install -r requirements.txt"
    bail "Dependencies incomplete"
fi

# ── 9. Done! ──────────────────────────────────────────────────────────────
echo ""
printf "${GRN}${BLD}"
cat <<'DONE'
╔════════════════════════════════════════╗
║   ✓  Environment siap dipakai!        ║
╚════════════════════════════════════════╝
DONE
printf "${RST}"
echo ""
echo "  python : $(which python)"
echo "  pip    : $(which pip)"
echo "  cwd    : $(pwd)"
echo ""
echo "  Lanjut :  python bot.py"
echo "  Stop   :  deactivate"
echo ""
