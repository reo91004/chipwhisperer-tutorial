"""ChipWhisperer 학부 부채널 분석 튜토리얼의 재현 가능한 핵심 함수."""

from .analysis import AES_SBOX, cpa_correlations, dpa_differences, hamming_weight, recover_key_cpa, welch_t_test
from .synthetic import AES_KEY, PASSWORD_ALPHABET, make_aes_dataset, make_operation_dataset, make_tvla_dataset, password_candidate_batch

__all__ = [
    "AES_KEY",
    "AES_SBOX",
    "PASSWORD_ALPHABET",
    "cpa_correlations",
    "dpa_differences",
    "hamming_weight",
    "make_aes_dataset",
    "make_operation_dataset",
    "make_tvla_dataset",
    "password_candidate_batch",
    "recover_key_cpa",
    "welch_t_test",
]
