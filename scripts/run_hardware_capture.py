#!/usr/bin/env python3
"""번들 펌웨어로 실제 비밀번호 SPA와 AES CPA 파형을 수집한다."""

from __future__ import annotations

import argparse
from pathlib import Path

from cw_sca_tutorial.hardware import capture_aes_run, capture_password_run, diagnose_password_signal


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("diagnostic", "password", "tvla", "aes", "all"))
    parser.add_argument("--runs-root", type=Path, default=Path("runs"))
    parser.add_argument("--serial-number")
    parser.add_argument("--platform", choices=("CWLITEARM", "CW308_STM32F4"), default="CWLITEARM")
    parser.add_argument("--target-identification", default="STM32F303")
    parser.add_argument("--password-repeats", type=int, default=1)
    parser.add_argument("--password-gain", type=float, default=25.0)
    parser.add_argument("--password-positions", type=int, choices=range(1, 6), default=5)
    parser.add_argument("--aes-traces", type=int, default=500)
    parser.add_argument("--tvla-traces", type=int, default=1000)
    parser.add_argument("--diagnostic-repeats", type=int, default=3)
    args = parser.parse_args()

    firmware = Path("firmware/prebuilt")
    if args.mode == "diagnostic":
        run = diagnose_password_signal(
            firmware / f"basic-passwdcheck-{args.platform}.hex",
            repeats=args.diagnostic_repeats,
            runs_root=args.runs_root,
            serial_number=args.serial_number,
            platform_name=args.platform,
            target_identification=args.target_identification,
        )
        print(f"diagnostic run: {run}")
    if args.mode in {"password", "all"}:
        run = capture_password_run(
            firmware / f"basic-passwdcheck-{args.platform}.hex",
            repeats=args.password_repeats,
            gain_db=args.password_gain,
            positions_to_recover=args.password_positions,
            runs_root=args.runs_root,
            serial_number=args.serial_number,
            platform_name=args.platform,
            target_identification=args.target_identification,
        )
        print(f"password run: {run}")
    if args.mode in {"aes", "all"}:
        run = capture_aes_run(
            firmware / f"simpleserial-aes-{args.platform}.hex",
            trace_count=args.aes_traces,
            runs_root=args.runs_root,
            serial_number=args.serial_number,
            platform_name=args.platform,
            target_identification=args.target_identification,
        )
        print(f"AES run: {run}")
    if args.mode == "tvla":
        run = capture_aes_run(
            firmware / f"simpleserial-aes-{args.platform}.hex",
            trace_count=args.tvla_traces,
            runs_root=args.runs_root,
            serial_number=args.serial_number,
            platform_name=args.platform,
            target_identification=args.target_identification,
            capture_mode="fixed_vs_random",
        )
        print(f"TVLA run: {run}")


if __name__ == "__main__":
    main()
