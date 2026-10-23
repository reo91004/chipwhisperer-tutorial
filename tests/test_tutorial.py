from __future__ import annotations

import unittest
import inspect

import numpy as np

from cw_sca_tutorial.analysis import cpa_correlations, dpa_differences, recover_key_cpa, welch_t_test
from cw_sca_tutorial.demo import repository_root
from cw_sca_tutorial.hardware import _trace_output, _trace_wave, capture_aes_run, capture_password_run, validate_waveform
from cw_sca_tutorial.synthetic import AES_KEY, PASSWORD_ALPHABET, make_aes_dataset, make_tvla_dataset, password_candidate_batch


class TutorialAnalysisTests(unittest.TestCase):
    def test_repository_root_finds_prebuilt_firmware(self) -> None:
        root = repository_root()
        self.assertTrue((root / "firmware" / "prebuilt" / "basic-passwdcheck-CWLITEARM.hex").is_file())

    def test_capture_functions_program_firmware_by_default(self) -> None:
        self.assertIs(inspect.signature(capture_password_run).parameters["program_firmware"].default, True)
        self.assertIs(inspect.signature(capture_aes_run).parameters["program_firmware"].default, True)

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
