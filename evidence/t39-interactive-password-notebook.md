# 01 비밀번호 노트북의 셀 단위 캡처 구조

2026-10-23 `01_전력으로_비밀번호_깨기.ipynb`를 upstream Lab 2_1B처럼 셀을 실행하며 과정을 따라가는 구조로 변경했습니다.

1. 첫 셀은 scope/target 연결과 `PasswordCaptureSession`만 엽니다. 00에서 기록한 펌웨어를 재사용합니다.
2. 다음 셀은 `h`와 `0`을 실제로 측정해 전체 파형과 차이 구간을 표시합니다.
3. 다음 셀은 한 위치의 invalid reference와 36개 후보를 측정하는 SAD 함수를 정의합니다.
4. 마지막 공격 셀 하나가 다섯 위치를 순서대로 캡처합니다. 각 위치가 끝날 때 현재 36개 점수 막대, 누적 heatmap, `h → h0 → h0p → h0px → h0px3` 목록을 함께 갱신합니다.
5. 세션은 `finally`에서 완료 상태로 저장하고 scope/target 연결을 닫습니다.

`PasswordCaptureSession`은 캡처 한 건마다 `attempts.jsonl`, `traces.npz`, `metadata.json`을 갱신합니다. 중간에 셀 실행이 멈춰도 그전까지의 물리 시도와 원시 파형이 run에 남습니다. preloaded 펌웨어의 boot banner가 없거나 파형 폭이 50 ADC count 미만이면 세션을 실패 상태로 저장하고 중단합니다.

노트북은 총 187개 파형(비교 2개 + 공격 185개)을 새로 측정합니다. 코드 셀 문법과 미실행 상태를 확인했으며, 새 interactive session의 물리 실행은 기존 run을 다시 만들지 않기 위해 이번 변경에서는 수행하지 않았습니다.
