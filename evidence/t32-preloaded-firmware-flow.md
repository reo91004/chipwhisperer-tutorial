# 펌웨어 재사용 흐름

2026-10-23 사용자 요청으로 학생용 노트북 사이의 중복 programming을 제거했습니다.

1. `00_사전점검`이 번들 비밀번호 펌웨어를 기록하고 세 입력의 UART와 신호를 확인합니다.
2. `01_전력으로_비밀번호_깨기`는 `program_firmware=False`로 같은 펌웨어를 재사용합니다. 캡처 전 `h` 응답에 `PASSWORD FAIL`이 없으면 즉시 중단합니다.
3. `02_비트에서_TVLA까지`가 번들 TinyAES 펌웨어를 한 번 기록하고 fixed/random 파형을 수집합니다.
4. `03_AES_키_복구`는 `program_firmware=False`로 같은 TinyAES를 재사용합니다. FIPS-197 Appendix B Cipher Example preflight가 펌웨어 동작을 확인한 뒤 파형을 수집합니다.

`capture_password_run`과 `capture_aes_run`의 기본값은 `program_firmware=True`로 유지했습니다. CLI에서 개별 실험을 실행할 때는 이전과 같이 펌웨어를 기록합니다. programming을 생략한 run은 `attempts.jsonl`에 `status=skipped`, 예상 firmware SHA-256과 platform을 남깁니다.

메인 노트북은 00→01→02→03 순서를 요구하며, 각 노트북 첫 화면에 선행 노트북과 target 플래시 동작을 적었습니다. 코드 셀 문법과 parameter 연결은 정적으로 확인했습니다. 새 skip-programming 경로의 물리 실행은 `runs/`를 빈 상태로 유지하기 위해 이번 변경에서는 수행하지 않았습니다.
