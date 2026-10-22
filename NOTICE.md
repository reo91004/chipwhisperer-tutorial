# 출처와 라이선스 고지

이 저장소의 교육 흐름은 NewAE Technology Inc.의 ChipWhisperer SCA101 자료, 특히 다음 실습에서 파생했습니다.

- `Lab 2_1B - Power Analysis for Password Bypass`
- `Lab 3_3 - DPA on Firmware Implementation of AES`
- `Lab 4_1 - Power and Hamming Weight Relationship`
- `Lab 4_2 - CPA on Firmware Implementation of AES`

원출처는 <https://github.com/newaetech/chipwhisperer>와 <https://chipwhisperer.io/>입니다. 참조한 로컬 원본은 ChipWhisperer commit `c47aefe0d3083b5fc7392ab0698aa7446c633dd4`, Jupyter submodule commit `dee4ddd71fa534457b97df6880ad4fecbc77bb94`입니다.

`firmware/mcu/` 아래의 F415 빌드 지원 코드, `basic-passwdcheck`, `simpleserial-aes`, SimpleSerial, tiny-AES 관련 파일은 위 ChipWhisperer 원본에서 필요한 부분만 복사한 것입니다. 각 파일의 저작권·라이선스 헤더가 우선 적용됩니다. 이 저장소 전체는 파생 교육자료와 펌웨어의 조건을 보존하기 위해 GPL-3.0-or-later로 둡니다. 전체 GPL v3 문서는 [LICENSE](LICENSE)에 있습니다.

ChipWhisperer는 NewAE Technology Inc.의 상표입니다. 이 저장소는 NewAE의 공식 강의자료가 아닙니다.
