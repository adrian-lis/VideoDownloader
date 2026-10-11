#!/usr/bin/env bash

set -Ee
cd -- "$(dirname -- "$(readlink -f -- "${BASH_SOURCE[0]}")")"

trap 'echo; echo "ERROR: Installation failed. Check the message above."; exit 1' ERR

echo
echo "Video Downloader - Installer"
echo "===================================="
echo

# Detect Linux distribution and package manager
detect_package_manager() {
    local distro=""
    local distro_like=""

    if [ -r /etc/os-release ]; then
        . /etc/os-release
        distro="${ID:-}"
        distro_like="${ID_LIKE:-}"
    fi

    if command -v apt-get >/dev/null 2>&1 &&
       [[ " $distro $distro_like " =~ (debian|ubuntu) ]]; then
        PACKAGE_MANAGER="apt"
    elif command -v dnf >/dev/null 2>&1; then
        PACKAGE_MANAGER="dnf"
    elif command -v yum >/dev/null 2>&1; then
        PACKAGE_MANAGER="yum"
    elif command -v pacman >/dev/null 2>&1; then
        PACKAGE_MANAGER="pacman"
    elif command -v zypper >/dev/null 2>&1; then
        PACKAGE_MANAGER="zypper"
    elif command -v apk >/dev/null 2>&1; then
        PACKAGE_MANAGER="apk"
    else
        PACKAGE_MANAGER=""
    fi

    # Run package-manager commands as root or through sudo.
    if [ "$EUID" -eq 0 ]; then
        PRIVILEGE_CMD=()
    elif command -v sudo >/dev/null 2>&1; then
        PRIVILEGE_CMD=(sudo)
    else
        PRIVILEGE_CMD=()
    fi
}

# Install requested packages only after explicit user consent.
install_packages() {
    local purpose="$1"
    shift

    local packages=("$@")
    local answer

    if [ -z "$PACKAGE_MANAGER" ]; then
        echo "ERROR: Could not detect a supported package manager."
        echo "Install $purpose manually using your distribution's package manager."
        return 1
    fi

    if [ "$EUID" -ne 0 ] && ! command -v sudo >/dev/null 2>&1; then
        echo "ERROR: sudo is not available."
        echo "Run the installer as root or install $purpose manually."
        return 1
    fi

    echo
    echo "The following packages are required for $purpose:"
    printf '  - %s\n' "${packages[@]}"
    echo
    printf 'Install these packages using %s? [y/N]: ' "$PACKAGE_MANAGER"
    read -r answer

    case "$answer" in
        y|Y|yes|YES|Yes)
            ;;
        *)
            echo "Package installation declined."
            return 1
            ;;
    esac

    echo
    echo "Installing packages..."

    case "$PACKAGE_MANAGER" in
        apt)
            "${PRIVILEGE_CMD[@]}" apt-get update
            "${PRIVILEGE_CMD[@]}" apt-get install -y "${packages[@]}"
            ;;
        dnf)
            "${PRIVILEGE_CMD[@]}" dnf install -y "${packages[@]}"
            ;;
        yum)
            "${PRIVILEGE_CMD[@]}" yum install -y "${packages[@]}"
            ;;
        pacman)
            "${PRIVILEGE_CMD[@]}" pacman -S --needed --noconfirm "${packages[@]}"
            ;;
        zypper)
            "${PRIVILEGE_CMD[@]}" zypper --non-interactive install "${packages[@]}"
            ;;
        apk)
            "${PRIVILEGE_CMD[@]}" apk add "${packages[@]}"
            ;;
        *)
            echo "ERROR: Unsupported package manager."
            return 1
            ;;
    esac

    echo "OK: Packages installed."
}

# Detect Python
find_python() {
    local candidate

    PYTHON=""

    for candidate in python3 python; do
        if command -v "$candidate" >/dev/null 2>&1 &&
           "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)' 2>/dev/null; then
            PYTHON="$candidate"
            return 0
        fi
    done

    return 1
}

# Detect virtual environment support
check_venv() {
    "$PYTHON" -c 'import venv' >/dev/null 2>&1
}

detect_package_manager

# 1. Check Python
echo "[1/4] Checking Python..."

if ! find_python; then
    echo "Python 3.10 or newer was not found."

    case "$PACKAGE_MANAGER" in
        apt)
            PYTHON_PACKAGES=(python3 python3-venv)
            ;;
        dnf|yum)
            PYTHON_PACKAGES=(python3)
            ;;
        pacman)
            PYTHON_PACKAGES=(python)
            ;;
        zypper)
            PYTHON_PACKAGES=(python3)
            ;;
        apk)
            PYTHON_PACKAGES=(python3)
            ;;
        *)
            PYTHON_PACKAGES=()
            ;;
    esac

    if [ "${#PYTHON_PACKAGES[@]}" -eq 0 ] ||
       ! install_packages "Python 3.10+" "${PYTHON_PACKAGES[@]}"; then
        echo "ERROR: Python 3.10 or newer is required."
        echo "Install it manually and run this installer again."
        exit 1
    fi

    if ! find_python; then
        echo "ERROR: Python 3.10 or newer is still unavailable."
        exit 1
    fi
fi

"$PYTHON" --version
echo "OK: Python is ready."

# 2. Prepare virtual environment
echo
echo "[2/4] Preparing virtual environment..."

if [ ! -x ".venv/bin/python" ]; then
    if [ -e ".venv" ]; then
        echo "ERROR: .venv exists but is not a valid virtual environment."
        echo "Remove or rename .venv and run the installer again."
        exit 1
    fi

    if ! check_venv; then
        echo "Python virtual environment support is unavailable."

        if [ "$PACKAGE_MANAGER" = "apt" ]; then
            if ! install_packages "Python virtual environment support" python3-venv; then
                echo "ERROR: Python venv support is required."
                exit 1
            fi
        else
            echo "Install your distribution's Python venv package manually."
            exit 1
        fi
    fi

    "$PYTHON" -m venv .venv
fi

VENV_PYTHON=".venv/bin/python"

if [ ! -x "$VENV_PYTHON" ]; then
    echo "ERROR: Could not create the virtual environment."
    exit 1
fi

echo "OK: Virtual environment is ready."

# 3. Install application dependencies
echo
echo "[3/4] Installing dependencies..."

"$VENV_PYTHON" -m pip install --upgrade pip
"$VENV_PYTHON" -m pip install -r requirements.txt

echo "OK: Dependencies installed."

# 4. Check FFmpeg
echo
echo "[4/4] Checking FFmpeg..."

if [ -x "ffmpeg/ffmpeg" ]; then
    echo "OK: Local Linux FFmpeg found."
elif command -v ffmpeg >/dev/null 2>&1; then
    echo "OK: System FFmpeg found."
else
    echo "FFmpeg was not found."
    echo "It may be required to merge video and audio."

    if install_packages "FFmpeg" ffmpeg; then
        if command -v ffmpeg >/dev/null 2>&1; then
            echo "OK: FFmpeg is ready."
        else
            echo "WARNING: FFmpeg was installed but could not be detected."
        fi
    else
        echo "WARNING: FFmpeg was not installed."
        echo "You can install it later using your distribution's package manager."
    fi
fi

# Finish
echo
echo "Installation completed."
echo "Start the application using: ./run.sh"
echo
