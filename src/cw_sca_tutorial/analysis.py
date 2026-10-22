"""작고 직접적인 DPA/CPA 구현.

교육용 구현이지만 점수는 실제 입력 파형에서 계산한다. 실패한 계산을 0이나
임의의 키로 대체하지 않는다.
"""

from __future__ import annotations

import numpy as np


AES_SBOX = np.array([
    0x63, 0x7C, 0x77, 0x7B, 0xF2, 0x6B, 0x6F, 0xC5, 0x30, 0x01, 0x67, 0x2B, 0xFE, 0xD7, 0xAB, 0x76,
    0xCA, 0x82, 0xC9, 0x7D, 0xFA, 0x59, 0x47, 0xF0, 0xAD, 0xD4, 0xA2, 0xAF, 0x9C, 0xA4, 0x72, 0xC0,
    0xB7, 0xFD, 0x93, 0x26, 0x36, 0x3F, 0xF7, 0xCC, 0x34, 0xA5, 0xE5, 0xF1, 0x71, 0xD8, 0x31, 0x15,
    0x04, 0xC7, 0x23, 0xC3, 0x18, 0x96, 0x05, 0x9A, 0x07, 0x12, 0x80, 0xE2, 0xEB, 0x27, 0xB2, 0x75,
    0x09, 0x83, 0x2C, 0x1A, 0x1B, 0x6E, 0x5A, 0xA0, 0x52, 0x3B, 0xD6, 0xB3, 0x29, 0xE3, 0x2F, 0x84,
    0x53, 0xD1, 0x00, 0xED, 0x20, 0xFC, 0xB1, 0x5B, 0x6A, 0xCB, 0xBE, 0x39, 0x4A, 0x4C, 0x58, 0xCF,
    0xD0, 0xEF, 0xAA, 0xFB, 0x43, 0x4D, 0x33, 0x85, 0x45, 0xF9, 0x02, 0x7F, 0x50, 0x3C, 0x9F, 0xA8,
    0x51, 0xA3, 0x40, 0x8F, 0x92, 0x9D, 0x38, 0xF5, 0xBC, 0xB6, 0xDA, 0x21, 0x10, 0xFF, 0xF3, 0xD2,
    0xCD, 0x0C, 0x13, 0xEC, 0x5F, 0x97, 0x44, 0x17, 0xC4, 0xA7, 0x7E, 0x3D, 0x64, 0x5D, 0x19, 0x73,
    0x60, 0x81, 0x4F, 0xDC, 0x22, 0x2A, 0x90, 0x88, 0x46, 0xEE, 0xB8, 0x14, 0xDE, 0x5E, 0x0B, 0xDB,
    0xE0, 0x32, 0x3A, 0x0A, 0x49, 0x06, 0x24, 0x5C, 0xC2, 0xD3, 0xAC, 0x62, 0x91, 0x95, 0xE4, 0x79,
    0xE7, 0xC8, 0x37, 0x6D, 0x8D, 0xD5, 0x4E, 0xA9, 0x6C, 0x56, 0xF4, 0xEA, 0x65, 0x7A, 0xAE, 0x08,
    0xBA, 0x78, 0x25, 0x2E, 0x1C, 0xA6, 0xB4, 0xC6, 0xE8, 0xDD, 0x74, 0x1F, 0x4B, 0xBD, 0x8B, 0x8A,
    0x70, 0x3E, 0xB5, 0x66, 0x48, 0x03, 0xF6, 0x0E, 0x61, 0x35, 0x57, 0xB9, 0x86, 0xC1, 0x1D, 0x9E,
    0xE1, 0xF8, 0x98, 0x11, 0x69, 0xD9, 0x8E, 0x94, 0x9B, 0x1E, 0x87, 0xE9, 0xCE, 0x55, 0x28, 0xDF,
    0x8C, 0xA1, 0x89, 0x0D, 0xBF, 0xE6, 0x42, 0x68, 0x41, 0x99, 0x2D, 0x0F, 0xB0, 0x54, 0xBB, 0x16,
], dtype=np.uint8)

_HW = np.array([i.bit_count() for i in range(256)], dtype=np.uint8)


def hamming_weight(values: np.ndarray) -> np.ndarray:
    """uint8 값들의 해밍 무게를 같은 모양으로 반환한다."""

    return _HW[np.asarray(values, dtype=np.uint8)]


