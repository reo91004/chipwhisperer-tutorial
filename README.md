# ChipWhisperer 실측 부채널 분석 시연

STM32F303과 ChipWhisperer-Lite에서 직접 측정한 전력 파형으로 비밀번호 SPA, fixed-vs-random TVLA, AES DPA·CPA를 빠르게 시연하는 Jupyter 튜토리얼입니다. 메인 노트북은 합성 데이터로 자동 대체하지 않습니다.

## 수업 순서

`00`은 강사용 점검입니다. 학생 시연은 `01`부터 시작합니다.

| 순서 | 노트북 | 시연 내용 | 권장 시간 |
|---:|---|---|---:|
| 준비 | `00_강사용_사전점검.ipynb` | 저장 run, USB, 신호 폭 확인 | 수업 전 |
| 1 | `01_전력으로_비밀번호_깨기.ipynb` | 실제 파형으로 `h0px3` 복구 | 10분 |
| 2 | `02_비트에서_TVLA까지.ipynb` | HW·HD와 실측 fixed-vs-random TVLA | 10분 |
| 3 | `03_AES_키_복구.ipynb` | 실측 DPA 한 바이트와 CPA 16바이트 복구 | 15분 |

기존 합성 예제는 `notebooks/appendix/`에 남겼습니다. 장비 없이 원리를 복습하거나 과제로 사용할 때만 열면 됩니다.

## 확인된 실측 결과

메인 노트북은 [data/demo_runs.json](data/demo_runs.json)에 고정한 다음 run을 읽습니다.

- 비밀번호 SPA: 185개 파형으로 `h0px3` 복구
- TVLA: fixed 500개와 random 500개, 최대 `|t|=72.80`, 비교용 0:50 창은 3.79
- TinyAES CPA: 500개 파형으로 `2b7e151628aed2a6abf7158809cf4f3c` 16바이트 복구
- TinyAES DPA: 첫 바이트 `0x2b`가 256개 후보 중 1위

각 메인 노트북의 실측 데이터 로딩 셀에 `DATA SOURCE: MEASURED`, run ID, target이 표시됩니다.

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

## 내일 보드를 연결한 뒤

먼저 강사용 `00` 노트북과 짧은 진단을 실행합니다.

```bash
python scripts/run_hardware_capture.py diagnostic \
  --platform CWLITEARM \
  --target-identification STM32F303
```

비밀번호 실습은 25 dB를 사용합니다. 정상 연결에서 preflight 파형 폭은 약 608 ADC count였습니다. 한 자릿수 count만 나온다면 공격을 반복하지 말고 target의 `MEASURE` SMA와 shunt 경로부터 확인합니다. 이 장치에서는 35 dB 이상에서 ADC clipping이 발생했습니다.

`01` 노트북의 `CAPTURE_LIVE_PREVIEW=True`를 켜면 invalid, `h`, `h0px3` 세 입력만 새로 측정합니다. 긴 공격은 저장된 실측 run으로 진행하므로 시연 시간이 늘어나지 않습니다.

전체 데이터를 다시 수집하려면 다음 명령을 사용합니다.

```bash
./scripts/build_firmware.sh
python scripts/run_hardware_capture.py password --platform CWLITEARM --target-identification STM32F303
python scripts/run_hardware_capture.py tvla --platform CWLITEARM --target-identification STM32F303 --tvla-traces 1000
python scripts/run_hardware_capture.py aes --platform CWLITEARM --target-identification STM32F303 --aes-traces 500
```

캡처 명령은 target 플래시를 지우고 번들 교육용 펌웨어를 기록합니다. 연결된 교육용 target에서만 실행하십시오.

## 저장소 구성

```text
data/demo_runs.json       수업에 고정한 실측 run 목록
notebooks/                강사용 00과 학생용 01–03
notebooks/appendix/       장비 없이 실행하는 합성 예제 부록
src/cw_sca_tutorial/      DPA·CPA·TVLA와 하드웨어 캡처 코드
firmware/mcu/             독립 빌드용 F303/F415 펌웨어 소스
firmware/prebuilt/        검증한 HEX와 SHA-256
runs/                     물리 run의 파형·입력·설정·시도 기록
tests/                    분석 로직과 품질 게이트 검사
evidence/                 빌드·노트북 실행·독립 검토 기록
```

실측 근거와 초기 연결 실패의 원인 분석은 [evidence/t17-hardware-results.md](evidence/t17-hardware-results.md)에 있습니다.

## 윤리와 라이선스

자신이 소유하거나 명시적으로 허가받은 교육용 장치에서만 실습합니다. 다른 시스템의 인증정보를 추출하는 데 사용하지 않습니다.

교육 흐름과 번들 펌웨어는 NewAE ChipWhisperer 자료에서 파생했습니다. 원저자·원저장소 고지는 [NOTICE.md](NOTICE.md), GPL-3.0-or-later 전문은 [LICENSE](LICENSE)에 있습니다.
