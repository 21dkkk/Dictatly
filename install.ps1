# Dictatly Automated PowerShell Installer
# Installs Dictatly with one command:
#   irm https://raw.githubusercontent.com/21dkkk/Dictatly/main/install.ps1 | iex

[CmdletBinding()]
param(
    [string]$InstallDir = (Join-Path $env:LOCALAPPDATA "Dictatly"),
    [string]$Model = "large-v3-turbo",
    [switch]$SkipModel,
    [switch]$NonInteractive
)

[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message, [string]$Step = "")
    if ($Step) {
        Write-Host "`n[$Step] $Message" -ForegroundColor Cyan
    } else {
        Write-Host $Message -ForegroundColor Green
    }
}

function Write-Notice {
    param([string]$Message)
    Write-Host " -> $Message" -ForegroundColor Gray
}

function Write-Warn {
    param([string]$Message)
    Write-Host " [!] $Message" -ForegroundColor Yellow
}

Write-Host @"
============================================================
              Dictatly - Automated Setup
   Fast, private, local speech dictation for Windows
============================================================
"@ -ForegroundColor Cyan

# 1. Terminate running instances
Write-Step "Checking for running Dictatly instances..." "1/6"
$existingProcesses = Get-Process -Name "Dictatly", "pythonw" -ErrorAction SilentlyContinue | Where-Object {
    try { $_.Path -like "*$InstallDir*" } catch { $false }
}
if ($existingProcesses) {
    Write-Notice "Stopping previous Dictatly instance..."
    $existingProcesses | Stop-Process -Force
    Start-Sleep -Seconds 1
}

# 2. Check / Install Python (>= 3.10)
Write-Step "Verifying Python 3.10+ runtime..." "2/6"

function Find-PythonExecutable {
    $candidates = @("python", "py", "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe", "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe", "$env:ProgramFiles\Python312\python.exe", "$env:ProgramFiles\Python311\python.exe")
    foreach ($cmd in $candidates) {
        try {
            $ver = & $cmd -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
            if ($ver) {
                $major, $minor = $ver.Trim().Split('.')
                if ([int]$major -ge 3 -and [int]$minor -ge 10) {
                    return $cmd
                }
            }
        } catch {}
    }
    return $null
}

$pythonCmd = Find-PythonExecutable

if (-not $pythonCmd) {
    Write-Warn "Python 3.10+ not detected on system. Initiating automatic setup..."
    $hasWinget = Get-Command "winget" -ErrorAction SilentlyContinue
    if ($hasWinget) {
        Write-Notice "Installing Python 3.12 via Windows Package Manager (winget)..."
        & winget install --id Python.Python.3.12 -e --accept-package-agreements --accept-source-agreements --silent
    } else {
        Write-Notice "Downloading official Python 3.12 installer..."
        $pyUrl = "https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe"
        $pyInstaller = Join-Path $env:TEMP "python-3.12.8-installer.exe"
        Invoke-WebRequest -Uri $pyUrl -OutFile $pyInstaller -UseBasicParsing
        Write-Notice "Installing Python 3.12 silently..."
        Start-Process -FilePath $pyInstaller -ArgumentList "/quiet InstallAllUsers=0 PrependPath=1 Include_test=0" -Wait
        Remove-Item $pyInstaller -Force -ErrorAction SilentlyContinue
    }

    # Refresh PATH in current process
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
    $pythonCmd = Find-PythonExecutable

    if (-not $pythonCmd) {
        throw "Failed to locate Python after installation. Please install Python 3.11+ manually from https://python.org and restart your terminal."
    }
}

Write-Notice "Using Python: $pythonCmd"

# 3. Download & Extract Dictatly
Write-Step "Downloading latest application files..." "3/6"
New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null

$zipUrl = "https://github.com/21dkkk/Dictatly/archive/refs/heads/main.zip"
$zipFile = Join-Path $env:TEMP "Dictatly-main.zip"
$extractTemp = Join-Path $env:TEMP "Dictatly-extract-$([Guid]::NewGuid().ToString().Substring(0,8))"

Write-Notice "Fetching repository archive..."
Invoke-WebRequest -Uri $zipUrl -OutFile $zipFile -UseBasicParsing

Write-Notice "Extracting files to $InstallDir..."
Expand-Archive -Path $zipFile -DestinationPath $extractTemp -Force
$innerDir = Join-Path $extractTemp "Dictatly-main"

