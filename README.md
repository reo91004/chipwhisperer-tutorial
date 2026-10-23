# ChipWhisperer 실측 부채널 분석 시연

STM32F303과 ChipWhisperer-Lite에서 매번 새로 측정한 전력 파형으로 비밀번호 SPA, fixed-vs-random TVLA, AES DPA·CPA를 시연하는 Jupyter 튜토리얼입니다. 메인 노트북은 합성 데이터나 이전 run으로 자동 대체하지 않습니다.

## 수업 순서

| 순서 | 노트북 | 새로 측정하는 데이터 | 예상 시간 |
|---:|---|---:|---:|
| 준비 | `00_사전점검.ipynb` | invalid, `h`, `h0px3` 3개 | 약 6초 |
| 1 | `01_전력으로_비밀번호_깨기.ipynb` | 비교 2개 + 비밀번호 공격 185개 | 약 38초 |
| 2 | `02_비트에서_TVLA까지.ipynb` | fixed 100개 + random 100개 | 약 10–15초 |
| 3 | `03_AES_키_복구.ipynb` | 무작위 평문 100개 | 약 10초 |

펌웨어 프로그래밍을 포함한 전체 캡처 시간은 약 1분입니다. 각 노트북은 자신이 만든 run을 즉시 분석합니다.

기존 합성 예제는 `notebooks/appendix/`에 남겼습니다. 장비 없이 원리를 복습하거나 과제로 사용할 때만 열면 됩니다.

## 설치

Python 3.10 이상을 사용합니다.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python scripts/make_notebooks.py
jupyter lab
```

검증 환경은 Python 3.11.3, ChipWhisperer 7.0.0, NumPy 2.4.3입니다.

## 연결과 gain

권장 target은 STM32F303이며 플랫폼 이름은 `CWLITEARM`입니다.

- CW-Lite USB와 target 전원을 확인합니다.
- 20-pin cable과 `MEASURE` SMA를 확인합니다.
- 외부 전원과 CW 전원이 충돌하지 않게 합니다.
- 기본 외부 clock은 약 7.37 MHz, ADC는 약 29.5 MHz입니다.
- 비밀번호 실습은 25 dB를 사용합니다.

정상 연결에서 비밀번호 진단 파형 폭은 약 600 ADC count였습니다. 한 자릿수 count만 나온다면 다음 노트북으로 넘어가지 말고 `MEASURE` SMA와 shunt 경로를 확인합니다. 이 장치에서는 35 dB 이상에서 ADC clipping이 발생했습니다.

## 노트북이 수행하는 작업

### 00 사전점검

target 플래시를 지우고 번들 비밀번호 펌웨어를 기록합니다. invalid, `h`, `h0px3`의 UART 응답과 파형 폭, clipping을 확인합니다.

### 01 비밀번호 SPA

00에서 기록한 비밀번호 펌웨어를 그대로 사용합니다. 36개 후보를 위치마다 한 번씩 측정하고 전체 3,000샘플 SAD를 원시 파형에서 계산해 `h0px3`를 복구합니다.

### 02 HW·HD와 TVLA

TinyAES 펌웨어를 기록한 뒤 fixed 100개와 random 100개를 섞어서 측정합니다. 샘플별 Welch t-test와 `±4.5` 기준선을 표시합니다.

### 03 DPA·CPA

02에서 기록한 TinyAES 펌웨어를 그대로 사용합니다. 무작위 평문 100개의 파형을 측정하고 bit-3 DPA로 첫 바이트를 찾은 뒤 CPA로 AES-128 키 16바이트를 복구합니다.

## run 기록

새 물리 실행은 `runs/<UTC시각>-<실험명>/`에 저장됩니다.

- `metadata.json`: 장치, firmware hash, clock, trigger, 완료 상태
- `attempts.jsonl`: programming과 캡처 시도
- `preflight_trace.npy`: 알려진 입력의 점검 파형
- `traces.npz`: 완료 run의 원시 파형과 입력·응답·그룹

자동 재시도는 하지 않습니다. 실패한 run은 `state=failed`로 남고 분석에 사용하지 않습니다.
새 run 디렉터리는 로컬 측정 결과이므로 Git에 추가하지 않습니다.

## 저장소 구성

```text
notebooks/                라이브 실측 00–03
notebooks/appendix/       장비 없이 실행하는 합성 예제
src/cw_sca_tutorial/      TVLA·DPA·CPA와 하드웨어 캡처 코드
firmware/mcu/             독립 빌드용 F303/F415 펌웨어 소스
firmware/prebuilt/        검증한 HEX와 SHA-256
runs/                     시연 때 생성되는 새 물리 run
tests/                    분석 로직과 품질 게이트 검사
evidence/                 개발·검증 기록
```

기존 개발 run은 사용자 요청으로 삭제했습니다. 필요하면 Git 커밋 `562e223`에서 복구할 수 있습니다.

## 윤리와 라이선스

자신이 소유하거나 명시적으로 허가받은 교육용 장치에서만 실습합니다. 다른 시스템의 인증정보를 추출하는 데 사용하지 않습니다.

교육 흐름과 번들 펌웨어는 NewAE ChipWhisperer 자료에서 파생했습니다. 원저자·원저장소 고지는 [NOTICE.md](NOTICE.md), GPL-3.0-or-later 전문은 [LICENSE](LICENSE)에 있습니다.
