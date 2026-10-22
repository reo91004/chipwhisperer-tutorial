# ChipWhisperer로 눈으로 배우는 부채널 분석

학부생이 “코드가 달라지면 파형이 달라지고, 데이터에 따라 달라지는 아주 작은 차이를 모으면 비밀을 복구할 수 있다”는 흐름을 그래프로 확인하는 독립형 Jupyter 실습입니다. 원본 ChipWhisperer 저장소 없이 이 폴더만으로 합성 실습, F303/F415 펌웨어 빌드, CW-Lite 캡처, 오프라인 재분석을 수행할 수 있습니다.

## 90–120분 권장 순서

| 순서 | 노트북 | 핵심 질문 |
|---:|---|---|
| 1 | `00_파형과_트리거.ipynb` | 계산은 전력 파형 어디에 나타나는가? |
| 2 | `01_타이밍_SPA_비밀번호.ipynb` | 조기 종료 비교는 왜 문자를 한 글자씩 누설하는가? |
| 3 | `02_TVLA_누설_검정.ipynb` | fixed-vs-random Welch t-test로 누설 시점을 어떻게 찾는가? |
| 4 | `03_DPA_AES_한바이트.ipynb` | 한 비트로 파형을 나누면 왜 정답 키에서만 차이가 남는가? |
| 5 | `04_CPA_AES_전체키.ipynb` | 해밍 무게와 Pearson 상관으로 16바이트를 어떻게 복구하는가? |
| 6 | `05_CWLITE_F303_실측.ipynb` | 합성 모델과 실제 CW-Lite/F303 파형은 무엇이 같고 다른가? |

앞의 다섯 노트북은 고정 seed로 생성한 **합성 파형**입니다. 여섯 번째만 물리 측정입니다. 합성 성공은 실제 장치 누설이나 실제 키 복구의 증거가 아닙니다.

## 설치와 실행