# Copy files preserving local changes / venv if existing
Get-ChildItem -Path $innerDir -Recurse | ForEach-Object {
    $rel = $_.FullName.Substring($innerDir.Length + 1)
    $dest = Join-Path $InstallDir $rel
    if ($_.PSIsContainer) {
        if (-not (Test-Path $dest)) { New-Item -ItemType Directory -Path $dest -Force | Out-Null }
    } else {
        Copy-Item -Path $_.FullName -Destination $dest -Force
    }
}

Remove-Item -Path $zipFile, $extractTemp -Recurse -Force -ErrorAction SilentlyContinue

# 4. Configure Virtual Environment & Dependencies
Write-Step "Configuring Python virtual environment & dependencies..." "4/6"
$venvDir = Join-Path $InstallDir "venv"
$venvPython = Join-Path $venvDir "Scripts\python.exe"
$venvPip = Join-Path $venvDir "Scripts\pip.exe"

if (-not (Test-Path $venvPython)) {
    Write-Notice "Creating isolated venv..."
    & $pythonCmd -m venv $venvDir
}

Write-Notice "Upgrading pip..."
& $venvPython -m pip install --upgrade pip --quiet

Write-Notice "Installing PySide6, Faster-Whisper, PyWin32..."
& $venvPip install -r (Join-Path $InstallDir "requirements.txt") --quiet

# Compile native C# launcher
$launcherExe = Join-Path $InstallDir "Dictatly.exe"
Write-Notice "Compiling native Windows launcher (Dictatly.exe)..."
& $venvPython (Join-Path $InstallDir "scripts\build_launcher.py")

# 5. Pre-cache Whisper Speech Model
Write-Step "Checking Whisper speech recognition model..." "5/6"
if ($SkipModel) {
    Write-Notice "Skipping model download (-SkipModel flag specified). Model will download on first dictation."
} else {
    Write-Notice "Pre-caching model '$Model' for offline use (this might take a few moments)..."
    $cacheScript = "from faster_whisper import WhisperModel; print('Loading model $Model...'); WhisperModel('$Model')"
    & $venvPython -c $cacheScript
    Write-Notice "Model ready for instant transcription."
}

# 6. Shortcuts creation
Write-Step "Creating Desktop and Start Menu shortcuts..." "6/6"
$wsh = New-Object -ComObject WScript.Shell

$icoPath = Join-Path $InstallDir "resources\app_icon.ico"
if (-not (Test-Path $icoPath)) {
    $icoPath = Join-Path $InstallDir "resources\app_icon_64.png"
}

# Desktop Shortcut
$desktopPath = [System.Environment]::GetFolderPath("Desktop")
$desktopShortcut = $wsh.CreateShortcut((Join-Path $desktopPath "Dictatly.lnk"))
$desktopShortcut.TargetPath = (Join-Path $InstallDir "Dictatly.exe")
$desktopShortcut.WorkingDirectory = $InstallDir
$desktopShortcut.IconLocation = "$icoPath,0"
$desktopShortcut.Description = "Dictatly - Local Speech Dictation"
$desktopShortcut.Save()

# Start Menu Shortcut
$programsPath = [System.Environment]::GetFolderPath("Programs")
$startMenuShortcut = $wsh.CreateShortcut((Join-Path $programsPath "Dictatly.lnk"))
$startMenuShortcut.TargetPath = (Join-Path $InstallDir "Dictatly.exe")
$startMenuShortcut.WorkingDirectory = $InstallDir
$startMenuShortcut.IconLocation = "$icoPath,0"
$startMenuShortcut.Description = "Dictatly - Local Speech Dictation"
$startMenuShortcut.Save()

Write-Notice "Created shortcuts on Desktop and in Start Menu."

Write-Host @"

============================================================
           Dictatly successfully installed!
============================================================
  • Installation Directory: $InstallDir
  • Hotkey: Press [Right Ctrl] anywhere to speak
  • Settings & History: Available from the system tray
============================================================
"@ -ForegroundColor Green

if (-not $NonInteractive) {
    $response = Read-Host "Запустить Dictatly прямо сейчас? / Launch Dictatly now? [Y/n]"
    if ($response -eq "" -or $response -match "^[yYдД]") {
        Start-Process (Join-Path $InstallDir "Dictatly.exe")
    }
}
