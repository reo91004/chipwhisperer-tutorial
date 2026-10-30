#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
venv_dir="${repo_root}/.venv"
cw_commit="c47aefe0d3083b5fc7392ab0698aa7446c633dd4"
cw_source_dir="${venv_dir}/src/chipwhisperer-${cw_commit}"

if [[ "$(uname -s)" != "Linux" ]]; then
    echo "This installer is for Linux. Use setup_macos.sh or setup_windows.ps1 instead." >&2
    exit 1
fi
if [[ "${EUID}" -eq 0 ]]; then
    echo "Run this script as your normal user, not with sudo." >&2
    exit 1
fi
if ! command -v sudo >/dev/null 2>&1; then
    echo "sudo is required to install Linux packages and USB permissions." >&2
    exit 1
fi

if command -v apt-get >/dev/null 2>&1; then
    sudo apt-get update
    sudo apt-get install -y python3 python3-venv python3-dev python3-pip \
        libusb-1.0-0-dev libusb-dev usbutils udev curl unzip
elif command -v dnf >/dev/null 2>&1; then
    sudo dnf install -y python3 python3-devel python3-pip libusb1-devel \
        usbutils systemd-udev curl unzip
elif command -v pacman >/dev/null 2>&1; then
    sudo pacman -S --needed --noconfirm python python-pip libusb usbutils \
        systemd curl unzip
else
    echo "Supported package managers: apt-get, dnf, pacman." >&2
    exit 1
fi

python_bin=""
for candidate in "${PYTHON:-}" python3.11; do
    if [[ -n "${candidate}" ]] && command -v "${candidate}" >/dev/null 2>&1 \
        && "${candidate}" -c 'import sys; raise SystemExit(sys.version_info[:2] != (3, 11))'; then
        python_bin="$(command -v "${candidate}")"
        break
    fi
done
if [[ -z "${python_bin}" ]]; then
    bootstrap_dir="$(mktemp -d)"
    trap 'rm -rf "${bootstrap_dir}"' EXIT
    python3 -m venv "${bootstrap_dir}/venv"
    "${bootstrap_dir}/venv/bin/python" -m pip install --upgrade pip
    "${bootstrap_dir}/venv/bin/python" -m pip install uv
    "${bootstrap_dir}/venv/bin/uv" python install 3.11
    python_bin="$("${bootstrap_dir}/venv/bin/uv" python find 3.11)"
    rm -rf "${bootstrap_dir}"
    trap - EXIT
fi

current_user="$(id -un)"
sudo groupadd --system --force chipwhisperer
sudo usermod --append --groups chipwhisperer "${current_user}"
sudo tee /etc/udev/rules.d/60-chipwhisperer-tutorial.rules >/dev/null <<'RULES'
SUBSYSTEMS=="usb", ATTRS{idVendor}=="2b3e", ATTRS{idProduct}=="*", MODE="0664", GROUP="chipwhisperer", TAG+="uaccess"
SUBSYSTEM=="tty", ATTRS{idVendor}=="2b3e", ATTRS{idProduct}=="*", MODE="0664", GROUP="chipwhisperer", TAG+="uaccess", SYMLINK+="cw_serial%n"
SUBSYSTEM=="tty", ATTRS{idVendor}=="03eb", ATTRS{idProduct}=="6124", MODE="0664", GROUP="chipwhisperer", TAG+="uaccess", SYMLINK+="cw_bootloader%n"
RULES
sudo udevadm control --reload-rules
sudo udevadm trigger

if [[ ! -x "${venv_dir}/bin/python" ]]; then
    "${python_bin}" -m venv "${venv_dir}"
fi
venv_python="${venv_dir}/bin/python"
"${venv_python}" -c 'import sys; assert sys.version_info[:2] == (3, 11), "Remove .venv and rerun with Python 3.11"'
"${venv_python}" -m pip install --upgrade pip setuptools wheel

if [[ ! -d "${cw_source_dir}" ]]; then
    download_dir="$(mktemp -d)"
    trap 'rm -rf "${download_dir}"' EXIT
    curl --fail --location --retry 3 \
        "https://github.com/newaetech/chipwhisperer/archive/${cw_commit}.zip" \
        --output "${download_dir}/chipwhisperer.zip"
    unzip -q "${download_dir}/chipwhisperer.zip" -d "${download_dir}"
    mkdir -p "${venv_dir}/src"
    mv "${download_dir}/chipwhisperer-${cw_commit}" "${cw_source_dir}"
    rm -rf "${download_dir}"
    trap - EXIT
fi
if [[ ! -f "${cw_source_dir}/pyproject.toml" \
    || ! -f "${cw_source_dir}/software/chipwhisperer/hardware/firmware/cwlite/version.txt" ]]; then
    echo "Pinned ChipWhisperer source is incomplete. Remove .venv and rerun this script." >&2
    exit 1
fi
"${venv_python}" -m pip install --editable "${cw_source_dir}"
"${venv_python}" -m pip install --editable "${repo_root}"
"${venv_python}" -m ipykernel install --user \
    --name chipwhisperer-tutorial \
    --display-name "Python (ChipWhisperer Tutorial)"

if [[ ! -f "${repo_root}/firmware/prebuilt/basic-passwdcheck-CWLITEARM.hex" \
    || ! -f "${repo_root}/firmware/prebuilt/simpleserial-aes-CWLITEARM.hex" ]]; then
    echo "Bundled CWLITEARM firmware is missing." >&2
    exit 1
fi
"${venv_python}" -m unittest discover -s "${repo_root}/tests" -v

echo
echo "Setup complete. Log out and back in once, then unplug and reconnect ChipWhisperer."
echo "Start Jupyter with:"
echo "  source '${venv_dir}/bin/activate'"
echo "  jupyter lab"
