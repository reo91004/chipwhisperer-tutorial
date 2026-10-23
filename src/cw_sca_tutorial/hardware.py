"""CW-Lite와 STM32F303/F415의 실측 캡처 및 증거 기록."""

from __future__ import annotations

import hashlib
import json
import platform
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from .synthetic import AES_KEY, PASSWORD_ALPHABET


NIST_PLAINTEXT = bytes.fromhex("3243f6a8885a308d313198a2e0370734")
NIST_CIPHERTEXT = bytes.fromhex("3925841d02dc09fbdc118597196a0b32")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _jsonable(value: Any) -> Any:
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, bytes):
        return value.hex()
    return str(value)


def _write_json(path: Path, data: dict[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=_jsonable) + "\n", encoding="utf-8")
    temporary.replace(path)


def _append_attempt(path: Path, record: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, ensure_ascii=False, default=_jsonable) + "\n")


def _new_run(root: Path, kind: str) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    candidate = root / f"{timestamp}-{kind}"
    suffix = 1
    while candidate.exists():
        candidate = root / f"{timestamp}-{kind}-{suffix}"
        suffix += 1
    candidate.mkdir(parents=True)
    return candidate


def validate_waveform(
    wave: np.ndarray,
    expected_samples: int,
    *,
    minimum_peak_to_peak: float = 1e-6,
) -> tuple[bool, str]:
    """잘린 파형, 비유한 값, 상수 파형을 claim 데이터에서 제외한다."""

    wave = np.asarray(wave)
    if wave.shape != (expected_samples,):
        return False, f"sample_count={wave.size}, expected={expected_samples}"
    if not np.isfinite(wave).all():
        return False, "non-finite sample"
    peak_to_peak = float(np.ptp(wave))
    if peak_to_peak < minimum_peak_to_peak:
        return False, f"peak_to_peak={peak_to_peak:.6g}, required>={minimum_peak_to_peak:.6g}"
    return True, "accepted"


def _scope_snapshot(scope: Any, device: dict[str, Any], *, samples: int) -> dict[str, Any]:
    return {
        "device": device,
        "scope_type": type(scope).__name__,
        "gain_db": float(scope.gain.db),
        "samples": int(scope.adc.samples),
        "offset": int(scope.adc.offset),
        "adc_source": str(scope.clock.adc_src),
        "adc_frequency_hz": float(scope.clock.adc_freq),
        "clock_generator_hz": float(scope.clock.clkgen_freq),
        "clock_generator_locked": bool(scope.clock.clkgen_locked),
        "trigger": str(scope.trigger.triggers),
        "tio1": str(scope.io.tio1),
        "tio2": str(scope.io.tio2),
        "tio4": str(scope.io.tio4),
        "hs2": str(scope.io.hs2),
        "expected_samples": samples,
    }


def _select_device(cw: Any, serial_number: str | None) -> dict[str, Any]:
    devices = cw.list_devices()
    if serial_number is not None:
        devices = [device for device in devices if device.get("sn") == serial_number]
    if len(devices) != 1:
        raise RuntimeError(f"정확히 한 대의 선택된 ChipWhisperer가 필요합니다. 발견: {devices}")
    return devices[0]


def _program(scope: Any, cw: Any, firmware: Path, attempts_path: Path, platform_name: str) -> None:
    record = {
        "kind": "programming",
        "started_at": _now(),
        "firmware": str(firmware),
        "firmware_sha256": _sha256(firmware),
        "platform": platform_name,
        "programmer": "STM32FProgrammer",
        "status": "running",
    }
    _append_attempt(attempts_path, record)
    try:
        cw.program_target(scope, cw.programmers.STM32FProgrammer, str(firmware))
    except Exception as error:
        _append_attempt(attempts_path, {**record, "finished_at": _now(), "status": "failed", "error": repr(error)})
        raise
    _append_attempt(attempts_path, {**record, "finished_at": _now(), "status": "complete"})


def _reset_target(scope: Any) -> None:
    import time

    scope.io.nrst = "low"
    time.sleep(0.05)
    scope.io.nrst = "high_z"
    time.sleep(0.05)


def _trace_output(trace: Any) -> bytes:
    if not hasattr(trace, "ciphertext"):
        raise TypeError(f"unsupported ChipWhisperer trace container: {type(trace).__name__}")
    output = trace.ciphertext
    return bytes(output) if output is not None else b""


def _trace_wave(trace: Any) -> np.ndarray:
    if not hasattr(trace, "trace"):
        raise TypeError(f"unsupported ChipWhisperer trace container: {type(trace).__name__}")
    return np.asarray(trace.trace, dtype=np.float32)


