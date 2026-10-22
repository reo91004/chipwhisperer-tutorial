# STM32F303 실측 결과

날짜는 2026-10-22(Asia/Seoul)입니다. Capture 장치는 ChipWhisperer-Lite serial `50203220594a48303130373132323034`, Python package는 로컬 ChipWhisperer 7.0.0, capture firmware는 0.65.0입니다. 라이브러리는 capture firmware를 최신 상태로 판정했습니다.

## 연결 진단

측정 SMA가 잘못 연결된 상태에서는 25 dB 비밀번호 파형의 peak-to-peak가 5 ADC count였습니다. UART의 `PASSWORD FAIL`/`Access granted` 분기는 정상이었지만 upstream Lab 2_1B도 `o3v3t`로 실패했습니다. 연결을 바로잡은 뒤 같은 25 dB 진단 파형은 618 count가 되었고, 35/45 dB에서는 0과 1023에 닿아 clipping됐습니다.

- 실패 진단: `runs/20261022T123657Z-password-signal-diagnostic`
- 연결 수정 후 진단: `runs/20261022T124144Z-password-signal-diagnostic`
- upstream 대조 실행: `evidence/t09-upstream-lab21b-f303.ipynb`

따라서 이번 실패의 원인은 Python/펌웨어 버전이나 비밀번호 공격 로직이 아니라 측정 SMA/shunt 경로였습니다. 이 결론은 동일 장치에서 UART와 버전을 유지한 채 아날로그 진폭이 5→618 count로 바뀌고 원본 공격이 성공한 결과에 한정합니다.

## 비밀번호 SPA

- Run: `runs/20261022T124300Z-password-spa`
- Evidence origin/purpose: measured, claim-bearing
- 설정: 3,000 samples, gain 24.8359375 dB, 후보당 1개 파형, 전체 구간 SAD
- 수락 파형: 185/185
- 결과: `h0px3`
- 첫 글자 점수: `h=248593`, 2위 `b=9464`
- Claim scope: 번들 조기 종료 비밀번호 비교 구현의 비밀번호 복구

## fixed-vs-random TVLA

- Run: `runs/20261022T125656Z-aes-tvla`
- Evidence origin/purpose: measured, claim-bearing
- 설정: 고정 평문 500개 + 무작위 평문 500개, 순서 shuffle, 5,000 samples, gain 24.8359375 dB
- 검정: 샘플별 1차 non-specific Welch t-test, 표시 기준 `|t|=4.5`
- 최대 `|t|`: 72.80 at sample 474
- 기준 초과 샘플: 3,258/5,000
- 잘못된 창 0:50 최대 `|t|`: 3.79
- Claim scope: 이 번들 TinyAES run의 fixed-vs-random 1차 TVLA 기준 초과. 키 복구 결과가 아닙니다.

## TinyAES CPA

- Run: `runs/20261022T124611Z-aes-cpa`
- Evidence origin/purpose: measured, claim-bearing
- Preflight: FIPS-197 Appendix B Cipher Example ciphertext 일치
- 설정: 무작위 평문 500개, 5,000 samples, gain 24.8359375 dB, HW(SBox[plaintext XOR guess])
- 복구 키: `2b7e151628aed2a6abf7158809cf4f3c` (16/16 bytes)
- 첫 바이트 최대 `|ρ|`: 0.8935
- 잘못된 창 0:50 최대 `|ρ|`: 0.0896
- 25, 50, 100, 200, 300, 500개 파형에서 첫 바이트 rank는 모두 1
- Claim scope: 이 STM32F303에서 실행한 번들 software TinyAES 첫 라운드 누설과 고정 AES-128 키 복구

성공한 claim-bearing run은 firmware SHA-256, scope/clock/trigger 설정, 캡처 시도, 원시 파형, 완료 상태를 각 run 디렉터리에 보존합니다. 실패한 `20261022T124451Z-aes-cpa`는 preflight 파형을 읽는 API 예외가 시도 행 기록 전에 발생해 metadata와 programming 기록만 남았습니다. 이 run은 결과 주장에 사용하지 않습니다.
