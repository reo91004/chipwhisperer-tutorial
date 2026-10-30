#!/usr/bin/env bash
set -euo pipefail

installer_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
official_root="${1:-${installer_root}/_workspace/official-chipwhisperer}"
cw_commit="c47aefe0d3083b5fc7392ab0698aa7446c633dd4"
jupyter_commit="dee4ddd71fa534457b97df6880ad4fecbc77bb94"
cw_url="https://github.com/newaetech/chipwhisperer.git"

if [[ "$(uname -s)" != "Darwin" ]]; then
    echo "This installer is for macOS." >&2
    exit 1
fi
if [[ "${EUID}" -eq 0 ]]; then
    echo "Run this script as your normal user, not with sudo." >&2
    exit 1
fi

if command -v brew >/dev/null 2>&1; then
    brew_bin="$(command -v brew)"
elif [[ -x /opt/homebrew/bin/brew ]]; then
    brew_bin=/opt/homebrew/bin/brew
elif [[ -x /usr/local/bin/brew ]]; then
    brew_bin=/usr/local/bin/brew
else
    echo "Homebrew is required. Install it from https://brew.sh and rerun this script." >&2
    exit 1
fi

for formula in libusb python@3.11 git; do
    "${brew_bin}" list --versions "${formula}" >/dev/null 2>&1 || "${brew_bin}" install "${formula}"
done
python_bin="$("${brew_bin}" --prefix python@3.11)/bin/python3.11"
toolchain_gcc="$(command -v arm-none-eabi-gcc || true)"
if [[ -z "${toolchain_gcc}" \
    || "$("${toolchain_gcc}" -print-file-name=nano.specs)" == "nano.specs" \
    || ! -f "$("${toolchain_gcc}" -print-file-name=nano.specs)" ]]; then
    "${brew_bin}" list --cask gcc-arm-embedded >/dev/null 2>&1 \
        || "${brew_bin}" install --cask gcc-arm-embedded
    toolchain_gcc="$(find /Applications/ArmGNUToolchain -type f -name arm-none-eabi-gcc -print 2>/dev/null | sort | tail -1)"
fi
if [[ -z "${toolchain_gcc}" || ! -x "${toolchain_gcc}" ]]; then
    echo "Full Arm GNU Toolchain was not found after installing gcc-arm-embedded." >&2
    exit 1
fi
toolchain_bin="$(dirname "${toolchain_gcc}")"
export PATH="$("${brew_bin}" --prefix git)/bin:${toolchain_bin}:${PATH}"
for command_name in "${python_bin}" git make arm-none-eabi-gcc; do
    if ! command -v "${command_name}" >/dev/null 2>&1; then
        echo "Required command not found: ${command_name}" >&2
        exit 1
    fi
done
if [[ ! -f "$(arm-none-eabi-gcc -print-file-name=nano.specs)" ]]; then
    echo "The selected Arm toolchain does not include newlib nano.specs." >&2
    exit 1
fi

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
echo "Setup complete. Start the official notebooks with:"
echo "  '${venv_dir}/bin/jupyter-lab' --ServerApp.root_dir='${official_root}/jupyter'"
