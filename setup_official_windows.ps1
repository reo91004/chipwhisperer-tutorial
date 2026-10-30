[CmdletBinding()]
param(
    [string]$InstallDir = ""
)

$ErrorActionPreference = "Stop"
$InstallerRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
if ([string]::IsNullOrWhiteSpace($InstallDir)) {
    $InstallDir = Join-Path $InstallerRoot "_workspace\official-chipwhisperer"
}
$OfficialRoot = [System.IO.Path]::GetFullPath($InstallDir)
$CwCommit = "c47aefe0d3083b5fc7392ab0698aa7446c633dd4"
$JupyterCommit = "dee4ddd71fa534457b97df6880ad4fecbc77bb94"
$CwUrl = "https://github.com/newaetech/chipwhisperer.git"

if ($env:OS -ne "Windows_NT") {
    throw "This installer is for Windows."
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

function Refresh-ProcessPath {
    $machinePath = [Environment]::GetEnvironmentVariable("Path", "Machine")
    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    $env:Path = "$machinePath;$userPath"
}

function Find-Executable {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string[]]$Roots
    )
    $command = Get-Command $Name -ErrorAction SilentlyContinue
    if ($null -ne $command) {
        return $command.Source
    }
    foreach ($root in $Roots) {
        if (Test-Path $root) {
            $match = Get-ChildItem -Path $root -Filter $Name -File -Recurse -ErrorAction SilentlyContinue |
                Select-Object -First 1
            if ($null -ne $match) {
                return $match.FullName
            }
        }
    }
    return $null
}

