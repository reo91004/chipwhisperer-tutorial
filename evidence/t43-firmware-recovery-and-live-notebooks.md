# 펌웨어 자동 복구와 라이브 노트북 검증

2026-10-23에 연결된 ChipWhisperer-Lite와 STM32F303 보드로 확인했습니다. 호스트는 Python 3.11.3, ChipWhisperer 7.0.0을 사용했습니다.

## 펌웨어 확인과 복구

- `20261023T002543Z-password-interactive`: TinyAES가 올라간 상태에서 비밀번호 세션을 `program_firmware=False`로 시작했습니다. 첫 부팅 문구 검사는 실패했고, 비밀번호 펌웨어를 한 번 기록한 뒤 재검사는 통과했습니다. `h`와 `0` 파형의 peak-to-peak는 각각 629, 625 ADC count였습니다.
- `20261023T002600Z-aes-cpa`: 비밀번호 펌웨어가 AES `set_key` 명령을 거부해 `Device failed to ack`로 중단됐습니다. 이 시도는 실패 상태와 accepted trace 0개로 보존했습니다.
- `20261023T002622Z-aes-cpa`: ACK 거부를 펌웨어 사전점검 실패로 기록하도록 수정한 뒤 TinyAES를 한 번 기록했습니다. FIPS-197 응답 `3925841d02dc09fbdc118597196a0b32`와 파형 2개를 확인했습니다.

펌웨어 SHA-256은 다음과 같습니다.

- `basic-passwdcheck-CWLITEARM.hex`: `d76a5d321a24fcd7c70bcc316bc06e47eed6ddddec6320f0a2b21dc35ae90ccd`
- `simpleserial-aes-CWLITEARM.hex`: `619460b1779e9490843c0ad41d43e76b8aaf2a550273fa04aaee5fc08497d3de`

## 00–03 실행 결과

- 00 `20261023T002706Z-password-signal-diagnostic`: 파형 3개를 측정했고 peak-to-peak는 627, 636, 701 ADC count였습니다.
- 01 `20261023T002713Z-password-interactive`: 187개 파형을 새로 측정했고 `h0px3`를 복구했습니다.
- 02 `20261023T002810Z-aes-tvla`: fixed 100개와 random 100개를 측정했습니다. 최대 절댓값 t는 36.70이었습니다.
- 03 `20261023T003343Z-aes-cpa`: 무작위 평문 200개를 측정했습니다. 8개 비트의 DPA 점수를 합산했을 때 첫 키 바이트 `0x2b`가 1/256위였고, CPA는 `2b7e151628aed2a6abf7158809cf4f3c` 16바이트를 모두 복구했습니다.

기존 100파형 run `20261023T002829Z-aes-cpa`의 bit-3 DPA에서 정답은 전체 구간 24위, 800:2300 구간 14위였습니다. 단일 비트 DPA는 같은 장비에서 새로 측정한 run마다 1위가 바뀌었습니다. 서로 다른 seed를 포함한 200파형 run 네 개로 8비트 점수 합산을 탐색했고, 같은 seed로 파형을 다시 측정한 `20261023T003343Z-aes-cpa`에서 측정 잡음에 대한 재현성을 확인했습니다. 200파형 run 다섯 개 모두 같은 합산 방식에서 `0x2b`가 1위였고 CPA는 16/16바이트를 복구했습니다. 파형 수 증가와 8비트 합산은 함께 적용했으며 두 변경의 기여를 따로 분리하지는 않았습니다.

위 결과는 번들 펌웨어와 현재 연결 구성에서 얻은 실측 결과입니다. 보드 종류는 사용자 확인값이며 소프트웨어로 세부 실리콘 표기까지 판독하지는 않았습니다. 원시 run 폴더는 저장소를 비워 달라는 요청에 따라 검증 후 macOS 휴지통으로 옮겼습니다.