def _capture_aes_preflight(cw: Any, scope: Any, target: Any, samples: int) -> tuple[np.ndarray | None, bytes, bool, str]:
    _reset_target(scope)
    try:
        trace = cw.capture_trace(
            scope,
            target,
            bytearray(NIST_PLAINTEXT),
            bytearray(AES_KEY),
            as_int=False,
            always_send_key=True,
        )
    except Warning as error:
        return None, b"", False, f"target command rejected: {error}"
    if trace is None:
        return None, b"", False, "capture timeout"
    wave = _trace_wave(trace)
    valid, reason = validate_waveform(wave, samples, minimum_peak_to_peak=0.05)
    output = _trace_output(trace)
    if output != NIST_CIPHERTEXT:
        valid, reason = False, f"NIST ciphertext mismatch: {output.hex()}"
    return wave, output, valid, reason


def capture_aes_run(
    firmware_hex: str | Path,
    *,
    trace_count: int = 500,
    samples: int = 5000,
    gain_db: float = 25.0,
    seed: int = 20261022,
    runs_root: str | Path = "runs",
    serial_number: str | None = None,
    platform_name: str = "CWLITEARM",
    target_identification: str = "STM32F303",
    capture_mode: str = "random",
    program_firmware: bool = True,
) -> Path:
    """STM32 대상의 소프트웨어 AES 파형을 캡처한다. 자동 재시도는 하지 않는다."""

    import chipwhisperer as cw

    if capture_mode not in {"random", "fixed_vs_random"}:
        raise ValueError("capture_mode은 'random' 또는 'fixed_vs_random'이어야 합니다")
    if capture_mode == "fixed_vs_random" and trace_count % 2:
        raise ValueError("fixed-vs-random TVLA의 trace_count는 짝수여야 합니다")
    is_tvla = capture_mode == "fixed_vs_random"
    firmware = Path(firmware_hex).resolve()
    if not firmware.is_file():
        raise FileNotFoundError(firmware)
    run = _new_run(Path(runs_root), "aes-tvla" if is_tvla else "aes-cpa")
    attempts_path = run / "attempts.jsonl"
    metadata_path = run / "metadata.json"
    metadata: dict[str, Any] = {
        "schema_version": 1,
        "run_id": run.name,
        "kind": "measured_aes_tvla" if is_tvla else "measured_aes_cpa",
        "state": "running",
        "started_at": _now(),
        "evidence_origin": "measured",
        "evidence_purpose": "claim_bearing",
        "measurement_scope": f"CW-Lite power capture of bundled TinyAES on {target_identification}",
        "claim_scope": (
            f"fixed-vs-random Welch t-test leakage detection for bundled TinyAES on {target_identification}"
            if is_tvla else
            f"isolated software AES-128 first-round leakage and key recovery on {target_identification}"
        ),
        "target_identity": {
            "platform": platform_name,
            "user_identification": target_identification,
            "software_verified_exact_board_variant": False,
        },
        "firmware": {"path": str(firmware), "sha256": _sha256(firmware), "crypto_target": "TINYAES128C", "ss_ver": "SS_VER_1_1"},
        "requested_trace_count": trace_count,
        "capture_mode": capture_mode,
        "program_firmware": program_firmware,
        "seed": seed,
        "host": {"python": platform.python_version(), "platform": platform.platform(), "chipwhisperer": cw.__version__},
        "negative_control": "samples 0:50 precede the synthetic lesson POIs; measured run evaluates an explicit wrong window after capture",
    }
    _write_json(metadata_path, metadata)
    scope = None
    target = None
    traces: list[np.ndarray] = []
    plaintexts: list[np.ndarray] = []
    responses: list[np.ndarray] = []
    groups: list[int] = []
    try:
        device = _select_device(cw, serial_number)
        scope = cw.scope(sn=device["sn"])
        scope.default_setup()
        scope.adc.samples = samples
        scope.gain.db = gain_db
        metadata["measurement_setup"] = _scope_snapshot(scope, device, samples=samples)
        if not scope.clock.clkgen_locked:
            raise RuntimeError("CW-Lite clock generator is not locked")
        if program_firmware:
            _program(scope, cw, firmware, attempts_path, platform_name)
        else:
            _append_attempt(attempts_path, {
                "kind": "programming",
                "at": _now(),
                "status": "skipped",
                "reason": "verify preloaded firmware before reuse",
                "firmware_sha256": _sha256(firmware),
                "platform": platform_name,
            })
        target = cw.target(scope, cw.targets.SimpleSerial)
        target.output_len = 16

        preflight_wave, preflight_output, valid, reason = _capture_aes_preflight(cw, scope, target, samples)
        _append_attempt(attempts_path, {
            "kind": "preflight",
            "at": _now(),
            "status": "accepted" if valid else "rejected",
            "stage": "initial",
            "reason": reason,
            "plaintext": NIST_PLAINTEXT.hex(),
            "response": preflight_output.hex(),
            "samples": 0 if preflight_wave is None else preflight_wave.size,
        })
        reprogrammed = False
        if not valid and not program_firmware:
            if preflight_wave is not None:
                np.save(run / "preflight_initial_trace.npy", preflight_wave)
            target.dis()
            target = None
            _program(scope, cw, firmware, attempts_path, platform_name)
            target = cw.target(scope, cw.targets.SimpleSerial)
            target.output_len = 16
            preflight_wave, preflight_output, valid, reason = _capture_aes_preflight(cw, scope, target, samples)
            _append_attempt(attempts_path, {
                "kind": "preflight",
                "at": _now(),
                "status": "accepted" if valid else "rejected",
                "stage": "after_reprogram",
                "reason": reason,
                "plaintext": NIST_PLAINTEXT.hex(),
                "response": preflight_output.hex(),
                "samples": 0 if preflight_wave is None else preflight_wave.size,
            })
            reprogrammed = True
        if preflight_wave is not None:
            np.save(run / "preflight_trace.npy", preflight_wave)
        if not valid:
            raise RuntimeError(f"AES preflight failed: {reason}")
        metadata["firmware_preflight"] = {
            "status": "passed",
            "reprogrammed_after_mismatch": reprogrammed,
        }
        metadata["preflight"] = {"status": "passed", "nist_vector": "FIPS-197 Appendix B Cipher Example", "response": preflight_output.hex()}

        rng = np.random.default_rng(seed)
        group_plan = None
        fixed_plaintext = np.frombuffer(bytes.fromhex("00112233445566778899aabbccddeeff"), dtype=np.uint8)
        if is_tvla:
            group_plan = np.repeat(np.array([0, 1], dtype=np.uint8), trace_count // 2)
            rng.shuffle(group_plan)
            metadata["tvla_groups"] = {"0": "fixed", "1": "random", "fixed_plaintext": fixed_plaintext.tobytes().hex()}
        for index in range(trace_count):
            group = int(group_plan[index]) if group_plan is not None else -1
            plaintext = fixed_plaintext.copy() if group == 0 else rng.integers(0, 256, size=16, dtype=np.uint8)
            trace = cw.capture_trace(scope, target, bytearray(plaintext), bytearray(AES_KEY), as_int=False)
            if trace is None:
                _append_attempt(attempts_path, {"kind": "claim_capture", "index": index, "at": _now(), "status": "rejected", "reason": "capture timeout", "plaintext": plaintext.tobytes().hex()})
                raise RuntimeError(f"AES capture {index} timed out; automatic retry is disabled")
            wave = _trace_wave(trace)
            valid, reason = validate_waveform(wave, samples, minimum_peak_to_peak=0.05)
            output = _trace_output(trace)
            if len(output) != 16:
                valid, reason = False, f"response length={len(output)}, expected=16"
            _append_attempt(attempts_path, {
                "kind": "claim_capture", "index": index, "at": _now(), "status": "accepted" if valid else "rejected",
                "reason": reason, "plaintext": plaintext.tobytes().hex(), "response": output.hex(), "samples": wave.size,
                "minimum": float(wave.min()), "maximum": float(wave.max()), "group": group,
            })
            if not valid:
                raise RuntimeError(f"AES capture {index} rejected: {reason}; automatic retry is disabled")
            traces.append(wave)
            plaintexts.append(plaintext)
            responses.append(np.frombuffer(output, dtype=np.uint8).copy())
            if is_tvla:
                groups.append(group)

        arrays: dict[str, Any] = {
            "traces": np.stack(traces),
            "plaintexts": np.stack(plaintexts),
            "responses": np.stack(responses),
            "key": AES_KEY,
            "sample_rate_hz": np.array(scope.clock.adc_freq),
        }
        if is_tvla:
            arrays["groups"] = np.asarray(groups, dtype=np.uint8)
        np.savez_compressed(run / "traces.npz", **arrays)
        metadata.update({"state": "complete", "finished_at": _now(), "accepted_trace_count": len(traces), "raw_artifact": "traces.npz"})
        _write_json(metadata_path, metadata)
        return run
    except Exception as error:
        if traces:
            np.savez_compressed(run / "partial_traces.npz", traces=np.stack(traces), plaintexts=np.stack(plaintexts), key=AES_KEY)
        metadata.update({"state": "failed", "finished_at": _now(), "accepted_trace_count": len(traces), "error": repr(error)})
        _write_json(metadata_path, metadata)
        raise
    finally:
        if target is not None:
            target.dis()
        if scope is not None:
            scope.dis()


def _drain_target(target: Any) -> str:
    import time

    chunks: list[str] = []
    waiting = target.in_waiting()
    while waiting > 0:
        chunks.append(str(target.read(waiting, 20)))
        time.sleep(0.01)
        waiting = target.in_waiting()
    return "".join(chunks)


def _prepare_password_target(
    scope: Any,
    cw: Any,
    firmware: Path,
    attempts_path: Path,
    platform_name: str,
    *,
    program_firmware: bool,
) -> tuple[Any, bool]:
    """Connect to the password target, programming once if the loaded image is wrong."""

    if program_firmware:
        _program(scope, cw, firmware, attempts_path, platform_name)
    else:
        _append_attempt(attempts_path, {
            "kind": "programming",
            "at": _now(),
            "status": "skipped",
            "reason": "verify preloaded firmware before reuse",
            "firmware_sha256": _sha256(firmware),
            "platform": platform_name,
        })

    target = cw.target(scope, cw.targets.SimpleSerial)
    _reset_target(scope)
    boot_output = _drain_target(target)
    valid = "Safe-o-matic 3000" in boot_output
    _append_attempt(attempts_path, {
        "kind": "firmware_preflight",
        "at": _now(),
        "status": "accepted" if valid else "rejected",
        "stage": "initial",
        "boot_output_prefix": boot_output[:160],
        "reason": "password boot banner observed" if valid else "password boot banner missing",
    })
    if valid:
        return target, False

    target.dis()
    if program_firmware:
        raise RuntimeError("password firmware boot banner missing after programming")

    _program(scope, cw, firmware, attempts_path, platform_name)
    target = cw.target(scope, cw.targets.SimpleSerial)
    _reset_target(scope)
    boot_output = _drain_target(target)
    valid = "Safe-o-matic 3000" in boot_output
    _append_attempt(attempts_path, {
        "kind": "firmware_preflight",
        "at": _now(),
        "status": "accepted" if valid else "rejected",
        "stage": "after_reprogram",
        "boot_output_prefix": boot_output[:160],
        "reason": "password boot banner observed" if valid else "password boot banner missing",
    })
    if not valid:
        target.dis()
        raise RuntimeError("password firmware boot banner missing after one recovery programming attempt")
    return target, True


def _password_capture(
    scope: Any,
    target: Any,
    guess: str,
    samples: int,
    *,
    minimum_peak_to_peak: float = 1e-6,
) -> tuple[np.ndarray, str, str]:
    import time

    _reset_target(scope)
    boot_output = _drain_target(target)
    scope.arm()
    target.write(guess + "\n")
    timed_out = scope.capture()
    if timed_out:
        raise RuntimeError("password capture timeout")
    wave = np.asarray(scope.get_last_trace(), dtype=np.float32)
    valid, reason = validate_waveform(wave, samples, minimum_peak_to_peak=minimum_peak_to_peak)
    if not valid:
        raise RuntimeError(reason)
    time.sleep(0.02)
    response = _drain_target(target)
    return wave, boot_output, response


class PasswordCaptureSession:
    """Jupyter 셀마다 비밀번호 추측을 캡처하고 즉시 run에 보존한다."""

    def __init__(
        self,
        firmware_hex: str | Path,
        *,
        samples: int = 3000,
        gain_db: float = 25.0,
        runs_root: str | Path = "runs",
        serial_number: str | None = None,
        platform_name: str = "CWLITEARM",
        target_identification: str = "STM32F303",
        program_firmware: bool = False,
    ) -> None:
        import chipwhisperer as cw

        self.firmware = Path(firmware_hex).resolve()
        if not self.firmware.is_file():
            raise FileNotFoundError(self.firmware)
        self.samples = samples
        self.run = _new_run(Path(runs_root), "password-interactive")
        self.attempts_path = self.run / "attempts.jsonl"
        self.metadata_path = self.run / "metadata.json"
        self.traces: list[np.ndarray] = []
        self.guesses: list[str] = []
        self.responses: list[str] = []
        self.scope = None
        self.target = None
        self.closed = False
        self.metadata: dict[str, Any] = {
            "schema_version": 1,
            "run_id": self.run.name,
            "kind": "measured_password_interactive",
            "state": "running",
            "started_at": _now(),
            "evidence_origin": "measured",
            "evidence_purpose": "teaching",
            "measurement_scope": f"interactive CW-Lite password traces on {target_identification}",
            "claim_scope": "cell-by-cell traces for the bundled early-exit password comparison",
            "target_identity": {
                "platform": platform_name,
                "user_identification": target_identification,
                "software_verified_exact_board_variant": False,
            },
            "firmware": {
                "path": str(self.firmware),
                "sha256": _sha256(self.firmware),
                "ss_ver": "SS_VER_1_0",
            },
            "program_firmware": program_firmware,
            "host": {
                "python": platform.python_version(),
                "platform": platform.platform(),
                "chipwhisperer": cw.__version__,
            },
        }
        _write_json(self.metadata_path, self.metadata)
        try:
            device = _select_device(cw, serial_number)
            self.scope = cw.scope(sn=device["sn"])
            self.scope.default_setup()
            self.scope.adc.samples = samples
            self.scope.gain.db = gain_db
            self.metadata["measurement_setup"] = _scope_snapshot(self.scope, device, samples=samples)
            if not self.scope.clock.clkgen_locked:
                raise RuntimeError("CW-Lite clock generator is not locked")
            self.target, reprogrammed = _prepare_password_target(
                self.scope,
                cw,
                self.firmware,
                self.attempts_path,
                platform_name,
                program_firmware=program_firmware,
            )
            self.metadata["firmware_preflight"] = {
                "status": "passed",
                "reprogrammed_after_mismatch": reprogrammed,
            }
            _write_json(self.metadata_path, self.metadata)
        except Exception as error:
            self.metadata.update({"state": "failed", "finished_at": _now(), "error": repr(error)})
            _write_json(self.metadata_path, self.metadata)
            self._disconnect()
            raise

    def capture(self, guess: str) -> np.ndarray:
        """한 추측을 측정하고 원시 파형·UART 응답·시도 기록을 저장한다."""

        if self.closed:
            raise RuntimeError("capture session is already closed")
        index = len(self.traces)
        try:
            wave, boot_output, response = _password_capture(
                self.scope,
                self.target,
                guess,
                self.samples,
                minimum_peak_to_peak=50.0,
            )
            if "Safe-o-matic 3000" not in boot_output:
                raise RuntimeError("expected password firmware boot banner was not observed")
        except Exception as error:
            _append_attempt(self.attempts_path, {
                "kind": "interactive_capture",
                "index": index,
                "guess_hex": guess.encode().hex(),
                "at": _now(),
                "status": "rejected",
                "reason": repr(error),
            })
            self.metadata.update({"state": "failed", "finished_at": _now(), "error": repr(error)})
            _write_json(self.metadata_path, self.metadata)
            self._disconnect()
            raise

        _append_attempt(self.attempts_path, {
            "kind": "interactive_capture",
            "index": index,
            "guess_hex": guess.encode().hex(),
            "at": _now(),
            "status": "accepted",
            "samples": wave.size,
            "response": response[:160],
            "minimum": float(wave.min()),
            "maximum": float(wave.max()),
            "peak_to_peak": float(np.ptp(wave)),
        })
        self.traces.append(wave)
        self.guesses.append(guess)
        self.responses.append(response)
        self._persist("running")
        return wave

    def finish(self) -> Path:
        """run을 완료 상태로 저장하고 scope와 target 연결을 닫는다."""

        if not self.closed:
            self._persist("complete")
            self._disconnect()
        return self.run

    def _persist(self, state: str) -> None:
        arrays: dict[str, Any] = {
            "traces": np.stack(self.traces) if self.traces else np.empty((0, self.samples), dtype=np.float32),
            "guesses": np.asarray(self.guesses),
            "responses": np.asarray(self.responses),
        }
        if self.scope is not None:
            arrays["sample_rate_hz"] = np.array(self.scope.clock.adc_freq)
        np.savez_compressed(self.run / "traces.npz", **arrays)
        self.metadata.update({
            "state": state,
            "accepted_trace_count": len(self.traces),
            "raw_artifact": "traces.npz",
        })
        if state == "complete":
            self.metadata["finished_at"] = _now()
        _write_json(self.metadata_path, self.metadata)

    def _disconnect(self) -> None:
        if self.target is not None:
            self.target.dis()
            self.target = None
        if self.scope is not None:
            self.scope.dis()
            self.scope = None
        self.closed = True


def capture_password_run(
    firmware_hex: str | Path,
    *,
    repeats: int = 1,
    samples: int = 3000,
    score_samples: int = 3000,
    gain_db: float = 25.0,
    positions_to_recover: int = 5,
    runs_root: str | Path = "runs",
    serial_number: str | None = None,
    platform_name: str = "CWLITEARM",
    target_identification: str = "STM32F303",
    program_firmware: bool = True,
) -> Path:
    """조기 종료 비밀번호 비교의 파형을 수집하고 다섯 글자를 순차 복구한다."""

    import chipwhisperer as cw

    firmware = Path(firmware_hex).resolve()
    if not firmware.is_file():
        raise FileNotFoundError(firmware)
    run = _new_run(Path(runs_root), "password-spa")
    attempts_path = run / "attempts.jsonl"
    metadata_path = run / "metadata.json"
    metadata: dict[str, Any] = {
        "schema_version": 1,
        "run_id": run.name,
        "kind": "measured_password_spa",
        "state": "running",
        "started_at": _now(),
        "evidence_origin": "measured",
        "evidence_purpose": "claim_bearing",
        "measurement_scope": f"CW-Lite power capture of bundled early-exit password comparison on {target_identification}",
        "claim_scope": "timing/SPA recovery of the bundled early-exit comparison password",
        "target_identity": {"platform": platform_name, "user_identification": target_identification, "software_verified_exact_board_variant": False},
        "firmware": {"path": str(firmware), "sha256": _sha256(firmware), "ss_ver": "SS_VER_1_0"},
        "repeats": repeats,
        "program_firmware": program_firmware,
        "score_samples": score_samples,
        "scoring": "sum(abs(candidate_mean - invalid_reference_mean)) over the configured sample window",
        "capture_order": "alphabetical, matching upstream Lab 2_1B",
        "positions_to_recover": positions_to_recover,
        "host": {"python": platform.python_version(), "platform": platform.platform(), "chipwhisperer": cw.__version__},
    }
    _write_json(metadata_path, metadata)
    scope = None
    target = None
    traces: list[np.ndarray] = []
    guesses: list[str] = []
    positions: list[int] = []
    kinds: list[str] = []
    decisions: list[dict[str, Any]] = []
    try:
        device = _select_device(cw, serial_number)
        scope = cw.scope(sn=device["sn"])
        scope.default_setup()
        scope.adc.samples = samples
        scope.gain.db = gain_db
        metadata["measurement_setup"] = _scope_snapshot(scope, device, samples=samples)
        if not scope.clock.clkgen_locked:
            raise RuntimeError("CW-Lite clock generator is not locked")
        target, reprogrammed = _prepare_password_target(
            scope,
            cw,
            firmware,
            attempts_path,
            platform_name,
            program_firmware=program_firmware,
        )
        metadata["firmware_preflight"] = {
            "status": "passed",
            "reprogrammed_after_mismatch": reprogrammed,
        }

        metadata["minimum_peak_to_peak"] = 50.0
        preflight_wave, boot_output, preflight_response = _password_capture(scope, target, "h", samples, minimum_peak_to_peak=50.0)
        np.save(run / "preflight_trace.npy", preflight_wave)
        preflight_valid = "PASSWORD FAIL" in preflight_response
        _append_attempt(attempts_path, {
            "kind": "preflight",
            "at": _now(),
            "status": "accepted" if preflight_valid else "rejected",
            "guess": "h",
            "samples": preflight_wave.size,
            "boot_output_prefix": boot_output[:120],
            "response": preflight_response[:120],
            "reason": "expected PASSWORD FAIL" if not preflight_valid else "accepted",
        })
        if not preflight_valid:
            raise RuntimeError(f"password firmware preflight failed: {preflight_response!r}")
        metadata["preflight"] = {"status": "passed", "guess": "h", "response": preflight_response[:120]}

        prefix = ""
        for position in range(positions_to_recover):
            position_traces: dict[str, list[np.ndarray]] = {candidate: [] for candidate in PASSWORD_ALPHABET}
            reference_traces: list[np.ndarray] = []
            for repeat in range(repeats):
                guess = prefix + "\x01"
                try:
                    wave, _, response = _password_capture(scope, target, guess, samples, minimum_peak_to_peak=50.0)
                except Exception as error:
                    _append_attempt(attempts_path, {"kind": "reference", "position": position, "repeat": repeat, "guess_hex": guess.encode().hex(), "at": _now(), "status": "rejected", "reason": repr(error)})
                    raise
                _append_attempt(attempts_path, {"kind": "reference", "position": position, "repeat": repeat, "guess_hex": guess.encode().hex(), "at": _now(), "status": "accepted", "samples": wave.size, "response": response[:120]})
                reference_traces.append(wave)
                traces.append(wave); guesses.append(guess); positions.append(position); kinds.append("reference")

                for candidate in PASSWORD_ALPHABET:
                    guess = prefix + candidate
                    try:
                        wave, _, response = _password_capture(scope, target, guess, samples, minimum_peak_to_peak=50.0)
                    except Exception as error:
                        _append_attempt(attempts_path, {"kind": "candidate", "position": position, "repeat": repeat, "candidate": candidate, "guess": guess, "at": _now(), "status": "rejected", "reason": repr(error)})
                        raise
                    _append_attempt(attempts_path, {"kind": "candidate", "position": position, "repeat": repeat, "candidate": candidate, "guess": guess, "at": _now(), "status": "accepted", "samples": wave.size, "response": response[:120]})
                    position_traces[candidate].append(wave)
                    traces.append(wave); guesses.append(guess); positions.append(position); kinds.append("candidate")

            reference_mean = np.mean(reference_traces, axis=0)[:score_samples]
            scores = {
                candidate: float(np.sum(np.abs(np.mean(position_traces[candidate], axis=0)[:score_samples] - reference_mean)))
                for candidate in PASSWORD_ALPHABET
            }
            selected = max(scores, key=scores.get)
            prefix += selected
            decisions.append({
                "position": position,
                "selected": selected,
                "prefix": prefix,
                "scores": scores,
            })

        np.savez_compressed(
            run / "traces.npz",
            traces=np.stack(traces),
            guesses=np.asarray(guesses),
            positions=np.asarray(positions, dtype=np.int8),
            kinds=np.asarray(kinds),
            sample_rate_hz=np.array(scope.clock.adc_freq),
        )
        expected_prefix = "h0px3"[:positions_to_recover]
        if prefix != expected_prefix:
            raise RuntimeError(f"password recovery validation failed: recovered={prefix!r}, expected={expected_prefix!r}")
        metadata.update({"state": "complete", "finished_at": _now(), "accepted_trace_count": len(traces), "recovered_password": prefix, "recovery_validation": "passed", "decisions": decisions, "raw_artifact": "traces.npz"})
        _write_json(metadata_path, metadata)
        return run
    except Exception as error:
        if traces:
            np.savez_compressed(run / "partial_traces.npz", traces=np.stack(traces), guesses=np.asarray(guesses), positions=np.asarray(positions), kinds=np.asarray(kinds))
        metadata.update({"state": "failed", "finished_at": _now(), "accepted_trace_count": len(traces), "decisions": decisions, "error": repr(error)})
        _write_json(metadata_path, metadata)
        raise
    finally:
        if target is not None:
            target.dis()
        if scope is not None:
            scope.dis()


def diagnose_password_signal(
    firmware_hex: str | Path,
    *,
    gains_db: tuple[float, ...] = (25.0, 35.0, 45.0),
    repeats: int = 3,
    samples: int = 3000,
    runs_root: str | Path = "runs",
    serial_number: str | None = None,
    platform_name: str = "CWLITEARM",
    target_identification: str = "STM32F303",
) -> Path:
    """UART 분기와 gain별 ADC 진폭을 분리해서 확인하는 짧은 진단 run."""

    import chipwhisperer as cw

    firmware = Path(firmware_hex).resolve()
    if not firmware.is_file():
        raise FileNotFoundError(firmware)
    run = _new_run(Path(runs_root), "password-signal-diagnostic")
    attempts_path = run / "attempts.jsonl"
    metadata_path = run / "metadata.json"
    metadata: dict[str, Any] = {
        "schema_version": 1,
        "run_id": run.name,
        "kind": "measured_password_signal_diagnostic",
        "state": "running",
        "started_at": _now(),
        "evidence_origin": "measured",
        "evidence_purpose": "diagnostic",
        "measurement_scope": f"UART response and ADC signal-level diagnostic on {target_identification}",
        "claim_scope": "UART branch validation and ADC signal-level diagnosis only",
        "target_identity": {"platform": platform_name, "user_identification": target_identification},
        "firmware": {"path": str(firmware), "sha256": _sha256(firmware)},
        "gains_db": list(gains_db),
        "repeats": repeats,
        "samples": samples,
        "host": {"python": platform.python_version(), "platform": platform.platform(), "chipwhisperer": cw.__version__},
    }
    _write_json(metadata_path, metadata)
    scope = None
    target = None
    traces: list[np.ndarray] = []
    labels: list[str] = []
    gain_values: list[float] = []
    try:
        device = _select_device(cw, serial_number)
        scope = cw.scope(sn=device["sn"])
        scope.default_setup()
        scope.adc.samples = samples
        metadata["measurement_setup"] = _scope_snapshot(scope, device, samples=samples)
        _program(scope, cw, firmware, attempts_path, platform_name)
        target = cw.target(scope, cw.targets.SimpleSerial)
        cases = (
            ("invalid", "\x01", "PASSWORD FAIL"),
            ("first_correct", "h", "PASSWORD FAIL"),
            ("full_correct", "h0px3", "Access granted"),
        )
        for gain_db in gains_db:
            scope.gain.db = gain_db
            for repeat in range(repeats):
                for label, guess, expected_response in cases:
                    wave, boot_output, response = _password_capture(scope, target, guess, samples)
                    response_ok = expected_response in response
                    record = {
                        "kind": "signal_diagnostic",
                        "gain_db": float(scope.gain.db),
                        "repeat": repeat,
                        "label": label,
                        "guess_hex": guess.encode().hex(),
                        "status": "accepted" if response_ok else "rejected",
                        "expected_response": expected_response,
                        "response": response[:160],
                        "boot_output_prefix": boot_output[:80],
                        "minimum": float(wave.min()),
                        "maximum": float(wave.max()),
                        "peak_to_peak": float(np.ptp(wave)),
                        "standard_deviation": float(wave.std()),
                        "clipped_low": bool(np.any(wave == 0)),
                        "clipped_high": bool(np.any(wave == 1023)),
                    }
                    _append_attempt(attempts_path, record)
                    if not response_ok:
                        raise RuntimeError(f"UART response mismatch for {label}: {response!r}")
                    traces.append(wave)
                    labels.append(label)
                    gain_values.append(float(scope.gain.db))

        trace_array = np.stack(traces)
        label_array = np.asarray(labels)
        gain_array = np.asarray(gain_values)
        summaries: list[dict[str, Any]] = []
        for requested_gain in gains_db:
            observed_gain = min(set(gain_values), key=lambda value: abs(value - requested_gain))
            gain_mask = np.isclose(gain_array, observed_gain)
            invalid_mean = trace_array[gain_mask & (label_array == "invalid")].mean(axis=0)
            first_mean = trace_array[gain_mask & (label_array == "first_correct")].mean(axis=0)
            full_mean = trace_array[gain_mask & (label_array == "full_correct")].mean(axis=0)
            summaries.append({
                "requested_gain_db": requested_gain,
                "observed_gain_db": observed_gain,
                "median_peak_to_peak": float(np.median(np.ptp(trace_array[gain_mask], axis=1))),
                "median_standard_deviation": float(np.median(trace_array[gain_mask].std(axis=1))),
                "sad_first_correct_vs_invalid": float(np.sum(np.abs(first_mean - invalid_mean))),
                "sad_full_correct_vs_invalid": float(np.sum(np.abs(full_mean - invalid_mean))),
                "minimum": float(trace_array[gain_mask].min()),
                "maximum": float(trace_array[gain_mask].max()),
            })
        np.savez_compressed(run / "traces.npz", traces=trace_array, labels=label_array, gains_db=gain_array)
        metadata.update({"state": "complete", "finished_at": _now(), "accepted_trace_count": len(traces), "uart_validation": "passed", "gain_summaries": summaries, "raw_artifact": "traces.npz"})
        _write_json(metadata_path, metadata)
        return run
    except Exception as error:
        if traces:
            np.savez_compressed(run / "partial_traces.npz", traces=np.stack(traces), labels=np.asarray(labels), gains_db=np.asarray(gain_values))
        metadata.update({"state": "failed", "finished_at": _now(), "accepted_trace_count": len(traces), "error": repr(error)})
        _write_json(metadata_path, metadata)
        raise
    finally:
        if target is not None:
            target.dis()
        if scope is not None:
            scope.dis()


def latest_complete_run(runs_root: str | Path, kind: str) -> Path:
    """지정한 kind의 가장 최근 완료 run을 찾는다."""

    matches: list[Path] = []
    for metadata_path in Path(runs_root).glob("*/metadata.json"):
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        recovery_is_valid = kind != "measured_password_spa" or metadata.get("recovery_validation") == "passed"
        if metadata.get("kind") == kind and metadata.get("state") == "complete" and recovery_is_valid:
            matches.append(metadata_path.parent)
    if not matches:
        raise FileNotFoundError(f"완료된 {kind} run이 {runs_root}에 없습니다")
    return max(matches, key=lambda path: path.name)