Python 3.10 이상에서 다음만 실행합니다.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python scripts/make_notebooks.py
jupyter lab
```

현재 이 저장소를 만든 환경은 Python 3.11.3, ChipWhisperer 7.0.0, NumPy 2.4.3입니다. 실행 검증 결과는 `evidence/`와 각 실측 `runs/`에 남깁니다.

## CW-Lite + STM32F303 실측

권장 대상은 STM32F303이며 플랫폼 이름은 `CWLITEARM`입니다. ChipWhisperer 빌드 시스템에서 이 이름은 CW-Lite Arm과 CW308 STM32F3 계열에 쓰입니다. 이전 F415 시도는 캡처 자체는 정상이나 비밀번호 점수가 안정적으로 복구되지 않아 `runs/`에 기각 근거와 함께 보존했습니다. 수업의 필수 성공 경로는 F303 검증 run입니다.

물리 연결은 수업 전에 다음을 확인합니다.

- 외장 CW308을 쓴다면 20-pin 케이블과 측정 SMA가 연결되어 있고 target 전원이 켜져 있다.
- 내장 CW-Lite Arm target을 쓴다면 기본 20-pin/SMA 연결 상태를 유지한다.
- 외부 전원과 CW 전원이 충돌하지 않는다.
- 기본 외부 클록은 HS2 7.37 MHz이고 ADC는 그 4배로 샘플링한다.
- 기본값이 아닌 J16이나 Rev-02 전용 점퍼 절차는 임의로 적용하지 않는다.

ARM GNU toolchain이 필요합니다. macOS에서는 `brew install arm-none-eabi-gcc`를 사용할 수 있고, 이 컴퓨터에 이미 있는 Arm GNU 14.3 경로도 빌드 스크립트가 감지합니다.

```bash
./scripts/build_firmware.sh
python scripts/run_hardware_capture.py password --platform CWLITEARM --target-identification STM32F303
python scripts/run_hardware_capture.py tvla --platform CWLITEARM --target-identification STM32F303 --tvla-traces 1000
python scripts/run_hardware_capture.py aes --platform CWLITEARM --target-identification STM32F303 --aes-traces 500
```

비밀번호 실습은 25 dB를 사용합니다. 정상 연결에서는 파형 폭이 약 618 ADC count였고 clipping이 없었습니다. 같은 장치에서 35 dB 이상은 ADC의 0과 1023에 닿았습니다. 파형 폭이 한 자릿수 count라면 분석을 반복하지 말고 `MEASURE` SMA와 shunt 경로부터 확인합니다.

첫 명령은 저장소에 포함된 소스로 두 펌웨어를 빌드합니다. 캡처 명령은 플래시를 지우고 새 펌웨어를 기록하므로 연결된 교육용 대상에서만 실행해야 합니다. 정상 캡처와 코드가 명시적으로 거부한 시도는 `runs/*/attempts.jsonl`에 기록합니다. 파형을 읽기 전에 예상하지 못한 API 예외가 나면 metadata와 programming 기록만 남을 수 있습니다.

## 증거와 주장 범위

| 자료 | 출처 | 말할 수 있는 것 | 말할 수 없는 것 |
|---|---|---|---|
| 00–04 노트북 | 고정 seed 합성 | 타이밍/SPA/TVLA/DPA/CPA 알고리즘의 원리와 구현 | 실제 보드의 누설 존재 |
| password run | CW-Lite 물리 측정 | 번들 조기 종료 비교 구현의 타이밍/전력 누설과 비밀번호 복구 | 일반적인 비밀번호 구현 전체의 취약성 |
| TVLA run | CW-Lite/F303 물리 측정 | 번들 TinyAES의 fixed-vs-random 1차 Welch t-test 기준선 초과 | 키 복구 또는 다른 구현의 누설 여부 |
| AES run | CW-Lite/F303 물리 측정 | 번들 TinyAES 첫 라운드의 누설과 고정 키 복구 | 하드웨어 AES, 시스템 전체, 다른 보드의 키 복구 |

AES 실측은 FIPS-197 Appendix B Cipher Example의 알려진 평문·키·암호문으로 preflight를 통과해야 시작합니다. 타임아웃, 응답 길이 오류, 잘린/상수/비유한 파형은 거부하며 자동 재시도하지 않습니다. CPA 노트북은 올바른 전체 구간뿐 아니라 잘못된 시간 창과 파형 수 변화도 함께 보여 줍니다.

## 이 장치에서 확인한 결과

- 비밀번호 SPA: 185개 파형으로 `h0px3` 복구
- fixed-vs-random TVLA: 고정 500개와 무작위 500개, 최대 `|t|=72.80`, 잘못된 0:50 창은 3.79
- TinyAES CPA: 500개 파형으로 `2b7e151628aed2a6abf7158809cf4f3c` 16바이트 복구

실측 근거와 실패 run을 포함한 원인 분석은 [evidence/t17-hardware-results.md](evidence/t17-hardware-results.md)에 정리했습니다.

## 저장소 구성

```text
notebooks/              순서대로 실행하는 강의 노트북
src/cw_sca_tutorial/    합성 생성, DPA/CPA, 실측 캡처 코드
firmware/mcu/           독립 빌드에 필요한 F303/F415 펌웨어 소스
firmware/prebuilt/      이 소스에서 검증한 HEX와 SHA-256
runs/                   물리 실행별 원시 파형·설정·시도 기록
tests/                  합성 복구와 파형 품질 게이트 검사
evidence/               빌드·노트북 실행·검토 증거
```

## 윤리와 라이선스

자신이 소유하거나 명시적으로 허가받은 교육용 장치에서만 실습합니다. 다른 시스템의 인증정보를 추출하는 데 사용하지 않습니다.

교육 흐름과 번들 펌웨어는 NewAE ChipWhisperer 자료에서 파생했습니다. 원저자·원저장소 고지는 [NOTICE.md](NOTICE.md), GPL-3.0-or-later 전문은 [LICENSE](LICENSE)에 있습니다.
