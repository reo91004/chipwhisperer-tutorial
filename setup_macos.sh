#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
venv_dir="${repo_root}/.venv"
cw_commit="c47aefe0d3083b5fc7392ab0698aa7446c633dd4"
cw_source_dir="${venv_dir}/src/chipwhisperer-${cw_commit}"

if [[ "$(uname -s)" != "Darwin" ]]; then
    echo "This installer is for macOS. Use setup_linux.sh or setup_windows.ps1 instead." >&2
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

"${brew_bin}" list --versions libusb >/dev/null 2>&1 || "${brew_bin}" install libusb
"${brew_bin}" list --versions python@3.11 >/dev/null 2>&1 || "${brew_bin}" install python@3.11

python_bin="$("${brew_bin}" --prefix python@3.11)/bin/python3.11"
if [[ ! -x "${python_bin}" ]]; then
    echo "Homebrew Python 3.11 was not found at ${python_bin}." >&2
    exit 1
fi

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
echo "Setup complete. Start Jupyter with:"
echo "  source '${venv_dir}/bin/activate'"
echo "  jupyter lab"
