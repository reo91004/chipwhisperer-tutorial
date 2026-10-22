# 실측 중심 시연 노트북 검증

2026-10-23(Asia/Seoul)에 보드 없이 저장된 claim-bearing run으로 메인 노트북 네 개를 실행했습니다.

- `00_강사용_사전점검.ipynb`: CW-Lite 0대 상태에서도 저장 run 세 개, 비밀번호 preflight 608 ADC count, TVLA 500/500, CPA 500개 검증 통과
- `01_전력으로_비밀번호_깨기.ipynb`: measured run 표시, 첫 글자 `h` 점수 248,593, `h0px3` 복구
- `02_비트에서_TVLA까지.ipynb`: HW(0x3A)=4, HD(0x00→0xFF)=8, measured TVLA 최대 `|t|=72.80`
- `03_AES_키_복구.ipynb`: measured DPA 첫 바이트 `0x2b`, CPA 최대 상관 0.8935, AES 키 16/16바이트 복구

모든 plot 제목·축·범례는 영어이며 한글 glyph 경고가 없습니다. 실행 로그는 `evidence/t20-measured-demo-notebooks-final.log`에 있습니다. 라이브 미리보기는 기본값이 꺼져 있어 보드 없이도 전체 메인 흐름을 실행할 수 있습니다.
