# 축소 캡처와 펌웨어 재사용 실측

2026-10-23 사용자가 메인 노트북을 실행해 만든 로컬 run을 확인했습니다. run 디렉터리는 `.gitignore`에 따라 Git에 추가하지 않습니다.

## 00 사전점검

- Run: `20261023T000745Z-password-signal-diagnostic`
- 3/3 accepted, UART validation passed
- Duration: 5.12초
- Median peak-to-peak: 626 ADC counts

## 01 비밀번호

- Run: `20261023T001023Z-password-spa`
- `program_firmware=false`: 00에서 기록한 비밀번호 펌웨어 재사용
- Preflight: `h` → `PASSWORD FAIL`
- 185/185 accepted
- `h0px3` recovery validation passed
- Duration: 33.01초

## 02 TVLA

- Run: `20261023T001213Z-aes-tvla`
- `program_firmware=true`: TinyAES 펌웨어 기록
- fixed/random 100개씩, 총 200/200 accepted
- FIPS-197 Appendix B Cipher Example preflight passed
- Maximum `|t|=30.56` at sample 122
- Duration: 10.85초

새 TVLA run은 trigger 직후부터 t-value가 높아 0:50 구간을 wrong-window control로 사용할 수 없었습니다. 학생용 02 노트북에서는 해당 비교 출력 문구를 제거하고 전체 t-value와 `±4.5` 기준선만 표시합니다.
