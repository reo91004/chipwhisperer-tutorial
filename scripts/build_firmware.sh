#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/.." && pwd)"
if ! command -v arm-none-eabi-gcc >/dev/null 2>&1; then
  bundled_toolchain="${HOME}/.local/opt/arm-gnu-toolchain-14.3.rel1-darwin-arm64-arm-none-eabi/bin"
  if [[ -x "${bundled_toolchain}/arm-none-eabi-gcc" ]]; then
    export PATH="${bundled_toolchain}:${PATH}"
  else
    echo "arm-none-eabi-gcc를 찾을 수 없습니다. macOS에서는 'brew install arm-none-eabi-gcc' 후 다시 실행하세요." >&2
    exit 1
  fi
fi

for platform in CWLITEARM CW308_STM32F4; do
  make -C "${repo_root}/firmware/mcu/basic-passwdcheck" PLATFORM="${platform}" CRYPTO_TARGET=NONE SS_VER=SS_VER_1_0
  make -C "${repo_root}/firmware/mcu/simpleserial-aes" PLATFORM="${platform}" CRYPTO_TARGET=TINYAES128C SS_VER=SS_VER_1_1
  cp "${repo_root}/firmware/mcu/basic-passwdcheck/basic-passwdcheck-${platform}.hex" "${repo_root}/firmware/prebuilt/"
  cp "${repo_root}/firmware/mcu/simpleserial-aes/simpleserial-aes-${platform}.hex" "${repo_root}/firmware/prebuilt/"
done
(
  cd "${repo_root}/firmware/prebuilt"
  shasum -a 256 basic-passwdcheck-CWLITEARM.hex basic-passwdcheck-CW308_STM32F4.hex \
    simpleserial-aes-CWLITEARM.hex simpleserial-aes-CW308_STM32F4.hex > SHA256SUMS
)

arm-none-eabi-gcc --version | head -1
cat "${repo_root}/firmware/prebuilt/SHA256SUMS"
