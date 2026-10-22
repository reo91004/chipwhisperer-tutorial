# 연결 후 라이브 미리보기 검증

2026-10-23(Asia/Seoul)에 `01_전력으로_비밀번호_깨기.ipynb`의 opt-in 라이브 셀이 호출하는 것과 같은 경로를 실행했습니다.

- Capture: ChipWhisperer-Lite serial `50203220594a48303130373132323034`
- Target: user-identified STM32F303, platform `CWLITEARM`
- Firmware: `basic-passwdcheck-CWLITEARM.hex`, SHA-256 `d76a5d321a24fcd7c70bcc316bc06e47eed6ddddec6320f0a2b21dc35ae90ccd`
- Run: `runs/20261022T234721Z-password-signal-diagnostic`
- Gain: 24.8359375 dB
- Accepted traces: 3/3
- UART: invalid와 `h`는 `PASSWORD FAIL`, `h0px3`는 `Access granted, Welcome!`
- Median peak-to-peak: 616 ADC counts
- ADC range: 65–769, clipping 없음
- State: `complete`, `uart_validation=passed`

자동 재시도나 설정 변경은 없었습니다. 이 run은 수업용 짧은 라이브 캡처 경로의 진단 근거이며, 전체 비밀번호·TVLA·CPA 결과는 `data/demo_runs.json`에 고정한 claim-bearing run을 계속 사용합니다.
