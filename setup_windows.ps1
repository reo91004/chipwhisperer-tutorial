[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvDir = Join-Path $RepoRoot ".venv"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
$CwCommit = "c47aefe0d3083b5fc7392ab0698aa7446c633dd4"
$CwSourceDir = Join-Path $VenvDir "cw"
$CwCommitFile = Join-Path $CwSourceDir ".tutorial-source-commit"

if ($env:OS -ne "Windows_NT") {
    throw "This installer is for Windows. Use setup_linux.sh or setup_macos.sh instead."
}

function Invoke-Checked {
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [Parameter(Mandatory = $true)][string[]]$Arguments
    )
    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed ($LASTEXITCODE): $FilePath $($Arguments -join ' ')"
    }
}

function Find-Python311 {
    $launcher = Get-Command py -ErrorAction SilentlyContinue
    if ($null -ne $launcher) {
        $resolved = $null
        $launcherExitCode = 1
        try {
            $resolved = & $launcher.Source -3.11 -c "import sys; print(sys.executable)" 2>$null
            $launcherExitCode = $LASTEXITCODE
        } catch {
            $resolved = $null
        }
        if ($launcherExitCode -eq 0 -and $null -ne $resolved -and (Test-Path $resolved)) {
            return $resolved.Trim()
        }
    }

    $candidates = @(
        (Join-Path $env:LOCALAPPDATA "Programs\Python\Python311\python.exe"),
        (Join-Path $env:ProgramFiles "Python311\python.exe")
    )
    foreach ($candidate in $candidates) {
        if (Test-Path $candidate) {
            return $candidate
        }
    }
    return $null
}

if (-not (Test-Path $VenvPython)) {
    $PythonExe = Find-Python311
    if ($null -eq $PythonExe) {
        $winget = Get-Command winget -ErrorAction SilentlyContinue
        if ($null -eq $winget) {
            throw "Python 3.11 is required. Install it from https://python.org and rerun this script."
        }
        Invoke-Checked -FilePath $winget.Source -Arguments @(
            "install", "--id", "Python.Python.3.11", "--exact", "--scope", "user",
            "--accept-package-agreements", "--accept-source-agreements"
        )
        $PythonExe = Find-Python311
        if ($null -eq $PythonExe) {
            throw "Python 3.11 was installed but not found. Open a new PowerShell window and rerun this script."
        }
    }
    Invoke-Checked -FilePath $PythonExe -Arguments @("-m", "venv", $VenvDir)
}

Invoke-Checked -FilePath $VenvPython -Arguments @(
    "-c", "import sys; assert sys.version_info[:2] == (3, 11), 'Remove .venv and rerun with Python 3.11'"
)
Invoke-Checked -FilePath $VenvPython -Arguments @("-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel")

if (-not (Test-Path $CwSourceDir)) {
    $TempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("chipwhisperer-tutorial-" + [guid]::NewGuid())
    $ArchivePath = Join-Path $TempRoot "chipwhisperer.zip"
    New-Item -ItemType Directory -Path $TempRoot | Out-Null
    try {
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        Invoke-WebRequest -Uri "https://github.com/newaetech/chipwhisperer/archive/$CwCommit.zip" -OutFile $ArchivePath -UseBasicParsing
        Expand-Archive -Path $ArchivePath -DestinationPath $TempRoot
        New-Item -ItemType Directory -Path (Split-Path -Parent $CwSourceDir) -Force | Out-Null
        Move-Item -Path (Join-Path $TempRoot "chipwhisperer-$CwCommit") -Destination $CwSourceDir
        Set-Content -Path $CwCommitFile -Value $CwCommit -Encoding ascii -NoNewline
    } finally {
        Remove-Item -Path $TempRoot -Recurse -Force -ErrorAction SilentlyContinue
    }
}
$CwProject = Join-Path $CwSourceDir "pyproject.toml"
$CwFirmware = Join-Path $CwSourceDir "software\chipwhisperer\hardware\firmware\cwlite\version.txt"
if (-not (Test-Path $CwProject) -or -not (Test-Path $CwFirmware) -or
    -not (Test-Path $CwCommitFile) -or (Get-Content -Raw $CwCommitFile).Trim() -ne $CwCommit) {
    throw "Pinned ChipWhisperer source is incomplete. Remove .venv and rerun this script."
}
Invoke-Checked -FilePath $VenvPython -Arguments @("-m", "pip", "install", "--editable", $CwSourceDir)
Invoke-Checked -FilePath $VenvPython -Arguments @("-m", "pip", "install", "--editable", $RepoRoot)
Invoke-Checked -FilePath $VenvPython -Arguments @(
    "-m", "ipykernel", "install", "--user", "--name", "chipwhisperer-tutorial",
    "--display-name", "Python (ChipWhisperer Tutorial)"
)

$PasswordFirmware = Join-Path $RepoRoot "firmware\prebuilt\basic-passwdcheck-CWLITEARM.hex"
$AesFirmware = Join-Path $RepoRoot "firmware\prebuilt\simpleserial-aes-CWLITEARM.hex"
if (-not (Test-Path $PasswordFirmware) -or -not (Test-Path $AesFirmware)) {
    throw "Bundled CWLITEARM firmware is missing."
}
Invoke-Checked -FilePath $VenvPython -Arguments @("-m", "unittest", "discover", "-s", (Join-Path $RepoRoot "tests"), "-v")

Write-Host ""
Write-Host "Setup complete. Modern ChipWhisperer-Lite firmware uses the automatic WinUSB driver."
Write-Host "If Device Manager does not show it under 'Universal Serial Bus devices', follow the Zadig instructions at:"
Write-Host "  https://chipwhisperer.readthedocs.io/en/latest/drivers.html#windows-drivers"
Write-Host "Start Jupyter with:"
Write-Host "  & `"$VenvDir\Scripts\jupyter-lab.exe`""
