#!/usr/bin/env bash
set -euo pipefail

installer_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
official_root="${1:-${installer_root}/_workspace/official-chipwhisperer}"
cw_commit="c47aefe0d3083b5fc7392ab0698aa7446c633dd4"
jupyter_commit="dee4ddd71fa534457b97df6880ad4fecbc77bb94"
cw_url="https://github.com/newaetech/chipwhisperer.git"

if [[ "$(uname -s)" != "Linux" ]]; then
    echo "This installer is for Linux." >&2
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
    sudo apt-get install -y python3 python3-venv python3-pip git make \
        gcc-arm-none-eabi libnewlib-arm-none-eabi libusb-1.0-0-dev usbutils udev
elif command -v dnf >/dev/null 2>&1; then
    sudo dnf install -y python3 python3-pip git make arm-none-eabi-gcc-cs \
        arm-none-eabi-newlib libusb1-devel usbutils systemd-udev
elif command -v pacman >/dev/null 2>&1; then
    sudo pacman -S --needed --noconfirm python python-pip git make \
        arm-none-eabi-gcc arm-none-eabi-newlib libusb usbutils systemd
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
    "${bootstrap_dir}/venv/bin/python" -m pip install --upgrade pip uv
    "${bootstrap_dir}/venv/bin/uv" python install 3.11
    python_bin="$("${bootstrap_dir}/venv/bin/uv" python find 3.11)"
    rm -rf "${bootstrap_dir}"
    trap - EXIT
fi

current_user="$(id -un)"
sudo groupadd --system --force chipwhisperer
sudo usermod --append --groups chipwhisperer "${current_user}"
sudo tee /etc/udev/rules.d/60-chipwhisperer-official.rules >/dev/null <<'RULES'
SUBSYSTEMS=="usb", ATTRS{idVendor}=="2b3e", ATTRS{idProduct}=="*", MODE="0664", GROUP="chipwhisperer", TAG+="uaccess"
SUBSYSTEM=="tty", ATTRS{idVendor}=="2b3e", ATTRS{idProduct}=="*", MODE="0664", GROUP="chipwhisperer", TAG+="uaccess", SYMLINK+="cw_serial%n"
SUBSYSTEM=="tty", ATTRS{idVendor}=="03eb", ATTRS{idProduct}=="6124", MODE="0664", GROUP="chipwhisperer", TAG+="uaccess", SYMLINK+="cw_bootloader%n"
RULES
sudo udevadm control --reload-rules
sudo udevadm trigger

new_clone=0
if [[ ! -e "${official_root}" ]]; then
    mkdir -p "$(dirname "${official_root}")"
    git clone --recursive "${cw_url}" "${official_root}"
    git -C "${official_root}" checkout --detach "${cw_commit}"
    new_clone=1
elif [[ ! -d "${official_root}/.git" ]]; then
    echo "Install path exists but is not a Git repository: ${official_root}" >&2
    exit 1
elif [[ "$(git -C "${official_root}" rev-parse HEAD)" != "${cw_commit}" ]]; then
    echo "Existing clone is not at the verified commit: ${official_root}" >&2
    exit 1
fi
if [[ "${new_clone}" -eq 0 \
    && -n "$(git -C "${official_root}" status --porcelain --ignore-submodules=none)" ]]; then
    echo "Official clone has local changes; refusing to modify it: ${official_root}" >&2
    exit 1
fi
git -C "${official_root}" submodule sync --recursive
git -C "${official_root}" submodule update --init --recursive
if [[ "$(git -C "${official_root}/jupyter" rev-parse HEAD)" != "${jupyter_commit}" ]]; then
    echo "Jupyter submodule is not at the verified commit." >&2
    exit 1
fi
generated_notebook="courses/sca101/SOLN_Lab 2_1B - Power Analysis for Password Bypass - CWLITEARM.ipynb"
jupyter_exclude="$(git -C "${official_root}/jupyter" rev-parse --git-path info/exclude)"
grep -Fxq "${generated_notebook}" "${jupyter_exclude}" \
    || printf '\n%s\n' "${generated_notebook}" >> "${jupyter_exclude}"
if [[ -n "$(git -C "${official_root}" status --porcelain --ignore-submodules=none)" ]]; then
    echo "Official clone is not clean after submodule setup: ${official_root}" >&2
    exit 1
fi

venv_dir="${official_root}/.venv"
if [[ ! -x "${venv_dir}/bin/python" ]]; then
    "${python_bin}" -m venv "${venv_dir}"
fi
venv_python="${venv_dir}/bin/python"
"${venv_python}" -c 'import sys; assert sys.version_info[:2] == (3, 11), "Remove .venv and rerun with Python 3.11"'
"${venv_python}" -m pip install --upgrade pip setuptools wheel
"${venv_python}" -m pip install --editable "${official_root}"
"${venv_python}" -m pip install --requirement "${official_root}/jupyter/requirements.txt" jupyterlab
"${venv_python}" "${installer_root}/scripts/prepare_official_f303.py" "${official_root}"

make -C "${official_root}/firmware/mcu/basic-passwdcheck" \
    PLATFORM=CWLITEARM CRYPTO_TARGET=NONE SS_VER=SS_VER_2_1 -j
make -C "${official_root}/firmware/mcu/simpleserial-aes" \
    PLATFORM=CWLITEARM CRYPTO_TARGET=TINYAES128C SS_VER=SS_VER_2_1 -j

"${venv_python}" -m ipykernel install --user \
    --name chipwhisperer-official-f303 \
    --display-name "Python (Official ChipWhisperer, F303)" \
    --env PATH "${PATH}"

echo
echo "Setup complete. Log out and back in once, then reconnect ChipWhisperer-Lite."
echo "Start the official notebooks with:"
echo "  '${venv_dir}/bin/jupyter-lab' --ServerApp.root_dir='${official_root}/jupyter'"
