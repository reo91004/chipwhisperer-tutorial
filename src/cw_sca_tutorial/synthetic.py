"""수업 흐름을 항상 재현하기 위한 명시적 합성 파형 생성기."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .analysis import AES_SBOX, hamming_weight


PASSWORD_ALPHABET = "abcdefghijklmnopqrstuvwxyz0123456789"
AES_KEY = np.frombuffer(bytes.fromhex("2b7e151628aed2a6abf7158809cf4f3c"), dtype=np.uint8).copy()


@dataclass(frozen=True)
class SyntheticAesDataset:
    traces: np.ndarray
    plaintexts: np.ndarray
    key: np.ndarray
    sample_rate_hz: float
    leakage_positions: np.ndarray
    seed: int
    claim_scope: str = "synthetic leakage model; physical leakage is not measured"


def _pulse(samples: int, center: float, width: float) -> np.ndarray:
    x = np.arange(samples, dtype=np.float64)
    return np.exp(-0.5 * ((x - center) / width) ** 2)


def make_operation_dataset(*, repeats: int = 12, samples: int = 500, seed: int = 20261022) -> tuple[np.ndarray, np.ndarray]:
    """NOP, 곱셈, AES의 활동량 차이를 보여 주는 합성 파형 묶음."""

    rng = np.random.default_rng(seed)
    labels = np.repeat(np.array(["NOP", "MUL", "AES"]), repeats)
    traces = rng.normal(0.0, 0.10, size=(labels.size, samples))
    traces += 0.06 * np.sin(2 * np.pi * np.arange(samples) / 12.0)
    patterns = {
        "NOP": [(190, 0.6)],
        "MUL": [(185, 0.8), (205, -0.55), (224, 0.7)],
        "AES": [(130 + 24 * i, 0.75 + 0.05 * (i % 2)) for i in range(10)],
    }
    for row, label in enumerate(labels):
        shift = rng.integers(-1, 2)
        for center, amplitude in patterns[label]:
            traces[row] += amplitude * _pulse(samples, center + shift, 3.0)
    return traces.astype(np.float32), labels


def password_trace(
    guess: str,
    *,
    secret: str = "h0px3",
    samples: int = 800,
    rng: np.random.Generator,
) -> np.ndarray:
    """첫 불일치에서 종료되는 비교 루프의 합성 전력 파형 한 개."""

    trace = rng.normal(0.0, 0.09, samples)
    trace += 0.035 * np.sin(2 * np.pi * np.arange(samples) / 10.0)
    trace += 0.45 * _pulse(samples, 55, 5)
    for index, actual in enumerate(guess[: len(secret) + 1]):
        center = 135 + index * 105
        expected = secret[index] if index < len(secret) else "\0"
        trace += (0.28 + 0.015 * ord(actual).bit_count()) * _pulse(samples, center, 4.0)
        if actual == expected:
            trace += 0.70 * _pulse(samples, center + 22, 3.2)
        else:
            trace -= 0.45 * _pulse(samples, center + 25, 4.0)
            break
    return trace.astype(np.float32)


def password_candidate_batch(
    prefix: str,
    *,
    alphabet: str = PASSWORD_ALPHABET,
    repeats: int = 4,
    secret: str = "h0px3",
    seed: int = 20261022,
) -> tuple[np.ndarray, np.ndarray]:
    """후보별 평균 파형과 항상 틀리는 기준 파형을 반환한다."""

    rng = np.random.default_rng(seed + 1009 * len(prefix) + sum(map(ord, prefix)))
    reference = np.mean(
        [password_trace(prefix + "\x01", secret=secret, rng=rng) for _ in range(repeats)], axis=0
    )
    candidates = np.stack([
        np.mean(
            [password_trace(prefix + candidate + "\x01", secret=secret, rng=rng) for _ in range(repeats)],
            axis=0,
        )
        for candidate in alphabet
    ])
    return candidates.astype(np.float32), reference.astype(np.float32)


def make_aes_dataset(
    *,
    trace_count: int = 600,
    samples: int = 700,
    seed: int = 20261022,
    key: np.ndarray = AES_KEY,
    plaintexts: np.ndarray | None = None,
) -> SyntheticAesDataset:
    """HW(SBox[평문 XOR 키]) 누설을 포함한 정렬된 AES 합성 파형을 만든다."""

    if trace_count < 32 or samples < 620:
        raise ValueError("16바이트 누설을 분리하려면 trace_count>=32, samples>=620이 필요합니다")
    key = np.asarray(key, dtype=np.uint8)
    if key.shape != (16,):
        raise ValueError("key는 16바이트여야 합니다")
    rng = np.random.default_rng(seed)
    if plaintexts is None:
        plaintexts = rng.integers(0, 256, size=(trace_count, 16), dtype=np.uint8)
    else:
        plaintexts = np.asarray(plaintexts, dtype=np.uint8)
        if plaintexts.ndim != 2 or plaintexts.shape[1] != 16 or plaintexts.shape[0] < 32:
            raise ValueError("plaintexts는 (32개 이상, 16) 모양이어야 합니다")
        trace_count = plaintexts.shape[0]
    traces = rng.normal(0.0, 0.85, size=(trace_count, samples))
    positions = np.linspace(95, samples - 95, 16, dtype=np.int64)

    # 평균 파형에는 처리 구간이, 개별 파형 차이에는 데이터 의존 누설이 보인다.
    common = np.zeros(samples, dtype=np.float64)
    for round_center in np.linspace(70, samples - 70, 10):
        common += 0.36 * _pulse(samples, round_center, 7.0)
    traces += common
    traces += rng.normal(0.0, 0.08, size=(trace_count, 1))

    for byte_index, position in enumerate(positions):
        intermediate = AES_SBOX[np.bitwise_xor(plaintexts[:, byte_index], key[byte_index])]
        leakage = hamming_weight(intermediate).astype(np.float64) - 4.0
        traces += 0.43 * leakage[:, None] * _pulse(samples, position, 2.8)[None, :]

    return SyntheticAesDataset(
        traces=traces.astype(np.float32),
        plaintexts=plaintexts,
        key=key.copy(),
        sample_rate_hz=29_480_000.0,
        leakage_positions=positions,
        seed=seed,
    )


def make_tvla_dataset(
    *,
    traces_per_group: int = 300,
    samples: int = 700,
    seed: int = 20261022,
    key: np.ndarray = AES_KEY,
) -> tuple[SyntheticAesDataset, np.ndarray]:
    """표준 fixed-vs-random TVLA를 위한 균형 잡힌 합성 파형을 만든다."""

    if traces_per_group < 16:
        raise ValueError("각 TVLA 그룹에 파형이 16개 이상 필요합니다")
    rng = np.random.default_rng(seed)
    groups = np.repeat(np.array([0, 1], dtype=np.uint8), traces_per_group)
    rng.shuffle(groups)
    plaintexts = rng.integers(0, 256, size=(groups.size, 16), dtype=np.uint8)
    fixed_plaintext = np.frombuffer(bytes.fromhex("00112233445566778899aabbccddeeff"), dtype=np.uint8)
    plaintexts[groups == 0] = fixed_plaintext
    dataset = make_aes_dataset(samples=samples, seed=seed + 1, key=key, plaintexts=plaintexts)
    return dataset, groups