def _validated(traces: np.ndarray, plaintexts: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    traces = np.asarray(traces, dtype=np.float64)
    plaintexts = np.asarray(plaintexts, dtype=np.uint8)
    if traces.ndim != 2 or plaintexts.ndim != 2 or plaintexts.shape[1] != 16:
        raise ValueError("traces는 (파형 수, 샘플 수), plaintexts는 (파형 수, 16)이어야 합니다")
    if traces.shape[0] != plaintexts.shape[0] or traces.shape[0] < 2:
        raise ValueError("파형과 평문의 개수가 같고 2개 이상이어야 합니다")
    if not np.isfinite(traces).all():
        raise ValueError("파형에 NaN 또는 무한대가 있습니다")
    return traces, plaintexts


def leakage_hypotheses(plaintexts: np.ndarray, byte_index: int) -> np.ndarray:
    """모든 256개 키 후보의 HW(SBox[평문 XOR 키]) 행렬을 만든다."""

    plaintexts = np.asarray(plaintexts, dtype=np.uint8)
    if not 0 <= byte_index < 16:
        raise ValueError("byte_index는 0..15 범위여야 합니다")
    guesses = np.arange(256, dtype=np.uint8)[:, None]
    return hamming_weight(AES_SBOX[np.bitwise_xor(guesses, plaintexts[:, byte_index])])


def dpa_differences(
    traces: np.ndarray,
    plaintexts: np.ndarray,
    *,
    byte_index: int = 0,
    bit: int = 0,
) -> np.ndarray:
    """SBox 출력 한 비트로 나눈 두 그룹 평균의 차이를 키 후보별로 계산한다."""

    traces, plaintexts = _validated(traces, plaintexts)
    if not 0 <= bit < 8:
        raise ValueError("bit는 0..7 범위여야 합니다")
    guesses = np.arange(256, dtype=np.uint8)[:, None]
    intermediate = AES_SBOX[np.bitwise_xor(guesses, plaintexts[:, byte_index])]
    groups = ((intermediate >> bit) & 1).astype(np.float64)
    ones = groups.sum(axis=1)
    zeros = traces.shape[0] - ones
    if np.any(ones == 0) or np.any(zeros == 0):
        raise ValueError("DPA 그룹 중 하나가 비었습니다. 더 다양한 평문이 필요합니다")
    return (groups @ traces) / ones[:, None] - ((1.0 - groups) @ traces) / zeros[:, None]


def welch_t_test(traces: np.ndarray, groups: np.ndarray) -> np.ndarray:
    """두 독립 파형군의 샘플별 Welch t-value를 계산한다."""

    traces = np.asarray(traces, dtype=np.float64)
    groups = np.asarray(groups)
    if traces.ndim != 2 or groups.shape != (traces.shape[0],):
        raise ValueError("traces는 2차원이고 groups는 파형 수와 같은 길이여야 합니다")
    labels = np.unique(groups)
    if labels.size != 2:
        raise ValueError("Welch t-test에는 정확히 두 그룹이 필요합니다")
    first = traces[groups == labels[0]]
    second = traces[groups == labels[1]]
    if first.shape[0] < 2 or second.shape[0] < 2:
        raise ValueError("각 그룹에 파형이 2개 이상 필요합니다")
    numerator = first.mean(axis=0) - second.mean(axis=0)
    denominator = np.sqrt(first.var(axis=0, ddof=1) / first.shape[0] + second.var(axis=0, ddof=1) / second.shape[0])
    result = np.divide(numerator, denominator, out=np.zeros_like(numerator), where=denominator != 0)
    result[(denominator == 0) & (numerator != 0)] = np.sign(numerator[(denominator == 0) & (numerator != 0)]) * np.inf
    return result


def cpa_correlations(traces: np.ndarray, plaintexts: np.ndarray, *, byte_index: int = 0) -> np.ndarray:
    """256개 키 후보와 각 시간 샘플의 Pearson 상관계수를 계산한다."""

    traces, plaintexts = _validated(traces, plaintexts)
    hypotheses = leakage_hypotheses(plaintexts, byte_index).astype(np.float64)
    hypotheses -= hypotheses.mean(axis=1, keepdims=True)
    centered = traces - traces.mean(axis=0, keepdims=True)
    numerator = hypotheses @ centered
    hypothesis_norm = np.sqrt(np.sum(hypotheses * hypotheses, axis=1, keepdims=True))
    trace_norm = np.sqrt(np.sum(centered * centered, axis=0, keepdims=True))
    denominator = hypothesis_norm * trace_norm
    return np.divide(numerator, denominator, out=np.zeros_like(numerator), where=denominator != 0)


def recover_key_cpa(traces: np.ndarray, plaintexts: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """AES-128 첫 라운드 누설에서 16바이트 키와 피크 점수/위치를 복구한다."""

    traces, plaintexts = _validated(traces, plaintexts)
    key = np.empty(16, dtype=np.uint8)
    scores = np.empty(16, dtype=np.float64)
    peaks = np.empty(16, dtype=np.int64)
    for byte_index in range(16):
        correlations = cpa_correlations(traces, plaintexts, byte_index=byte_index)
        candidate_scores = np.max(np.abs(correlations), axis=1)
        key[byte_index] = int(np.argmax(candidate_scores))
        scores[byte_index] = candidate_scores[key[byte_index]]
        peaks[byte_index] = int(np.argmax(np.abs(correlations[key[byte_index]])))
    return key, scores, peaks
