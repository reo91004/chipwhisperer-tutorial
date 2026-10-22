# 실측 run 형식

이 디렉터리는 시연 전에 비워 둡니다. `00`–`03` 노트북을 실행할 때마다 새 run이 생성됩니다.

각 물리 실행은 `UTC시각-실험명/`에 다음을 함께 둡니다.

- `metadata.json`: 장치·펌웨어·클록·트리거·상태·지원되는 주장 범위
- `attempts.jsonl`: 프로그래밍과 코드가 정상 처리하거나 명시적으로 거부한 캡처 시도
- `preflight_trace.npy`: 알려진 입력으로 얻은 진단 파형
- `traces.npz`: 완료된 run의 원시 파형, 입력, 응답, 키 또는 후보 레이블
- `partial_traces.npz`: 실패 전에 수집된 파형이 있을 때만 생성

`metadata.json`의 `state`가 `complete`가 아니면 결과 주장에 사용하지 않습니다. 자동 재시도는 하지 않으므로 실패한 시도가 성공 데이터로 바뀌지 않습니다.

파형을 읽거나 시도 행을 쓰기 전에 예상하지 못한 API 예외가 발생하면 metadata와 programming 기록만 남을 수 있습니다. `20261022T124451Z-aes-cpa`가 이 경우이며, claim-bearing run으로 사용하지 않습니다.

