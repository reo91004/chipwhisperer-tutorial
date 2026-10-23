from __future__ import annotations

import json
import inspect
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

import numpy as np

from cw_sca_tutorial.analysis import cpa_correlations, dpa_differences, recover_key_cpa, welch_t_test
from cw_sca_tutorial.demo import repository_root
from cw_sca_tutorial.hardware import PasswordCaptureSession, _prepare_password_target, _trace_output, _trace_wave, capture_aes_run, capture_password_run, validate_waveform
from cw_sca_tutorial.synthetic import AES_KEY, PASSWORD_ALPHABET, make_aes_dataset, make_tvla_dataset, password_candidate_batch


class TutorialAnalysisTests(unittest.TestCase):
    def test_repository_root_finds_prebuilt_firmware(self) -> None:
        root = repository_root()
        self.assertTrue((root / "firmware" / "prebuilt" / "basic-passwdcheck-CWLITEARM.hex").is_file())

    def test_capture_functions_program_firmware_by_default(self) -> None:
        self.assertIs(inspect.signature(capture_password_run).parameters["program_firmware"].default, True)
        self.assertIs(inspect.signature(capture_aes_run).parameters["program_firmware"].default, True)
        self.assertIs(inspect.signature(PasswordCaptureSession).parameters["program_firmware"].default, False)

    def test_password_target_reprograms_once_after_firmware_mismatch(self) -> None:
        class FakeTarget:
            def __init__(self, output: str) -> None:
                self.output = output
                self.disconnected = False

            def in_waiting(self) -> int:
                return len(self.output)

            def read(self, length: int, timeout: int) -> str:
                chunk = self.output[:length]
                self.output = self.output[length:]
                return chunk

            def dis(self) -> None:
                self.disconnected = True

        class FakeChipWhisperer:
            targets = SimpleNamespace(SimpleSerial=object())
            programmers = SimpleNamespace(STM32FProgrammer=object())

            def __init__(self, targets: list[FakeTarget]) -> None:
                self.remaining_targets = targets.copy()
                self.program_calls: list[str] = []

            def target(self, scope: object, target_type: object) -> FakeTarget:
                return self.remaining_targets.pop(0)

            def program_target(self, scope: object, programmer: object, firmware: str) -> None:
                self.program_calls.append(firmware)

        initial_target = FakeTarget("TinyAES boot")
        recovered_target = FakeTarget("Safe-o-matic 3000")
        cw = FakeChipWhisperer([initial_target, recovered_target])
        scope = SimpleNamespace(io=SimpleNamespace(nrst=None))

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            firmware = root / "password.hex"
            firmware.write_text(":00000001FF\n", encoding="ascii")
            attempts_path = root / "attempts.jsonl"
            target, reprogrammed = _prepare_password_target(
                scope,
                cw,
                firmware,
                attempts_path,
                "CWLITEARM",
                program_firmware=False,
            )

            records = [json.loads(line) for line in attempts_path.read_text(encoding="utf-8").splitlines()]

        self.assertIs(target, recovered_target)
        self.assertTrue(reprogrammed)
        self.assertTrue(initial_target.disconnected)
        self.assertEqual(cw.program_calls, [str(firmware)])
        self.assertEqual(
            [(record.get("stage"), record["status"]) for record in records if record["kind"] == "firmware_preflight"],
            [("initial", "rejected"), ("after_reprogram", "accepted")],
        )

    def test_password_sad_recovers_all_characters(self) -> None:
        prefix = ""
        for _ in range(5):
            candidates, reference = password_candidate_batch(prefix, repeats=4)
            scores = np.sum(np.abs(candidates - reference), axis=1)
            prefix += PASSWORD_ALPHABET[int(np.argmax(scores))]
        self.assertEqual(prefix, "h0px3")

    def test_dpa_recovers_first_key_byte(self) -> None:
        dataset = make_aes_dataset(trace_count=700)
        differences = dpa_differences(dataset.traces, dataset.plaintexts, byte_index=0, bit=0)
        scores = np.max(np.abs(differences), axis=1)
        self.assertEqual(int(np.argmax(scores)), int(AES_KEY[0]))

    def test_fixed_vs_random_tvla_detects_synthetic_leakage(self) -> None:
        dataset, groups = make_tvla_dataset(traces_per_group=200)
        t_values = welch_t_test(dataset.traces, groups)
        self.assertGreater(float(np.max(np.abs(t_values))), 4.5)
        self.assertLess(float(np.max(np.abs(t_values[:50]))), 4.5)

    def test_cpa_recovers_full_key_and_wrong_window_is_weaker(self) -> None:
        dataset = make_aes_dataset(trace_count=420)
        recovered, _, _ = recover_key_cpa(dataset.traces, dataset.plaintexts)
        np.testing.assert_array_equal(recovered, AES_KEY)

        correlations = cpa_correlations(dataset.traces, dataset.plaintexts, byte_index=0)
        true_guess = int(AES_KEY[0])
        self.assertGreater(
            float(np.max(np.abs(correlations[true_guess]))),
            float(np.max(np.abs(correlations[true_guess, :50]))),
        )

    def test_waveform_validity_gate(self) -> None:
        self.assertEqual(validate_waveform(np.arange(5.0), 5), (True, "accepted"))
        self.assertFalse(validate_waveform(np.ones(5), 5)[0])
        self.assertFalse(validate_waveform(np.arange(4.0), 5)[0])
        self.assertFalse(validate_waveform(np.arange(5.0), 5, minimum_peak_to_peak=10.0)[0])

    def test_chipwhisperer_v7_trace_container_fields(self) -> None:
        class Container:
            trace = np.arange(5.0)
            ciphertext = bytearray.fromhex("00112233")

        np.testing.assert_array_equal(_trace_wave(Container()), np.arange(5.0))
        self.assertEqual(_trace_output(Container()), bytes.fromhex("00112233"))



if __name__ == "__main__":
    unittest.main()
