# 공식 ChipWhisperer에서 CW-Lite + STM32F303 사용하기

이 문서는 공식 `newaetech/chipwhisperer` 저장소의 Jupyter 실습을 ChipWhisperer-Lite와 STM32F303 target board에서 실행할 때 확인할 설정을 정리합니다.

## 1. 보드 이름과 PLATFORM

STM32F303이라고 해서 모든 보드가 같은 `PLATFORM`을 사용하는 것은 아닙니다.

| 실제 구성 | `PLATFORM` |
|---|---|
| CW-Lite ARM target board의 STM32F303 | `CWLITEARM` |
| CW308 UFO + STM32F3 target | `CW308_STM32F3` |
| CW308 UFO + STM32F415 target | `CW308_STM32F4` |

이 프로젝트에서 검증한 구성은 `CWLITEARM`입니다.

## 2. 자동 설치

운영체제에 맞는 공식 저장소용 스크립트를 실행합니다.

```bash
# Linux
./setup_official_linux.sh

# macOS
./setup_official_macos.sh
```

Windows PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File .\setup_official_windows.ps1
```

스크립트는 다음 작업을 수행합니다.

1. 공식 ChipWhisperer 저장소 전체를 `git clone --recursive`
2. 검증한 root와 Jupyter submodule 커밋으로 고정
3. Python 3.11 가상환경과 공식 Jupyter requirements 설치
4. ARM GCC, `make`, USB 권한 준비
5. F303용 비밀번호·AES 펌웨어 빌드 확인
6. F303용 Jupyter 커널 등록
7. 원본을 보존한 F303용 Lab 2_1B 복사본 생성

기본 clone 위치는 다음과 같습니다.

```text
chipwhisperer-tutorial/_workspace/official-chipwhisperer
```

생성되는 준비된 노트북은 다음과 같습니다.

```text
jupyter/courses/sca101/
SOLN_Lab 2_1B - Power Analysis for Password Bypass - CWLITEARM.ipynb
```

## 3. 기본 설정 셀

공식 노트북 상단의 hardware configuration 셀에서 다음 값을 사용합니다.

```python
SCOPETYPE = "OPENADC"
PLATFORM = "CWLITEARM"
VERSION = "HARDWARE"
```

- `OPENADC`: CW-Lite/CW-Pro 계열 scope
- `CWLITEARM`: CW-Lite용 STM32F303 target
- `HARDWARE`: 저장된 파형 대신 실제 보드 사용

다음 값들은 현재 구성과 다릅니다.

```python
PLATFORM = "CWHUSKY"        # Husky용
PLATFORM = "CW308_STM32F4"  # STM32F415용
```

## 4. 비밀번호 실습

`basic-passwdcheck`를 사용하는 Lab 2_1B 설정입니다.

```python
SCOPETYPE = "OPENADC"
PLATFORM = "CWLITEARM"
CRYPTO_TARGET = "NONE"
SS_VER = "SS_VER_2_1"
VERSION = "HARDWARE"
```

빌드 셀은 `PLATFORM`과 `SS_VER`을 그대로 사용합니다.

```bash
%%bash -s "$PLATFORM" "$SS_VER"
cd ../../../firmware/mcu/basic-passwdcheck
make PLATFORM=$1 CRYPTO_TARGET=NONE SS_VER=$2
```

결과 펌웨어 이름은 다음과 같습니다.

```text
basic-passwdcheck-CWLITEARM.hex
```

## 5. AES 실습

TinyAES를 사용하는 HW·DPA·CPA 실습의 일반적인 설정입니다.

```python
SCOPETYPE = "OPENADC"
PLATFORM = "CWLITEARM"
CRYPTO_TARGET = "TINYAES128C"
SS_VER = "SS_VER_2_1"
VERSION = "HARDWARE"
```

빌드 예시는 다음과 같습니다.

```bash
%%bash -s "$PLATFORM" "$CRYPTO_TARGET" "$SS_VER"
cd ../../../firmware/mcu/simpleserial-aes
make PLATFORM=$1 CRYPTO_TARGET=$2 SS_VER=$3 -j
```

결과 펌웨어 이름은 다음과 같습니다.

```text
simpleserial-aes-CWLITEARM.hex
```

일부 기존 실습은 `SS_VER_1_1`을 사용합니다. `SS_VER`은 무조건 바꾸기보다 해당 노트북이 지정한 값을 우선 사용해야 합니다. Python target 통신과 펌웨어 빌드의 `SS_VER`이 같아야 합니다.

## 6. SOLN 노트북의 설정 위치

통합 SOLN 노트북에는 보통 다음과 같은 셀이 있습니다.

```python
SCOPETYPE = "OPENADC"
PLATFORM = "CWHUSKY"
CRYPTO_TARGET = "NONE"
VERSION = "HARDWARE"
```

F303/Lite에서는 이 셀을 다음처럼 바꿉니다.

```python
SCOPETYPE = "OPENADC"
PLATFORM = "CWLITEARM"
CRYPTO_TARGET = "NONE"
SS_VER = "SS_VER_2_1"
VERSION = "HARDWARE"
```

그 아래에서 `(HARDWARE).ipynb`를 `%run`하기 전에 설정 셀을 먼저 실행합니다.

```python
%run "Lab 2_1B - Power Analysis for Password Bypass (HARDWARE).ipynb"
```

설치 스크립트가 생성한 `- CWLITEARM.ipynb` 복사본에는 이 설정이 이미 들어 있습니다.

## 7. Jupyter 커널

F303용 노트북에서는 다음 커널을 선택합니다.

```text
Python (Official ChipWhisperer, F303)
```

이 커널의 `PATH`에는 ARM GCC와 `make`가 포함됩니다. 다른 `python3` 커널을 선택하면 `%%bash` 빌드 셀에서 `arm-none-eabi-gcc`를 찾지 못할 수 있습니다.

커널을 바꾼 뒤에는 `Restart Kernel`을 실행하고 노트북을 위에서부터 다시 실행합니다.

## 8. 물리 연결

다음을 확인합니다.

- CW-Lite USB 연결
- CW-Lite와 F303 target 사이 20-pin 케이블
- `MEASURE` SMA 케이블
- target 전원
- 다른 ChipWhisperer 장치는 분리

`scope.default_setup()`은 일반적으로 HS2 target clock, ADC, trigger를 설정합니다. 현재 구성에서는 별도의 `MCU_CLK=INT` 설정을 추가하지 않습니다.

## 9. 무엇을 수정하지 않아도 되나요?

다음 파일은 보통 수정할 필요가 없습니다.

- ChipWhisperer Python 라이브러리 소스
- `Setup_Generic.ipynb`
- STM32 HAL
- firmware C 코드

일반적인 실습에서는 노트북 상단의 `SCOPETYPE`, `PLATFORM`, `CRYPTO_TARGET`, `SS_VER`, `VERSION`만 맞추면 됩니다. `Setup_Generic.ipynb`가 `CWLITEARM`을 보고 `STM32FProgrammer`를 선택합니다.

## 10. 자주 발생하는 오류

### `arm-none-eabi-gcc`를 찾을 수 없음

Jupyter 커널이 다음인지 확인합니다.

```text
Python (Official ChipWhisperer, F303)
```

### `Device failed to ack`

펌웨어 빌드의 `SS_VER`과 Python 통신의 `SS_VER`이 같은지 확인합니다. 버전이 다르면 펌웨어를 다시 빌드하고 기록합니다.

### `Timeout in OpenADC capture, no trigger seen`

다음 순서로 확인합니다.

1. `SCOPETYPE="OPENADC"`
2. `PLATFORM="CWLITEARM"`
3. F303용 HEX가 기록됐는지
4. 20-pin 케이블
5. `MEASURE` SMA
6. target clock
7. trigger를 발생시키는 올바른 펌웨어인지

### Linux에서 장치를 열 수 없음

설치 후 로그아웃·로그인하고 CW-Lite를 재연결합니다. 설치 스크립트는 별도 udev 규칙과 `chipwhisperer` system group을 설정합니다.

### Windows에서 장치가 보이지 않음

최신 CW-Lite firmware는 WinUSB를 자동 사용합니다. Device Manager의 `Universal Serial Bus devices` 아래에서 ChipWhisperer-Lite를 확인합니다. 잘못된 드라이버가 잡힌 경우 공식 ChipWhisperer WinUSB/Zadig 안내를 따릅니다.

## 핵심 요약

CW-Lite + STM32F303에서는 다음 두 값이 핵심입니다.

```python
SCOPETYPE = "OPENADC"
PLATFORM = "CWLITEARM"
```

비밀번호 실습:

```python
CRYPTO_TARGET = "NONE"
```

AES 실습:

```python
CRYPTO_TARGET = "TINYAES128C"
```

`SS_VER`은 해당 노트북과 펌웨어 빌드에서 같은 값을 사용합니다.
