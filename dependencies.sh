#!/usr/bin/env bash
# Install OS-packaged dependencies for piwigo-batch-uploader.
# Prefers distribution packages (python3-pillow / python3-pil, python3-requests)
# over pip when available. Falls back to pip if no supported package manager
# is detected or the packages are missing.
#
# Supported ecosystems:
#   - Debian / Ubuntu / derivatives (apt): python3-pil, python3-requests
#   - Fedora / RHEL / CentOS Stream / AlmaLinux / Rocky / Oracle Linux (dnf/yum):
#       python3-pillow, python3-requests
#   - openSUSE / SUSE (zypper): python3-Pillow, python3-requests
#   - Arch / Manjaro (pacman): python-pillow, python-requests
#   - Alpine (apk): py3-pillow, py3-requests
#   - Gentoo (emerge): dev-python/pillow, dev-python/requests
#   - Fallback: pip install -r dependencies.txt

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPS_TXT="${SCRIPT_DIR}/dependencies.txt"

# Prefer sudo if not root
SUDO=""
if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
  if command -v sudo >/dev/null 2>&1; then
    SUDO="sudo"
  else
    echo "Warning: not root and sudo not found. Package installs may fail." >&2
  fi
fi

install_apt() {
  echo "Detected apt (Debian/Ubuntu family)."
  $SUDO apt-get update
  # python3-pil is the package that provides Pillow on Debian/Ubuntu
  $SUDO apt-get install -y python3-pil python3-requests
}

install_dnf() {
  local mgr="$1"
  echo "Detected ${mgr} (Fedora / RHEL / AlmaLinux / Rocky / CentOS Stream family)."
  # python3-pillow is available in AppStream (AlmaLinux 8+) and Fedora/EPEL.
  # On some older EL systems it may require EPEL; we try the standard name first.
  $SUDO "$mgr" install -y python3-pillow python3-requests
}

install_yum() {
  echo "Detected yum."
  # yum is typical on CentOS 7 / older RHEL. Package may be python3-pillow
  # or (on very old systems) python-pillow. Prefer python3-pillow.
  if $SUDO yum list available python3-pillow >/dev/null 2>&1; then
    $SUDO yum install -y python3-pillow python3-requests
  elif $SUDO yum list available python-pillow >/dev/null 2>&1; then
    echo "Note: installing python-pillow (older naming) instead of python3-pillow."
    $SUDO yum install -y python-pillow python3-requests || $SUDO yum install -y python-pillow python-requests
  else
    echo "python3-pillow not found in yum repos. You may need EPEL." >&2
    echo "Try: sudo yum install epel-release && sudo yum install python3-pillow python3-requests" >&2
    return 1
  fi
}

install_zypper() {
  echo "Detected zypper (openSUSE / SUSE)."
  # openSUSE uses python3-Pillow (capital P) in some releases; try both.
  if zypper search -x python3-Pillow >/dev/null 2>&1; then
    $SUDO zypper install -y python3-Pillow python3-requests
  else
    $SUDO zypper install -y python3-pillow python3-requests
  fi
}

install_pacman() {
  echo "Detected pacman (Arch / Manjaro)."
  $SUDO pacman -Sy --noconfirm python-pillow python-requests
}

install_apk() {
  echo "Detected apk (Alpine)."
  $SUDO apk add --no-cache py3-pillow py3-requests
}

install_emerge() {
  echo "Detected emerge (Gentoo)."
  $SUDO emerge --ask=n dev-python/pillow dev-python/requests
}

install_pip_fallback() {
  echo "Falling back to pip (see dependencies.txt)."
  if command -v pip3 >/dev/null 2>&1; then
    pip3 install --user -r "$DEPS_TXT" || pip3 install -r "$DEPS_TXT"
  elif command -v pip >/dev/null 2>&1; then
    pip install --user -r "$DEPS_TXT" || pip install -r "$DEPS_TXT"
  elif command -v python3 >/dev/null 2>&1; then
    python3 -m pip install --user -r "$DEPS_TXT" || python3 -m pip install -r "$DEPS_TXT"
  else
    echo "Error: no pip and no python3 found." >&2
    exit 1
  fi
}

main() {
  if command -v apt-get >/dev/null 2>&1; then
    install_apt
  elif command -v dnf >/dev/null 2>&1; then
    install_dnf dnf
  elif command -v yum >/dev/null 2>&1; then
    install_yum || install_pip_fallback
  elif command -v zypper >/dev/null 2>&1; then
    install_zypper
  elif command -v pacman >/dev/null 2>&1; then
    install_pacman
  elif command -v apk >/dev/null 2>&1; then
    install_apk
  elif command -v emerge >/dev/null 2>&1; then
    install_emerge
  else
    echo "No supported package manager detected."
    install_pip_fallback
    return
  fi

  echo "OS packages installed. You can also run: pip install -e ."
  echo "Or use the fallback: pip install -r dependencies.txt"
}

main "$@"
