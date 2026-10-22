#!/usr/bin/env python3
"""강의용 ipynb 다섯 개를 같은 내용으로 재생성한다."""

from __future__ import annotations

from pathlib import Path

import nbformat as nbf


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "notebooks"


def md(text: str):
    return nbf.v4.new_markdown_cell(text.strip())


def code(text: str):
    return nbf.v4.new_code_cell(text.strip())


def save(filename: str, title: str, cells: list) -> None:
    notebook = nbf.v4.new_notebook(
        cells=cells,
        metadata={
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.11"},
            "tutorial": {"title": title, "evidence": "measured" if filename.startswith("05_") else "synthetic"},
        },
    )
    nbf.write(notebook, OUT / filename)


def main() -> None:
    OUT.mkdir(exist_ok=True)

    save(
        "00_파형과_트리거.ipynb",
        "파형과 트리거",
        [
            md("""
# 00. 전력 파형과 트리거

같은 마이크로컨트롤러라도 실행하는 코드가 달라지면 전력 파형도 달라집니다. 이번 실습에서는 트리거로 연산 시작점을 맞춘 뒤 NOP, 곱셈, AES 파형을 비교합니다.

여기서 사용하는 데이터는 원리를 설명하려고 만든 합성 파형입니다. 실제 장치에서 누설을 측정한 결과는 아닙니다.
            """),
            code("""
import matplotlib.pyplot as plt
import numpy as np

from cw_sca_tutorial.synthetic import make_operation_dataset

plt.rcParams.update({"figure.figsize": (11, 4), "axes.grid": True})
traces, labels = make_operation_dataset()
print(f"파형 {traces.shape[0]}개 × 샘플 {traces.shape[1]}개")
            """),
            md("""
## 개별 파형과 평균

얇은 선은 개별 파형이고 굵은 선은 같은 연산을 여러 번 평균한 결과입니다. 모든 파형의 트리거를 샘플 0에 맞췄으므로 같은 연산 구간이 겹쳐 보입니다.
            """),
            code("""
colors = {"NOP": "#4c78a8", "MUL": "#f58518", "AES": "#e45756"}
fig, axes = plt.subplots(1, 2, figsize=(14, 4), sharex=True)
for label in ("NOP", "MUL", "AES"):
    group = traces[labels == label]
    axes[0].plot(group[:4].T, color=colors[label], alpha=0.18)
    axes[1].plot(group.mean(axis=0), color=colors[label], linewidth=2.4, label=label)
axes[0].set(title="Individual traces", xlabel="Samples after trigger", ylabel="Relative power")
axes[1].set(title="Mean traces", xlabel="Samples after trigger")
axes[1].legend()
plt.show()
            """),
            md("""
## Heatmap으로 보기

아래 heatmap의 한 행이 한 번의 실행입니다. AES에서는 반복되는 라운드가 보이고, MUL에서는 짧은 활동이 몇 차례 나타납니다. SPA(Simple Power Analysis)는 이런 큰 구조를 파형에서 직접 읽는 분석입니다.
            """),
            code("""
order = np.argsort(labels)
plt.figure(figsize=(12, 5))
plt.imshow(traces[order], aspect="auto", cmap="RdBu_r", vmin=-1.2, vmax=1.2)
plt.colorbar(label="Relative power")
plt.yticks([5, 17, 29], ["AES", "MUL", "NOP"])
plt.xlabel("Samples after trigger")
plt.title("Operation trace heatmap")
plt.show()
            """),
            md("""
## 정리

트리거는 반복 측정의 시간축을 맞추고 평균은 잡음을 줄입니다. 다음 노트북에서는 조기 종료가 비밀번호 비교 횟수를 어떻게 드러내는지 살펴보겠습니다.
            """),
        ],
    )

    save(
        "01_타이밍_SPA_비밀번호.ipynb",
        "타이밍과 SPA로 비밀번호 복구",
        [
            md("""
# 01. 타이밍과 SPA로 비밀번호 찾기

번들 펌웨어는 비밀번호를 앞에서부터 비교하고 첫 불일치에서 바로 `break`합니다.

```text
입력 h0p?  ── 비교 h ✓ ── 비교 0 ✓ ── 비교 p ✓ ── 비교 ? ✗ ── 종료
입력 a...  ── 비교 a ✗ ── 종료
```

앞부분이 맞을수록 비교 횟수가 늘고 파형에도 다음 비교가 추가됩니다. 먼저 고정 seed로 만든 합성 파형에서 이 차이를 확인합니다.
            """),
            md("""
## 후보 파형 준비

첫 글자 후보 36개와 항상 틀리는 기준 입력의 파형을 만듭니다. `correct_index`와 `wrong_index`는 그래프에서 `h`와 `a`를 바로 꺼내 비교하려고 사용합니다. 이 셀을 실행하면 아직 공격은 하지 않고 비교할 데이터만 준비합니다.
            """),
            code("""
import matplotlib.pyplot as plt
import numpy as np

from cw_sca_tutorial.synthetic import PASSWORD_ALPHABET, password_candidate_batch

plt.rcParams.update({"figure.figsize": (12, 4), "axes.grid": True})
candidates, reference = password_candidate_batch("")
correct_index = PASSWORD_ALPHABET.index("h")
wrong_index = PASSWORD_ALPHABET.index("a")
            """),
            md("""
## 맞는 후보와 틀린 후보 비교

왼쪽 그래프에서는 기준 파형, `a`, `h`를 겹쳐 봅니다. 오른쪽 그래프는 각 후보에서 기준 파형을 뺀 결과입니다. `h`를 넣었을 때만 다음 문자 비교로 넘어가므로 차이 파형에 추가 활동이 남습니다.
            """),
            code("""
fig, axes = plt.subplots(1, 2, figsize=(14, 4))
axes[0].plot(reference, label="Invalid reference", color="black", alpha=.8)
axes[0].plot(candidates[wrong_index], label="Candidate a", alpha=.8)
axes[0].plot(candidates[correct_index], label="Candidate h", linewidth=2)
axes[0].set(title="First-character traces", xlabel="Sample", ylabel="Relative power")
axes[0].legend()
axes[1].plot(candidates[correct_index] - reference, label="h - reference", linewidth=2)
axes[1].plot(candidates[wrong_index] - reference, label="a - reference", alpha=.8)
axes[1].set(title="Difference traces", xlabel="Sample")
axes[1].legend()
plt.show()
            """),
            md("""
## 차이를 점수로 계산하기

기준 파형과 후보 파형의 절댓값 차이 합(SAD)을 계산합니다. 양수와 음수가 서로 지워지지 않도록 차이의 절댓값을 먼저 구합니다.
            """),
            code("""
scores = np.sum(np.abs(candidates - reference), axis=1)
plt.figure(figsize=(13, 4))
bars = plt.bar(list(PASSWORD_ALPHABET), scores, color="#4c78a8")
bars[int(np.argmax(scores))].set_color("#e45756")
plt.ylabel("Σ |candidate - reference|")
plt.title(f"Largest difference: '{PASSWORD_ALPHABET[int(np.argmax(scores))]}'")
plt.show()
            """),
            md("""
## 전체 비밀번호 복구

지금까지 찾은 접두사 뒤에 36개 후보를 차례로 붙입니다. 기준 파형과 가장 큰 차이를 만든 문자를 고르는 과정을 다섯 번 반복합니다.
            """),
            code("""
prefix = ""
score_rows = []
for position in range(5):
    candidates, reference = password_candidate_batch(prefix)
    scores = np.sum(np.abs(candidates - reference), axis=1)
    score_rows.append(scores)
    prefix += PASSWORD_ALPHABET[int(np.argmax(scores))]
    print(f"{position + 1}번째 글자 → {prefix}")

score_rows = np.stack(score_rows)
assert prefix == "h0px3"
            """),
            md("""
## 위치별 후보 점수

앞 셀에서 저장한 다섯 단계의 점수를 heatmap으로 표시합니다. 각 행에서 가장 밝은 칸을 왼쪽부터 읽으면 `h`, `0`, `p`, `x`, `3`이 됩니다. 한 글자를 잘못 고르면 다음 단계의 접두사도 틀어지므로 매 행에서 하나의 후보가 충분히 분리되는지 확인합니다.
            """),
            code("""
fig, ax = plt.subplots(figsize=(14, 4))
image = ax.imshow(score_rows, aspect="auto", cmap="magma")
ax.set_xticks(range(len(PASSWORD_ALPHABET)), list(PASSWORD_ALPHABET))
ax.set_yticks(range(5), ["Position 1", "Position 2", "Position 3", "Position 4", "Position 5"])
ax.set(title="Candidate score by position", xlabel="Candidate character")
fig.colorbar(image, ax=ax, label="SAD score")
plt.show()
            """),
        ],
    )

    save(
        "02_TVLA_누설_검정.ipynb",
        "TVLA fixed-vs-random 누설 검정",
        [
            md("""
# 02. TVLA로 누설 위치 찾기

TVLA(Test Vector Leakage Assessment)는 두 입력군의 전력 분포가 같은지 확인하는 검사입니다. 여기서는 AES 키를 고정하고 평문이 항상 같은 그룹과 매번 바뀌는 그룹을 비교합니다. t-value가 큰 시간 구간에는 입력 데이터와 관련된 전력 차이가 있습니다. 이 검사는 누설 위치를 찾지만 키를 복구하지는 않습니다.
            """),
            md("""
## fixed-vs-random 데이터 준비

고정 평문 300개와 무작위 평문 300개를 만들고 측정 순서를 섞습니다. `groups=0`은 고정 평문, `groups=1`은 무작위 평문입니다. 두 그룹의 개수가 같아야 평균과 분산을 공정하게 비교하기 쉽습니다.
            """),
            code("""
import matplotlib.pyplot as plt
import numpy as np

from cw_sca_tutorial.analysis import welch_t_test
from cw_sca_tutorial.synthetic import make_tvla_dataset

dataset, groups = make_tvla_dataset(traces_per_group=300)
traces = dataset.traces
fixed = traces[groups == 0]
random = traces[groups == 1]
print(f"fixed={len(fixed)}, random={len(random)}, samples={traces.shape[1]}")
            """),
            md("""
## 두 그룹의 평균 파형

왼쪽에는 고정 평문군과 무작위 평문군의 평균을 겹쳐 그립니다. 두 선은 대부분 비슷해 보이지만 바이트가 처리되는 위치에서 작은 차이가 생깁니다. 오른쪽 heatmap에서는 고정 평문군이 위쪽, 무작위 평문군이 아래쪽에 놓입니다.
            """),
            code("""
fig, axes = plt.subplots(1, 2, figsize=(15, 4))
axes[0].plot(fixed.mean(axis=0), label="Fixed plaintext")
axes[0].plot(random.mean(axis=0), label="Random plaintext", alpha=.85)
axes[0].set(title="Group mean traces", xlabel="Sample", ylabel="Relative power")
axes[0].legend()
ordered = np.concatenate([fixed[:40], random[:40]])
image = axes[1].imshow(ordered, aspect="auto", cmap="RdBu_r")
axes[1].axhline(39.5, color="black", linewidth=1)
axes[1].set(title="Fixed and random trace heatmap", xlabel="Sample", ylabel="Trace")
fig.colorbar(image, ax=axes[1], label="Relative power")
plt.show()
            """),
            md(r"""
## Welch t-test 계산

각 시간 샘플에서 두 그룹의 평균 차이를 표준오차로 나눕니다.

$$t = \frac{\bar{x}_{fixed}-\bar{x}_{random}}{\sqrt{s^2_{fixed}/n_{fixed}+s^2_{random}/n_{random}}}$$

그래프에는 수업에서 자주 쓰는 기준선 `±4.5`를 함께 표시합니다. 첫 50개 샘플은 누설을 넣지 않은 구간이므로 기준선을 넘지 않아야 합니다.
            """),
            code("""
t_values = welch_t_test(traces, groups)
threshold = 4.5
peak = int(np.argmax(np.abs(t_values)))
print(f"maximum |t|={abs(t_values[peak]):.2f} at sample {peak}")
print(f"wrong-window maximum |t|={np.max(np.abs(t_values[:50])):.2f}")
assert np.max(np.abs(t_values)) > threshold
assert np.max(np.abs(t_values[:50])) < threshold

fig, ax = plt.subplots(figsize=(14, 4))
ax.plot(t_values, linewidth=1)
ax.axhline(threshold, color="#e45756", linestyle="--", label="+4.5 threshold")
ax.axhline(-threshold, color="#e45756", linestyle="--", label="-4.5 threshold")
for position in dataset.leakage_positions:
    ax.axvline(position, color="black", alpha=.12)
ax.set(title="Fixed-vs-random Welch t-test", xlabel="Sample", ylabel="t-value")
ax.legend()
plt.show()
            """),
            md("""
## 파형 수에 따른 t-value

각 그룹에서 사용하는 파형 수를 늘리며 최대 `|t|`를 다시 계산합니다. 누설이 반복해서 나타나면 파형이 많아질수록 평균 차이의 통계적 신호가 커집니다.
            """),
            code("""
counts = [25, 50, 100, 200, 300]
max_t = []
for count in counts:
    subset = np.concatenate([np.flatnonzero(groups == 0)[:count], np.flatnonzero(groups == 1)[:count]])
    max_t.append(np.max(np.abs(welch_t_test(traces[subset], groups[subset]))))

plt.figure(figsize=(8, 4))
plt.plot(counts, max_t, "o-")
plt.axhline(4.5, color="#e45756", linestyle="--")
plt.xlabel("Traces per group")
plt.ylabel("Maximum |t|")
plt.title("TVLA convergence")
plt.show()
            """),
        ],
    )

    save(
        "03_DPA_AES_한바이트.ipynb",
        "DPA로 AES 한 바이트 복구",
        [
            md("""
# 03. DPA로 AES 한 바이트 복구하기

AES 첫 라운드의 중간값을 `SBox[평문[0] XOR 키 후보]`로 가정합니다. 각 키 후보에 대해 중간값의 한 비트가 0인 파형과 1인 파형을 나눈 뒤 두 그룹의 평균 차이를 계산합니다.

정답 후보로 분류했을 때만 실제 누설 시점에 큰 차이가 남습니다. 이번 데이터는 해밍 무게 누설을 넣어 만든 합성 파형입니다.
            """),
            md("""
## AES 파형 만들기

서로 다른 평문 700개를 고정 키로 처리한 합성 파형을 만듭니다. `plaintexts`는 공격자가 알고 있는 입력이고 `traces`는 측정 파형입니다. `key`는 마지막에 복구 결과를 확인할 때만 사용합니다.
            """),
            code("""
import matplotlib.pyplot as plt
import numpy as np

from cw_sca_tutorial.analysis import dpa_differences
from cw_sca_tutorial.synthetic import make_aes_dataset

dataset = make_aes_dataset(trace_count=700)
traces, plaintexts, key = dataset.traces, dataset.plaintexts, dataset.key
print(f"합성 파형: {traces.shape}, 실제 키 첫 바이트: 0x{key[0]:02x}")
            """),
            md("""
## 파형과 누설 위치 확인

왼쪽에는 개별 파형 8개를, 오른쪽에는 700개 파형의 평균을 그립니다. 빨간 점은 합성 데이터에 넣어 둔 바이트별 누설 위치입니다. 개별 파형에서는 잡음이 커 보이지만 평균에서는 반복되는 처리 구간이 드러납니다.
            """),
            code("""
fig, axes = plt.subplots(1, 2, figsize=(14, 4))
axes[0].plot(traces[:8].T, alpha=.35)
axes[0].set(title="Eight AES traces", xlabel="Sample", ylabel="Relative power")
axes[1].plot(traces.mean(axis=0), color="black")
axes[1].scatter(dataset.leakage_positions, traces.mean(axis=0)[dataset.leakage_positions], color="#e45756", s=18, label="Synthetic byte POIs")
axes[1].set(title="Mean trace and leakage points", xlabel="Sample")
axes[1].legend()
plt.show()
            """),
            md("""
## 키 후보로 두 그룹 만들기

첫 번째 키 바이트의 후보 256개를 모두 시험합니다. 각 후보가 예측한 SBox 출력의 최하위 비트로 파형을 두 그룹으로 나누고 평균 차이를 계산합니다. `scores`에는 후보별 차이 파형의 가장 큰 절댓값이 들어갑니다.
            """),
            code("""
differences = dpa_differences(traces, plaintexts, byte_index=0, bit=0)
scores = np.max(np.abs(differences), axis=1)
best = int(np.argmax(scores))
print(f"DPA 최상위 후보: 0x{best:02x} / 정답: 0x{key[0]:02x}")
assert best == int(key[0])
            """),
            md("""
## 256개 후보 비교

왼쪽 heatmap의 한 행이 한 키 후보입니다. 정답 행에서는 실제 누설 위치에 밝은 점이 생깁니다. 오른쪽에서는 정답 후보와 가장 강한 오답의 차이 파형을 겹쳐 피크 위치와 크기를 비교합니다.
            """),
            code("""
wrong = int(np.argsort(scores)[-2])
fig, axes = plt.subplots(1, 2, figsize=(15, 4))
image = axes[0].imshow(np.abs(differences), aspect="auto", cmap="viridis")
axes[0].axhline(best, color="white", linewidth=1)
axes[0].set(title="DPA difference by key guess", xlabel="Sample", ylabel="Key guess")
fig.colorbar(image, ax=axes[0], label="|Mean difference|")
axes[1].plot(differences[best], label=f"Correct 0x{best:02x}", linewidth=2)
axes[1].plot(differences[wrong], label=f"Best wrong 0x{wrong:02x}", alpha=.8)
axes[1].axvline(dataset.leakage_positions[0], color="black", linestyle="--", label="Byte 0 POI")
axes[1].set(title="Correct and wrong DPA traces", xlabel="Sample")
axes[1].legend()
plt.show()
            """),
            md("""
## 잘못된 시간 창과 비교하기

첫 50개 샘플에는 데이터 의존 누설을 넣지 않았습니다. 전체 구간의 정답 피크와 이 구간의 점수를 비교해 우연히 큰 값이 나온 경우를 구분합니다.
            """),
            code("""
full_score = scores[int(key[0])]
wrong_window_score = np.max(np.abs(differences[int(key[0]), :50]))
print(f"정답 후보 전체 구간 점수: {full_score:.3f}")
print(f"정답 후보 잘못된 창 점수: {wrong_window_score:.3f}")
assert full_score > wrong_window_score
            """),
            md("""
## 정리

DPA는 키 후보가 예측한 한 비트로 파형을 나눕니다. 정답 후보라면 실제 누설 시점에서 두 그룹의 평균이 분리됩니다.
            """),
        ],
    )

    save(
        "04_CPA_AES_전체키.ipynb",
        "CPA로 AES 전체 키 복구",
        [
            md("""
# 04. CPA로 AES-128 키 복구하기

CPA는 `HW(SBox[평문 XOR 키 후보])`와 각 시간 샘플의 Pearson 상관계수를 계산합니다. DPA와 달리 0부터 8까지의 해밍 무게 정보를 모두 사용합니다. 여기서는 합성 파형으로 계산을 익히고, 실제 측정 결과는 05 노트북에서 확인합니다.
            """),
            md("""
## 첫 바이트 CPA

합성 AES 파형 420개를 만든 뒤 첫 번째 키 바이트의 후보 256개를 시험합니다. 각 후보가 만든 해밍 무게 벡터와 파형의 모든 시간 샘플 사이에서 상관계수를 구합니다. 후보별 최대 절댓값이 첫 바이트 점수입니다.
            """),
            code("""
import matplotlib.pyplot as plt
import numpy as np

from cw_sca_tutorial.analysis import cpa_correlations, recover_key_cpa, welch_t_test
from cw_sca_tutorial.synthetic import make_aes_dataset

dataset = make_aes_dataset(trace_count=420)
traces, plaintexts, key = dataset.traces, dataset.plaintexts, dataset.key
correlations = cpa_correlations(traces, plaintexts, byte_index=0)
scores = np.max(np.abs(correlations), axis=1)
best = int(np.argmax(scores))
print(f"첫 바이트: 후보 0x{best:02x}, 정답 0x{key[0]:02x}")
            """),
            md("""
## 상관계수 heatmap

왼쪽 heatmap은 256개 후보의 상관계수를 시간축 전체에 표시합니다. 정답 후보는 첫 바이트가 처리되는 샘플에서 뚜렷한 피크를 만듭니다. 오른쪽 그래프에서는 정답과 가장 강한 오답의 상관 파형을 직접 비교합니다.
            """),
            code("""
wrong = int(np.argsort(scores)[-2])
fig, axes = plt.subplots(1, 2, figsize=(15, 4))
image = axes[0].imshow(np.abs(correlations), aspect="auto", cmap="magma", vmin=0)
axes[0].axhline(best, color="cyan", linewidth=1)
axes[0].set(title="CPA correlation by key guess", xlabel="Sample", ylabel="Key guess")
fig.colorbar(image, ax=axes[0], label="|ρ|")
axes[1].plot(np.abs(correlations[best]), label=f"Correct 0x{best:02x}", linewidth=2)
axes[1].plot(np.abs(correlations[wrong]), label=f"Best wrong 0x{wrong:02x}", alpha=.8)
axes[1].axvline(dataset.leakage_positions[0], color="black", linestyle="--")
axes[1].set(title="Correct and wrong CPA traces", xlabel="Sample", ylabel="|ρ|")
axes[1].legend()
plt.show()
            """),
            md("""
## 파형 수에 따른 변화

사용하는 파형 수를 늘리면서 정답 후보와 가장 강한 오답의 최대 상관계수를 다시 계산합니다. 파형이 늘어날수록 두 점수가 어떻게 벌어지는지 확인합니다.
            """),
            code("""
counts = [30, 60, 120, 240, 420]
true_scores, wrong_scores, ranks = [], [], []
for count in counts:
    corr = cpa_correlations(traces[:count], plaintexts[:count], byte_index=0)
    candidate_scores = np.max(np.abs(corr), axis=1)
    true_scores.append(candidate_scores[int(key[0])])
    wrong_scores.append(np.max(np.delete(candidate_scores, int(key[0]))))
    ranks.append(1 + int(np.sum(candidate_scores > candidate_scores[int(key[0])])))

fig, ax = plt.subplots(figsize=(9, 4))
ax.plot(counts, true_scores, "o-", label="Correct guess")
ax.plot(counts, wrong_scores, "o-", label="Best wrong guess")
for x, y, rank in zip(counts, true_scores, ranks):
    ax.annotate(f"rank {rank}", (x, y), xytext=(0, 7), textcoords="offset points", ha="center")
ax.set(xlabel="Number of traces", ylabel="Maximum |ρ|", title="CPA convergence for byte 0")
ax.legend()
plt.show()
            """),
            md("""
## 16바이트 키 복구

AES 첫 라운드에서는 각 바이트마다 `SBox[평문[i] XOR 키[i]]`를 계산합니다. 같은 CPA를 16번 적용해 전체 키를 구합니다.
            """),
            code("""
recovered, byte_scores, peak_samples = recover_key_cpa(traces, plaintexts)
print("정답 키:  ", bytes(key).hex())
print("복구한 키:", bytes(recovered).hex())
print("피크 샘플:", peak_samples.tolist())
assert np.array_equal(recovered, key)

fig, ax = plt.subplots(figsize=(12, 4))
bars = ax.bar(range(16), byte_scores, color="#4c78a8")
ax.set_xticks(range(16), [f"{value:02x}" for value in recovered])
ax.set(xlabel="Recovered key byte", ylabel="Maximum |ρ|", title="Full AES-128 key recovery")
for bar, sample in zip(bars, peak_samples):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height(), str(sample), ha="center", va="bottom", fontsize=8)
plt.show()
            """),
        ],
    )

    save(
        "05_CWLITE_F303_실측.ipynb",
        "CW-Lite와 F303 실측",
        [
            md("""
# 05. CW-Lite + STM32F303 실측

이 노트북은 `runs/`의 실제 측정 결과를 읽습니다. `RUN_HARDWARE=True`로 바꾸면 번들 HEX를 다시 프로그래밍하고 새 run을 만듭니다. 프로그래밍 과정에서 대상 플래시는 지워집니다.

측정 범위는 `CWLITEARM` 경로의 STM32F303에서 실행한 조기 종료 비교와 TinyAES입니다. 비밀번호 복구 검증을 통과한 F303 run만 선택합니다. 이전 F415 결과는 별도 run에 보존했습니다.
            """),
            md("""
## 측정 신호 확인

25 dB에서 비밀번호 preflight 파형 폭이 50 ADC count보다 작으면 캡처를 중단합니다. 정상 연결에서 확인한 폭은 약 608 count였습니다. 한 자릿수 count만 나온다면 분석을 반복하지 말고 target의 `MEASURE` SMA와 shunt 경로를 먼저 확인하십시오. 35 dB 이상에서는 이 장치의 ADC가 clipping됐습니다.
            """),
            md("""
## 사용할 run 선택

`RUN_HARDWARE=False`이면 이미 검증한 최신 run을 불러옵니다. 수업 전에 새로 측정하려면 값을 `True`로 바꾸십시오. 새 측정은 비밀번호 펌웨어와 AES 펌웨어를 차례로 프로그래밍하므로 target 플래시의 기존 내용은 지워집니다.
            """),
            code("""
from pathlib import Path
import json

import matplotlib.pyplot as plt
import numpy as np

from cw_sca_tutorial.analysis import cpa_correlations, recover_key_cpa, welch_t_test
from cw_sca_tutorial.hardware import capture_aes_run, capture_password_run, latest_complete_run

RUN_HARDWARE = False
RUNS = Path("../runs") if Path.cwd().name == "notebooks" else Path("runs")
FIRMWARE = Path("../firmware/prebuilt") if Path.cwd().name == "notebooks" else Path("firmware/prebuilt")

if RUN_HARDWARE:
    password_run = capture_password_run(FIRMWARE / "basic-passwdcheck-CWLITEARM.hex", runs_root=RUNS, platform_name="CWLITEARM", target_identification="STM32F303")
    tvla_run = capture_aes_run(FIRMWARE / "simpleserial-aes-CWLITEARM.hex", trace_count=1000, runs_root=RUNS, platform_name="CWLITEARM", target_identification="STM32F303", capture_mode="fixed_vs_random")
    aes_run = capture_aes_run(FIRMWARE / "simpleserial-aes-CWLITEARM.hex", trace_count=500, runs_root=RUNS, platform_name="CWLITEARM", target_identification="STM32F303")
else:
    password_run = latest_complete_run(RUNS, "measured_password_spa")
    tvla_run = latest_complete_run(RUNS, "measured_aes_tvla")
    aes_run = latest_complete_run(RUNS, "measured_aes_cpa")

print("password run:", password_run)
print("TVLA run:    ", tvla_run)
print("AES run:     ", aes_run)
            """),
            md("""
## 실측 비밀번호 SPA

metadata의 상태가 `complete`이고 복구 검증을 통과한 run만 사용합니다. 각 후보를 한 번씩 측정하고 전체 3,000샘플의 SAD를 계산합니다. upstream Lab 2_1B와 같은 방식입니다.
            """),
            code("""
password_meta = json.loads((password_run / "metadata.json").read_text())
password_data = np.load(password_run / "traces.npz")
assert password_meta["state"] == "complete"
print("복구된 비밀번호:", password_meta["recovered_password"])
print("수락된 파형:", password_meta["accepted_trace_count"])
print("firmware SHA-256:", password_meta["firmware"]["sha256"])
            """),
            md("""
## 비밀번호 파형과 후보 점수

왼쪽 heatmap에는 실제 비밀번호 파형을 캡처 순서대로 표시합니다. 오른쪽 heatmap은 위치별 SAD 점수입니다. 각 행에서 가장 밝은 후보가 선택되며, 정상 run에서는 `h0px3` 순서가 선명하게 나타납니다.
            """),
            code("""
decisions = password_meta["decisions"]
score_matrix = np.array([[decision["scores"][c] for c in "abcdefghijklmnopqrstuvwxyz0123456789"] for decision in decisions])
fig, axes = plt.subplots(1, 2, figsize=(16, 4))
axes[0].imshow(password_data["traces"][:80], aspect="auto", cmap="RdBu_r")
axes[0].set(title="Measured password traces", xlabel="Sample", ylabel="Capture")
image = axes[1].imshow(score_matrix, aspect="auto", cmap="magma")
axes[1].set_xticks(range(36), list("abcdefghijklmnopqrstuvwxyz0123456789"))
axes[1].set_yticks(range(5), ["Position 1", "Position 2", "Position 3", "Position 4", "Position 5"])
axes[1].set(title="Measured password SAD", xlabel="Candidate")
fig.colorbar(image, ax=axes[1], label="SAD")
plt.show()
            """),
            md("""
## 실측 fixed-vs-random TVLA

고정 평문 500개와 무작위 평문 500개를 섞어서 측정한 run을 사용합니다. 먼저 두 그룹의 평균 파형을 비교하고, 이어서 샘플별 Welch t-value를 계산합니다. 빨간 점선 `±4.5`를 넘는 구간이 실제 데이터 의존 차이가 검출된 위치입니다.
            """),
            code("""
tvla_meta = json.loads((tvla_run / "metadata.json").read_text())
tvla_data = np.load(tvla_run / "traces.npz")
assert tvla_meta["state"] == "complete"
tvla_traces = tvla_data["traces"]
tvla_groups = tvla_data["groups"]
fixed = tvla_traces[tvla_groups == 0]
random = tvla_traces[tvla_groups == 1]
t_values = welch_t_test(tvla_traces, tvla_groups)
peak = int(np.argmax(np.abs(t_values)))
print(f"fixed={len(fixed)}, random={len(random)}")
print(f"maximum |t|={abs(t_values[peak]):.2f} at sample {peak}")
print(f"wrong-window maximum |t|={np.max(np.abs(t_values[:50])):.2f}")
assert np.max(np.abs(t_values)) > 4.5
assert np.max(np.abs(t_values[:50])) < 4.5
            """),
            code("""
fig, axes = plt.subplots(1, 2, figsize=(15, 4))
axes[0].plot(fixed.mean(axis=0), label="Fixed plaintext")
axes[0].plot(random.mean(axis=0), label="Random plaintext", alpha=.85)
axes[0].set(title="Measured group mean traces", xlabel="Sample", ylabel="Relative power")
axes[0].legend()
axes[1].plot(t_values, linewidth=1)
axes[1].axhline(4.5, color="#e45756", linestyle="--", label="+4.5 threshold")
axes[1].axhline(-4.5, color="#e45756", linestyle="--", label="-4.5 threshold")
axes[1].set(title="Measured fixed-vs-random TVLA", xlabel="Sample", ylabel="t-value")
axes[1].legend()
plt.show()
            """),
            md("""
## 실측 TinyAES와 CPA

캡처를 시작하기 전에 FIPS-197 Appendix B Cipher Example의 알려진 벡터로 암호문을 확인합니다. 이어서 원시 파형의 평균과 표준편차를 살펴보고 CPA로 키를 복구합니다.
            """),
            code("""
aes_meta = json.loads((aes_run / "metadata.json").read_text())
aes_data = np.load(aes_run / "traces.npz")
assert aes_meta["state"] == "complete"
traces = aes_data["traces"]
plaintexts = aes_data["plaintexts"]
known_key = aes_data["key"]
print("preflight:", aes_meta["preflight"])
print("raw shape:", traces.shape)
print("firmware SHA-256:", aes_meta["firmware"]["sha256"])
            """),
            md("""
## 실측 AES 파형 확인

왼쪽에는 서로 다른 평문으로 얻은 파형 10개를 겹쳐 그립니다. 오른쪽에는 500개 파형의 평균과 표준편차를 표시합니다. 같은 펌웨어를 실행해도 데이터가 바뀌면 특정 구간의 전력값이 조금씩 달라집니다.
            """),
            code("""
fig, axes = plt.subplots(1, 2, figsize=(15, 4))
axes[0].plot(traces[:10].T, alpha=.35)
axes[0].set(title="Ten measured AES traces", xlabel="Sample", ylabel="Relative power")
axes[1].plot(traces.mean(axis=0), label="Mean")
axes[1].fill_between(np.arange(traces.shape[1]), traces.mean(axis=0)-traces.std(axis=0), traces.mean(axis=0)+traces.std(axis=0), alpha=.25, label="±1 standard deviation")
axes[1].set(title="Mean and trace variation", xlabel="Sample")
axes[1].legend()
plt.show()
            """),
            md("""
## 첫 바이트 CPA

실측 평문과 파형으로 첫 번째 키 바이트의 상관계수를 계산합니다. heatmap에서 가장 밝은 행을 찾고, 정답 후보와 가장 강한 오답의 상관 파형을 비교합니다. 비교용으로 정한 0:50 창의 점수도 함께 출력합니다.
            """),
            code("""
first_corr = cpa_correlations(traces, plaintexts, byte_index=0)
first_scores = np.max(np.abs(first_corr), axis=1)
best = int(np.argmax(first_scores))
wrong_window = slice(0, 50)
print(f"첫 바이트 후보: 0x{best:02x}, 알려진 키: 0x{known_key[0]:02x}")
print(f"정답 전체 창 최대 |ρ|: {np.max(np.abs(first_corr[int(known_key[0])])):.4f}")
print(f"정답 잘못된 창 최대 |ρ|: {np.max(np.abs(first_corr[int(known_key[0]), wrong_window])):.4f}")

fig, axes = plt.subplots(1, 2, figsize=(15, 4))
axes[0].imshow(np.abs(first_corr), aspect="auto", cmap="magma")
axes[0].axhline(best, color="cyan", linewidth=1)
axes[0].set(title="Measured CPA heatmap for byte 0", xlabel="Sample", ylabel="Key guess")
axes[1].plot(np.abs(first_corr[best]), label=f"Best guess 0x{best:02x}")
axes[1].plot(np.abs(first_corr[int(np.argsort(first_scores)[-2])]), label="Best wrong guess", alpha=.8)
axes[1].set(title="Correct and wrong CPA traces", xlabel="Sample", ylabel="|ρ|")
axes[1].legend()
plt.show()
            """),
            md("""
## 전체 키 복구

첫 바이트에서 사용한 CPA를 나머지 15바이트에도 적용합니다. 복구한 키를 알려진 고정 키와 비교하고, 각 바이트에서 가장 높은 상관이 나온 샘플 위치도 출력합니다.
            """),
            code("""
recovered, scores, peaks = recover_key_cpa(traces, plaintexts)
print("알려진 키:", bytes(known_key).hex())
print("복구한 키:", bytes(recovered).hex())
print("피크 샘플:", peaks.tolist())
assert np.array_equal(recovered, known_key)
            """),
            md("""
## 결론

비밀번호 run은 번들 조기 종료 비교 코드에서 `h0px3`를 복구했습니다. fixed-vs-random TVLA에서는 AES 처리 구간의 t-value가 기준선을 넘었습니다. CPA run은 번들 TinyAES 첫 라운드에서 고정 AES-128 키를 복구했습니다.
            """),
        ],
    )

    print(f"generated tutorial notebooks in {OUT}")


if __name__ == "__main__":
    main()
