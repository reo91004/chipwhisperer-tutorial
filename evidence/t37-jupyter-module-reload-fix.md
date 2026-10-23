# Jupyter 모듈 캐시 대응

2026-10-23 기존 Jupyter 커널에서 수정 전 `capture_password_run`이 캐시되어 `program_firmware` 인자를 인식하지 못하는 오류가 발생했습니다.

터미널의 Python 3.11.3 환경에서는 `cw_sca_tutorial.hardware`가 현재 저장소의 `src/cw_sca_tutorial/hardware.py`에서 import되고, `capture_password_run`과 `capture_aes_run` signature에 `program_firmware: bool = True`가 있음을 확인했습니다.

메인 00–03의 첫 하드웨어 셀에 다음 처리를 추가했습니다.

```python
import importlib
import cw_sca_tutorial.hardware as hardware
hardware = importlib.reload(hardware)
```

각 노트북은 reload한 모듈에서 사용하는 캡처 함수를 다시 바인딩합니다. 생성 스크립트와 네 노트북에서 reload 존재 여부와 모든 코드 셀의 Python 문법을 확인했습니다. 이미 열려 있던 노트북은 디스크 변경을 다시 불러오고 커널을 재시작한 뒤 실행하는 것이 가장 확실합니다.