function Install-WingetPackage {
    param([Parameter(Mandatory = $true)][string]$PackageId)
    $winget = Get-Command winget -ErrorAction SilentlyContinue
    if ($null -eq $winget) {
        throw "winget is required to install $PackageId."
    }
    Invoke-Checked -FilePath $winget.Source -Arguments @(
        "install", "--id", $PackageId, "--exact",
        "--accept-package-agreements", "--accept-source-agreements"
    )
    Refresh-ProcessPath
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

$PythonExe = Find-Python311
if ($null -eq $PythonExe) {
    Install-WingetPackage -PackageId "Python.Python.3.11"
    $PythonExe = Find-Python311
    if ($null -eq $PythonExe) {
        throw "Python 3.11 was installed but not found. Open a new PowerShell window and rerun this script."
    }
}

$searchRoots = @(
    $env:ProgramFiles,
    ${env:ProgramFiles(x86)},
    (Join-Path $env:LOCALAPPDATA "Programs")
)
$GitExe = Find-Executable -Name "git.exe" -Roots $searchRoots
if ($null -eq $GitExe) {
    Install-WingetPackage -PackageId "Git.Git"
    $GitExe = Find-Executable -Name "git.exe" -Roots $searchRoots
}
$CompilerExe = Find-Executable -Name "arm-none-eabi-gcc.exe" -Roots $searchRoots
if ($null -eq $CompilerExe) {
    Install-WingetPackage -PackageId "Arm.GnuArmEmbeddedToolchain"
    $CompilerExe = Find-Executable -Name "arm-none-eabi-gcc.exe" -Roots $searchRoots
}
$MakeExe = Find-Executable -Name "make.exe" -Roots $searchRoots
if ($null -eq $MakeExe) {
    Install-WingetPackage -PackageId "GnuWin32.Make"
    $MakeExe = Find-Executable -Name "make.exe" -Roots $searchRoots
}
$BashExe = $null
if ($null -ne $GitExe) {
    $gitRoot = Split-Path -Parent (Split-Path -Parent $GitExe)
    $candidateBash = Join-Path $gitRoot "bin\bash.exe"
    if (Test-Path $candidateBash) {
        $BashExe = $candidateBash
    }
}
if ($null -eq $BashExe) {
    $BashExe = Find-Executable -Name "bash.exe" -Roots $searchRoots
}
foreach ($tool in @($GitExe, $CompilerExe, $MakeExe, $BashExe)) {
    if ($null -eq $tool) {
        throw "Git, Git Bash, GNU Make, and arm-none-eabi-gcc are required."
    }
    $toolDir = Split-Path -Parent $tool
    if (($env:Path -split ";") -notcontains $toolDir) {
        $env:Path = "$toolDir;$env:Path"
    }
}

Invoke-Checked -FilePath $GitExe -Arguments @("config", "--global", "core.longpaths", "true")
$NewClone = $false
if (-not (Test-Path $OfficialRoot)) {
    New-Item -ItemType Directory -Path (Split-Path -Parent $OfficialRoot) -Force | Out-Null
    Invoke-Checked -FilePath $GitExe -Arguments @("clone", "--recursive", $CwUrl, $OfficialRoot)
    Invoke-Checked -FilePath $GitExe -Arguments @("-C", $OfficialRoot, "checkout", "--detach", $CwCommit)
    $NewClone = $true
} elseif (-not (Test-Path (Join-Path $OfficialRoot ".git"))) {
    throw "Install path exists but is not a Git repository: $OfficialRoot"
} else {
    $currentCommit = (& $GitExe -C $OfficialRoot rev-parse HEAD).Trim()
    if ($LASTEXITCODE -ne 0 -or $currentCommit -ne $CwCommit) {
        throw "Existing clone is not at the verified commit: $OfficialRoot"
    }
}
if (-not $NewClone) {
    $localChanges = & $GitExe -C $OfficialRoot status --porcelain --ignore-submodules=none
    if ($LASTEXITCODE -ne 0 -or $localChanges) {
        throw "Official clone has local changes; refusing to modify it: $OfficialRoot"
    }
}
Invoke-Checked -FilePath $GitExe -Arguments @("-C", $OfficialRoot, "submodule", "sync", "--recursive")
Invoke-Checked -FilePath $GitExe -Arguments @("-C", $OfficialRoot, "submodule", "update", "--init", "--recursive")
$actualJupyterCommit = (& $GitExe -C (Join-Path $OfficialRoot "jupyter") rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0 -or $actualJupyterCommit -ne $JupyterCommit) {
    throw "Jupyter submodule is not at the verified commit."
}
$GeneratedNotebook = "courses/sca101/SOLN_Lab 2_1B - Power Analysis for Password Bypass - CWLITEARM.ipynb"
$JupyterRoot = Join-Path $OfficialRoot "jupyter"
$JupyterExclude = (& $GitExe -C $JupyterRoot rev-parse --git-path info/exclude).Trim()
if (-not [System.IO.Path]::IsPathRooted($JupyterExclude)) {
    $JupyterExclude = [System.IO.Path]::GetFullPath((Join-Path $JupyterRoot $JupyterExclude))
}
if (-not (Select-String -Path $JupyterExclude -SimpleMatch $GeneratedNotebook -Quiet)) {
    Add-Content -Path $JupyterExclude -Value "`n$GeneratedNotebook"
}
$localChanges = & $GitExe -C $OfficialRoot status --porcelain --ignore-submodules=none
if ($LASTEXITCODE -ne 0 -or $localChanges) {
    throw "Official clone is not clean after submodule setup: $OfficialRoot"
}

$VenvDir = Join-Path $OfficialRoot ".venv"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    Invoke-Checked -FilePath $PythonExe -Arguments @("-m", "venv", $VenvDir)
}
Invoke-Checked -FilePath $VenvPython -Arguments @(
    "-c", "import sys; assert sys.version_info[:2] == (3, 11), 'Remove .venv and rerun with Python 3.11'"
)
Invoke-Checked -FilePath $VenvPython -Arguments @("-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel")
Invoke-Checked -FilePath $VenvPython -Arguments @("-m", "pip", "install", "--editable", $OfficialRoot)
Invoke-Checked -FilePath $VenvPython -Arguments @(
    "-m", "pip", "install", "--requirement", (Join-Path $OfficialRoot "jupyter\requirements.txt"), "jupyterlab"
)
Invoke-Checked -FilePath $VenvPython -Arguments @(
    (Join-Path $InstallerRoot "scripts\prepare_official_f303.py"), $OfficialRoot
)

Invoke-Checked -FilePath $MakeExe -Arguments @(
    "-C", (Join-Path $OfficialRoot "firmware\mcu\basic-passwdcheck"),
    "PLATFORM=CWLITEARM", "CRYPTO_TARGET=NONE", "SS_VER=SS_VER_2_1", "-j"
)
Invoke-Checked -FilePath $MakeExe -Arguments @(
    "-C", (Join-Path $OfficialRoot "firmware\mcu\simpleserial-aes"),
    "PLATFORM=CWLITEARM", "CRYPTO_TARGET=TINYAES128C", "SS_VER=SS_VER_2_1", "-j"
)

Invoke-Checked -FilePath $VenvPython -Arguments @(
    "-m", "ipykernel", "install", "--user",
    "--name", "chipwhisperer-official-f303",
    "--display-name", "Python (Official ChipWhisperer, F303)",
    "--env", "PATH", $env:Path
)

$JupyterLab = Join-Path $VenvDir "Scripts\jupyter-lab.exe"
Write-Host ""
Write-Host "Setup complete. Modern ChipWhisperer-Lite firmware uses WinUSB."
Write-Host "Start the official notebooks with:"
Write-Host "  & `"$JupyterLab`" --ServerApp.root_dir=`"$(Join-Path $OfficialRoot 'jupyter')`""
