#!/usr/bin/env python3
"""실측 데이터를 사용하는 강의용 메인 노트북 네 개를 생성한다."""

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
            "tutorial": {"title": title, "evidence": "measured"},
        },
    )
    nbf.write(notebook, OUT / filename)


def main() -> None:
    OUT.mkdir(exist_ok=True)

    save(
        "00_사전점검.ipynb",
        "사전점검",
        [
            md("""
# 00. 사전점검

시연 전에 CW-Lite, target, 펌웨어, 측정 신호를 확인합니다. 이 노트북은 invalid, `h`, `h0px3` 세 입력을 25 dB에서 짧게 측정합니다. 정상 파형이 확인되면 01번부터 차례로 진행합니다.
            """),
            md("""
## 장치와 펌웨어 확인

CW-Lite가 정확히 한 대 연결되어 있어야 합니다. prebuilt 비밀번호 펌웨어의 SHA-256도 함께 출력해 시연에 사용할 입력을 확인합니다.
            """),
            code("""
import hashlib
import json

import chipwhisperer as cw

from cw_sca_tutorial.demo import repository_root
from cw_sca_tutorial.hardware import diagnose_password_signal

ROOT = repository_root()
devices = cw.list_devices()
assert len(devices) == 1, f"Expected one ChipWhisperer, found: {devices}"

firmware = ROOT / "firmware/prebuilt/basic-passwdcheck-CWLITEARM.hex"
firmware_sha256 = hashlib.sha256(firmware.read_bytes()).hexdigest()
print("Device   :", devices[0])
print("Firmware :", firmware.name)
print("SHA-256  :", firmware_sha256)
            """),
            md("""
## 세 입력으로 신호 확인

target 플래시를 지우고 번들 비밀번호 펌웨어를 기록합니다. invalid와 `h`는 `PASSWORD FAIL`, `h0px3`는 `Access granted`를 반환해야 합니다. 25 dB 파형 폭이 50 ADC count보다 작거나 clipping이 있으면 다음 노트북으로 넘어가지 않습니다.
            """),
            code("""
run = diagnose_password_signal(
    firmware,
    gains_db=(25.0,),
    repeats=1,
    runs_root=ROOT / "runs",
    serial_number=devices[0]["sn"],
    platform_name="CWLITEARM",
    target_identification="STM32F303",
)

metadata = json.loads((run / "metadata.json").read_text())
summary = metadata["gain_summaries"][0]
print("Run          :", run.name)
print("UART         :", metadata["uart_validation"])
print("Peak-to-peak :", summary["median_peak_to_peak"])
print("ADC range    :", summary["minimum"], summary["maximum"])

assert metadata["state"] == "complete"
assert metadata["uart_validation"] == "passed"
assert metadata["accepted_trace_count"] == 3
assert summary["median_peak_to_peak"] >= 50
assert summary["minimum"] > 0 and summary["maximum"] < 1023
print("Pre-class checks passed.")
            """),
            md("""
## 점검이 실패하면

CW-Lite USB, 20-pin cable, target 전원, `MEASURE` SMA와 shunt 경로를 차례로 확인합니다. 이 장치의 정상 파형 폭은 약 600 ADC count였습니다. 35 dB 이상으로 gain을 올려 통과시키지 마십시오. 이전 측정에서는 ADC clipping이 발생했습니다.
            """),
        ],
    )

    save(
        "01_전력으로_비밀번호_깨기.ipynb",
        "전력으로 비밀번호 깨기",
        [
            md("""
# 01. 전력으로 비밀번호 깨기

같은 펌웨어에 입력 한 글자만 다르게 넣었습니다. 그런데 실제 전력 파형은 달라집니다. 그 차이만 사용해 교육용 금고의 비밀번호 `h0px3`를 복구해 보겠습니다.

이 노트북을 실행할 때 STM32F303과 ChipWhisperer-Lite에서 후보 185개를 직접 측정합니다. 시작 셀은 target 플래시를 지우고 번들 비밀번호 펌웨어를 기록합니다. 이전 측정에서 약 37초가 걸렸습니다.
            """),
            code("""
import chipwhisperer as cw
import json
import matplotlib.pyplot as plt
import numpy as np

from cw_sca_tutorial.demo import repository_root
from cw_sca_tutorial.hardware import capture_password_run

ROOT = repository_root()
devices = cw.list_devices()
assert len(devices) == 1, f"Expected one ChipWhisperer, found: {devices}"
run = capture_password_run(
    ROOT / "firmware/prebuilt/basic-passwdcheck-CWLITEARM.hex",
    repeats=1,
    gain_db=25.0,
    runs_root=ROOT / "runs",
    serial_number=devices[0]["sn"],
    platform_name="CWLITEARM",
    target_identification="STM32F303",
)
metadata = json.loads((run / "metadata.json").read_text())
data = np.load(run / "traces.npz")

traces = data["traces"]
guesses = data["guesses"]
positions = data["positions"]
kinds = data["kinds"]

print("DATA SOURCE : MEASURED")
print("RUN         :", run.name)
print("TARGET      :", metadata["target_identity"]["user_identification"])
print("SCOPE       :", metadata["measurement_setup"]["device"]["name"])
print("TRACES      :", traces.shape)
            """),
            md("""
## 입력 한 글자가 만든 차이

`a`는 첫 비교에서 바로 틀립니다. `h`는 첫 글자가 맞아서 다음 글자까지 비교합니다. 왼쪽에서는 전체 파형을 겹쳐 보고, 오른쪽에서는 차이가 가장 큰 구간을 확대합니다.
            """),
            code("""
first_position = positions == 0
reference = traces[first_position & (kinds == "reference")][0]
trace_a = traces[first_position & (kinds == "candidate") & (guesses == "a")][0]
trace_h = traces[first_position & (kinds == "candidate") & (guesses == "h")][0]

difference = np.abs(trace_h - reference)
window = 120
rolling = np.convolve(difference, np.ones(window), mode="valid")
start = int(np.argmax(rolling))
zoom = slice(max(0, start - 80), min(len(reference), start + window + 80))

fig, axes = plt.subplots(1, 2, figsize=(15, 4))
axes[0].plot(reference, label="Invalid reference", alpha=.8)
axes[0].plot(trace_a, label="Candidate a", alpha=.8)
axes[0].plot(trace_h, label="Candidate h", linewidth=1.5)
axes[0].set(title="Measured password traces", xlabel="Sample", ylabel="ADC count")
axes[0].legend()
axes[1].plot(np.arange(len(reference))[zoom], trace_h[zoom] - reference[zoom], label="h - reference")
axes[1].plot(np.arange(len(reference))[zoom], trace_a[zoom] - reference[zoom], label="a - reference", alpha=.8)
axes[1].axhline(0, color="black", linewidth=.7)
axes[1].set(title="Largest difference window", xlabel="Sample", ylabel="ADC difference")
axes[1].legend()
plt.show()
            """),
            md("""
## 왜 다음 비교로 넘어갈까요?

펌웨어는 앞에서부터 문자를 비교하고 첫 불일치에서 멈춥니다.

```c
for (i = 0; i < sizeof(correct_passwd); i++) {
    if (correct_passwd[i] != passwd[i]) {
        break;
    }
}
```

맞는 접두사가 길수록 비교 루프를 더 오래 실행합니다. 이 실행 경로 차이가 전력 파형에 남습니다.
            """),
            md("""
## 36개 후보 중 첫 글자 찾기

항상 틀리는 기준 파형과 각 후보 파형의 절댓값 차이 합(SAD)을 계산합니다. 점수가 가장 큰 후보가 다음 비교로 넘어간 문자입니다.
            """),
            code("""
alphabet = "abcdefghijklmnopqrstuvwxyz0123456789"
first_scores = metadata["decisions"][0]["scores"]
score_values = np.array([first_scores[c] for c in alphabet])
best_index = int(np.argmax(score_values))

fig, ax = plt.subplots(figsize=(13, 4))
bars = ax.bar(list(alphabet), score_values, color="#4c78a8")
bars[best_index].set_color("#e45756")
ax.set(title=f"First character: {alphabet[best_index]}", xlabel="Candidate", ylabel="Full-trace SAD")
plt.show()

ranking = np.argsort(score_values)[::-1][:5]
for index in ranking:
    print(f"{alphabet[index]}: {score_values[index]:.0f}")
            """),
            md("""
## 비밀번호 전체 복구

찾은 문자를 접두사에 붙이고 같은 과정을 다음 위치에서 반복합니다. 아래 셀은 저장된 원시 파형에서 SAD를 다시 계산해 선택 순서를 만듭니다.
            """),
            code("""
prefixes = []
score_rows = []
prefix = ""
for position in range(5):
    mask = positions == position
    reference = traces[mask & (kinds == "reference")].mean(axis=0)
    scores = []
    for candidate in alphabet:
        guess = prefix + candidate
        candidate_traces = traces[mask & (kinds == "candidate") & (guesses == guess)]
        assert len(candidate_traces) >= 1, (position, guess)
        scores.append(np.sum(np.abs(candidate_traces.mean(axis=0) - reference)))
    scores = np.asarray(scores)
    score_rows.append(scores)
    prefix += alphabet[int(np.argmax(scores))]
    prefixes.append(prefix)
    print(prefix)

assert prefixes[-1] == "h0px3"
assert prefixes == [decision["prefix"] for decision in metadata["decisions"]]

fig, ax = plt.subplots(figsize=(14, 4))
image = ax.imshow(np.stack(score_rows), aspect="auto", cmap="magma")
ax.set_xticks(range(len(alphabet)), list(alphabet))
ax.set_yticks(range(5), ["Position 1", "Position 2", "Position 3", "Position 4", "Position 5"])
ax.set(title="Measured password candidate scores", xlabel="Candidate")
fig.colorbar(image, ax=ax, label="SAD")
plt.show()
            """),
        ],
    )

    save(
        "02_비트에서_TVLA까지.ipynb",
        "비트에서 TVLA까지",
        [
            md("""
# 02. 비트 변화가 전력으로 보이는 이유

01번에서는 파형 차이로 비밀번호를 찾았습니다. 이제 MCU 내부 값과 전력 소비를 연결하는 Hamming weight와 Hamming distance를 살펴보고, 실제 TVLA로 누설 위치를 찾겠습니다. 실측 셀은 target 플래시를 지우고 번들 TinyAES 펌웨어를 기록합니다.
            """),
            md("""
## Hamming weight

Hamming weight는 비트열에서 1의 개수입니다. 파형 배열이 `float32`인 것은 ADC 값을 소수로 저장했기 때문이며, 누설 모델의 Hamming weight와는 별개입니다.
            """),
            code("""
import matplotlib.pyplot as plt
import numpy as np

from cw_sca_tutorial.analysis import welch_t_test

value = 0x3A
bits = np.array([(value >> bit) & 1 for bit in range(7, -1, -1)])
print(f"0x{value:02X} = {value:08b}")
print("Hamming weight =", value.bit_count())

plt.figure(figsize=(8, 3))
plt.bar(range(8), bits, color=np.where(bits, "#e45756", "#d9d9d9"))
plt.xticks(range(8), [f"b{bit}" for bit in range(7, -1, -1)])
plt.ylim(0, 1.2)
plt.xlabel("Register bit")
plt.ylabel("Bit value")
plt.title("Hamming weight of 0x3A")
plt.show()
            """),
            md("""
## Hamming distance

Hamming distance는 이전 값과 새 값 사이에서 바뀐 비트 수입니다. 실제 CMOS 동적 전력은 충전·방전된 노드 수와 관련되므로 Hamming distance가 더 자연스러운 모델인 경우도 많습니다.
            """),
            code("""
old = 0x00
new = 0xFF
distance = (old ^ new).bit_count()

print(f"old : {old:08b}")
print(f"new : {new:08b}")
print(f"xor : {old ^ new:08b}")
print("Hamming distance =", distance)
            """),
            md("""
## 실제 fixed-vs-random 데이터

AES 키는 고정한 채 평문이 항상 같은 그룹 100개와 매번 달라지는 그룹 100개를 지금 측정합니다. 두 그룹은 시간 순서에 따른 드리프트가 한쪽에 몰리지 않도록 섞어서 수집합니다. 이전 측정에서는 약 10–15초가 걸릴 것으로 예상됩니다.
            """),
            code("""
import chipwhisperer as cw
import json

from cw_sca_tutorial.demo import repository_root
from cw_sca_tutorial.hardware import capture_aes_run

ROOT = repository_root()
devices = cw.list_devices()
assert len(devices) == 1, f"Expected one ChipWhisperer, found: {devices}"
run = capture_aes_run(
    ROOT / "firmware/prebuilt/simpleserial-aes-CWLITEARM.hex",
    trace_count=200,
    runs_root=ROOT / "runs",
    serial_number=devices[0]["sn"],
    platform_name="CWLITEARM",
    target_identification="STM32F303",
    capture_mode="fixed_vs_random",
)
metadata = json.loads((run / "metadata.json").read_text())
data = np.load(run / "traces.npz")
traces = data["traces"]
groups = data["groups"]
fixed = traces[groups == 0]
random = traces[groups == 1]

print("DATA SOURCE : MEASURED")
print("RUN         :", run.name)
print("TARGET      :", metadata["target_identity"]["user_identification"])
print(f"GROUPS      : fixed={len(fixed)}, random={len(random)}")
            """),
            md("""
## 평균 파형과 Welch t-test

평균 파형 두 개는 비슷해 보이지만 샘플별 Welch t-test를 계산하면 반복되는 작은 차이가 드러납니다. 빨간 점선은 수업에서 자주 사용하는 `±4.5` 기준입니다.
            """),
            code("""
t_values = welch_t_test(traces, groups)
threshold = 4.5
peak = int(np.argmax(np.abs(t_values)))

fig, axes = plt.subplots(2, 1, figsize=(14, 7), sharex=True)
axes[0].plot(fixed.mean(axis=0), label="Fixed plaintext")
axes[0].plot(random.mean(axis=0), label="Random plaintext", alpha=.85)
axes[0].set(title="Measured group mean traces", ylabel="Relative power")
axes[0].legend()
axes[1].plot(t_values, linewidth=1)
axes[1].axhline(threshold, color="#e45756", linestyle="--", label="+4.5 threshold")
axes[1].axhline(-threshold, color="#e45756", linestyle="--", label="-4.5 threshold")
axes[1].set(title="Measured fixed-vs-random TVLA", xlabel="Sample", ylabel="t-value")
axes[1].legend()
plt.show()

print(f"maximum |t| = {abs(t_values[peak]):.2f} at sample {peak}")
print(f"comparison window 0:50 maximum |t| = {np.max(np.abs(t_values[:50])):.2f}")
assert np.max(np.abs(t_values)) > threshold
            """),
            md("""
## 파형 수를 늘리면

각 그룹에서 사용하는 파형 수를 늘리며 최대 `|t|`를 다시 계산합니다. TVLA는 누설 위치를 찾는 검사이며, 이 단계에서는 아직 키 후보를 사용하지 않습니다.
            """),
            code("""
counts = [10, 25, 50, 75, 100]
max_t = []
for count in counts:
    subset = np.concatenate([
        np.flatnonzero(groups == 0)[:count],
        np.flatnonzero(groups == 1)[:count],
    ])
    max_t.append(float(np.max(np.abs(welch_t_test(traces[subset], groups[subset])))))

plt.figure(figsize=(8, 4))
plt.plot(counts, max_t, "o-")
plt.axhline(4.5, color="#e45756", linestyle="--")
plt.xlabel("Traces per group")
plt.ylabel("Maximum |t|")
plt.title("Measured TVLA convergence")
plt.show()
            """),
        ],
    )

    save(
        "03_AES_키_복구.ipynb",
        "AES 키 복구",
        [
            md("""
# 03. 실제 파형으로 AES 키 복구하기

TVLA에서는 누설 위치만 확인했습니다. 이제 알려진 평문과 키 후보로 AES 첫 라운드 중간값을 예측하고, 새로 측정한 파형 100개에서 16바이트 키를 복구합니다. 시작 셀은 target 플래시를 지우고 번들 TinyAES 펌웨어를 기록합니다. 이전 측정에서는 약 10초가 걸렸습니다.

$$Z = SBox[P \oplus K]$$

공격자는 평문 `P`를 알고 있습니다. 키 후보 `K`를 하나씩 넣으면 중간값 `Z`를 예측할 수 있습니다.
            """),
            code("""
import chipwhisperer as cw
import json
import matplotlib.pyplot as plt
import numpy as np

from cw_sca_tutorial.analysis import cpa_correlations, dpa_differences, recover_key_cpa
from cw_sca_tutorial.demo import repository_root
from cw_sca_tutorial.hardware import capture_aes_run

ROOT = repository_root()
devices = cw.list_devices()
assert len(devices) == 1, f"Expected one ChipWhisperer, found: {devices}"
run = capture_aes_run(
    ROOT / "firmware/prebuilt/simpleserial-aes-CWLITEARM.hex",
    trace_count=100,
    runs_root=ROOT / "runs",
    serial_number=devices[0]["sn"],
    platform_name="CWLITEARM",
    target_identification="STM32F303",
)
metadata = json.loads((run / "metadata.json").read_text())
data = np.load(run / "traces.npz")
traces = data["traces"]
plaintexts = data["plaintexts"]
known_key = data["key"]

print("DATA SOURCE : MEASURED")
print("RUN         :", run.name)
print("TARGET      :", metadata["target_identity"]["user_identification"])
print("TRACES      :", traces.shape)
            """),
            md("""
## 실제 AES 파형

서로 다른 평문 10개의 파형을 겹쳐 봅니다. 전체 형태는 비슷하지만 데이터가 바뀌면서 각 샘플의 전력값이 조금씩 달라집니다.
            """),
            code("""
fig, axes = plt.subplots(1, 2, figsize=(15, 4))
axes[0].plot(traces[:10].T, alpha=.35)
axes[0].set(title="Ten measured AES traces", xlabel="Sample", ylabel="Relative power")
axes[1].plot(traces.mean(axis=0), label="Mean")
axes[1].fill_between(
    np.arange(traces.shape[1]),
    traces.mean(axis=0) - traces.std(axis=0),
    traces.mean(axis=0) + traces.std(axis=0),
    alpha=.25,
    label="±1 standard deviation",
)
axes[1].set(title="Mean and trace variation", xlabel="Sample")
axes[1].legend()
plt.show()
            """),
            md("""
## DPA로 첫 바이트 찾기

키 후보마다 `SBox[P XOR guess]`의 3번 비트를 예측합니다. 예측 비트가 0인 파형과 1인 파형의 평균을 빼면, 정답 후보에서 실제 누설 시점의 차이가 가장 크게 남습니다. 그래프는 첫 라운드 피크가 모인 800:2300 샘플을 확대합니다.
            """),
            code("""
differences = dpa_differences(traces, plaintexts, byte_index=0, bit=3)
dpa_scores = np.max(np.abs(differences), axis=1)
dpa_best = int(np.argmax(dpa_scores))
dpa_wrong = int(np.argsort(dpa_scores)[-2])

print(f"DPA best guess: 0x{dpa_best:02x}")
print(f"Known key byte: 0x{known_key[0]:02x}")
assert dpa_best == int(known_key[0])

fig, axes = plt.subplots(1, 2, figsize=(15, 4))
dpa_window = slice(800, 2300)
image = axes[0].imshow(
    np.abs(differences[:, dpa_window]),
    aspect="auto",
    cmap="viridis",
    extent=[dpa_window.start, dpa_window.stop, 255, 0],
)
axes[0].axhline(dpa_best, color="white", linewidth=1)
axes[0].set(title="Measured DPA by key guess", xlabel="Sample", ylabel="Key guess")
fig.colorbar(image, ax=axes[0], label="|Mean difference|")
samples = np.arange(traces.shape[1])[dpa_window]
axes[1].plot(samples, differences[dpa_best, dpa_window], label=f"Correct 0x{dpa_best:02x}")
axes[1].plot(samples, differences[dpa_wrong, dpa_window], label=f"Best wrong 0x{dpa_wrong:02x}", alpha=.8)
axes[1].set(title="Correct and wrong DPA traces", xlabel="Sample")
axes[1].legend()
plt.show()
            """),
            md("""
## CPA는 한 비트 대신 Hamming weight 전체를 사용합니다

DPA에서는 중간값의 한 비트만 사용했습니다. CPA에서는 `HW(SBox[P XOR guess])`의 0부터 8까지 값을 모두 사용하고, 예측값과 실제 파형의 Pearson 상관계수를 계산합니다. 같은 800:2300 구간에서 정답 후보의 상관 피크를 확인합니다.
            """),
            code("""
correlations = cpa_correlations(traces, plaintexts, byte_index=0)
cpa_scores = np.max(np.abs(correlations), axis=1)
cpa_best = int(np.argmax(cpa_scores))
cpa_wrong = int(np.argsort(cpa_scores)[-2])

fig, axes = plt.subplots(1, 2, figsize=(15, 4))
cpa_window = slice(800, 2300)
image = axes[0].imshow(
    np.abs(correlations[:, cpa_window]),
    aspect="auto",
    cmap="magma",
    extent=[cpa_window.start, cpa_window.stop, 255, 0],
)
axes[0].axhline(cpa_best, color="cyan", linewidth=1)
axes[0].set(title="Measured CPA by key guess", xlabel="Sample", ylabel="Key guess")
fig.colorbar(image, ax=axes[0], label="|ρ|")
samples = np.arange(traces.shape[1])[cpa_window]
axes[1].plot(samples, np.abs(correlations[cpa_best, cpa_window]), label=f"Correct 0x{cpa_best:02x}")
axes[1].plot(samples, np.abs(correlations[cpa_wrong, cpa_window]), label=f"Best wrong 0x{cpa_wrong:02x}", alpha=.8)
axes[1].set(title="Correct and wrong CPA traces", xlabel="Sample", ylabel="|ρ|")
axes[1].legend()
plt.show()

print(f"CPA best guess: 0x{cpa_best:02x}")
print(f"Maximum correlation: {cpa_scores[cpa_best]:.4f}")
            """),
            md("""
## 파형 수와 정답 순위

25개부터 500개까지 파형 수를 늘리며 첫 바이트 정답의 순위를 계산합니다. 파형이 늘어나면 가장 강한 오답의 상관은 낮아지고 정답 후보가 안정적으로 분리됩니다.
            """),
            code("""
counts = [25, 50, 75, 100]
true_scores, wrong_scores, ranks = [], [], []
for count in counts:
    corr = cpa_correlations(traces[:count], plaintexts[:count], byte_index=0)
    scores = np.max(np.abs(corr), axis=1)
    true = int(known_key[0])
    true_scores.append(scores[true])
    wrong_scores.append(np.max(np.delete(scores, true)))
    ranks.append(1 + int(np.sum(scores > scores[true])))

fig, ax = plt.subplots(figsize=(9, 4))
ax.plot(counts, true_scores, "o-", label="Correct guess")
ax.plot(counts, wrong_scores, "o-", label="Best wrong guess")
for x, y, rank in zip(counts, true_scores, ranks):
    ax.annotate(f"rank {rank}", (x, y), xytext=(0, 7), textcoords="offset points", ha="center")
ax.set(title="Measured CPA convergence", xlabel="Number of traces", ylabel="Maximum |ρ|")
ax.legend()
plt.show()
            """),
            md("""
## AES-128 전체 키

같은 CPA를 나머지 15바이트에도 적용합니다. 아래 두 줄이 같으면 16바이트를 모두 복구한 것입니다.
            """),
            code("""
recovered, byte_scores, peak_samples = recover_key_cpa(traces, plaintexts)

print("Expected :", bytes(known_key).hex())
print("Recovered:", bytes(recovered).hex())
print(f"Matching : {int(np.sum(recovered == known_key))} / 16 bytes")
assert np.array_equal(recovered, known_key)

fig, ax = plt.subplots(figsize=(12, 4))
bars = ax.bar(range(16), byte_scores, color="#4c78a8")
ax.set_xticks(range(16), [f"{value:02x}" for value in recovered])
ax.set(title="Full measured AES-128 key recovery", xlabel="Recovered key byte", ylabel="Maximum |ρ|")
for bar, sample in zip(bars, peak_samples):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height(), str(sample), ha="center", va="bottom", fontsize=8)
plt.show()
            """),
        ],
    )

    print(f"generated measured demo notebooks in {OUT}")


if __name__ == "__main__":
    main()
