@echo off
REM ================================================================
REM   AChat Exporter — Windows Installer
REM   Requires: Python 3.8+, internet connection
REM
REM   Run as normal user (no admin needed)
REM ================================================================

setlocal enabledelayedexpansion

set VERSION=1.0.0
set REPO=RAVENBHAI-81/AChat-Exporter
set RELEASE_URL=https://github.com/%REPO%/releases/latest/download/achat.py
set RAW_URL=https://raw.githubusercontent.com/%REPO%/main/achat.py
set INSTALL_DIR=%USERPROFILE%\.local\bin
set DEST=%INSTALL_DIR%\achat.py
set ACHAT_DIR=%USERPROFILE%\AChat

echo.
echo   ============================================================
echo    AChat Exporter  v%VERSION%  --  by Raven RX
echo    Windows Installer
echo   ============================================================
echo.

REM ── Check Python ──────────────────────────────────────────────
echo   . Checking Python 3...
python --version >nul 2>&1
if errorlevel 1 (
    python3 --version >nul 2>&1
    if errorlevel 1 (
        echo.
        echo   [!] Python 3 not found.
        echo       Download from: https://www.python.org/downloads/
        echo       Make sure to check "Add Python to PATH" during install.
        echo.
        pause
        exit /b 1
    )
    set PYTHON=python3
) else (
    set PYTHON=python
)

for /f "tokens=*" %%v in ('!PYTHON! --version 2^>^&1') do (
    echo   [OK] %%v
)

REM ── Optional: cloudscraper ────────────────────────────────────
echo.
echo   . Checking optional: cloudscraper (for Claude export)...
!PYTHON! -c "import cloudscraper" >nul 2>&1
if errorlevel 1 (
    echo   [!] cloudscraper not installed.
    echo       Install with:  pip install cloudscraper
    echo       Claude exports will be unavailable without it.
) else (
    echo   [OK] cloudscraper installed
)

REM ── Create install directory ──────────────────────────────────
echo.
echo   . Creating install directory: %INSTALL_DIR%
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

REM ── Create AChat data folders ─────────────────────────────────
echo   . Creating data folder: %ACHAT_DIR%
if not exist "%ACHAT_DIR%\exports\deepseek" mkdir "%ACHAT_DIR%\exports\deepseek"
if not exist "%ACHAT_DIR%\exports\grok"     mkdir "%ACHAT_DIR%\exports\grok"
if not exist "%ACHAT_DIR%\exports\chatgpt"  mkdir "%ACHAT_DIR%\exports\chatgpt"
if not exist "%ACHAT_DIR%\exports\claude"   mkdir "%ACHAT_DIR%\exports\claude"
if not exist "%ACHAT_DIR%\search_index"     mkdir "%ACHAT_DIR%\search_index"
echo   [OK] Data folder ready

REM ── Download achat.py ─────────────────────────────────────────
echo.
echo   . Downloading achat.py from GitHub...
set DOWNLOAD_OK=0

REM Try PowerShell (available on Win7+)
where powershell >nul 2>&1
if not errorlevel 1 (
    powershell -Command "& { $ProgressPreference='SilentlyContinue'; try { Invoke-WebRequest -Uri '%RELEASE_URL%' -OutFile '%DEST%.tmp' -UseBasicParsing -TimeoutSec 30; exit 0 } catch { try { Invoke-WebRequest -Uri '%RAW_URL%' -OutFile '%DEST%.tmp' -UseBasicParsing -TimeoutSec 30; exit 0 } catch { exit 1 } } }" >nul 2>&1
    if not errorlevel 1 (
        set DOWNLOAD_OK=1
        echo   [OK] Downloaded via PowerShell
    )
)

REM Fallback: curl (available on Win10 1803+)
if !DOWNLOAD_OK!==0 (
    where curl >nul 2>&1
    if not errorlevel 1 (
        curl -fsSL --max-time 30 -o "%DEST%.tmp" "%RELEASE_URL%" >nul 2>&1
        if not errorlevel 1 (
            set DOWNLOAD_OK=1
            echo   [OK] Downloaded via curl
        ) else (
            curl -fsSL --max-time 30 -o "%DEST%.tmp" "%RAW_URL%" >nul 2>&1
            if not errorlevel 1 (
                set DOWNLOAD_OK=1
                echo   [OK] Downloaded via curl (main branch)
            )
        )
    )
)

if !DOWNLOAD_OK!==0 (
    echo.
    echo   [!] Download failed.
    echo       Please download achat.py manually from:
    echo       https://github.com/%REPO%/releases/latest
    echo       and save it as: %DEST%
    echo.
    pause
    exit /b 1
)

REM Validate Python syntax
!PYTHON! -c "import ast; ast.parse(open(r'%DEST%.tmp').read())" >nul 2>&1
if errorlevel 1 (
    del "%DEST%.tmp" >nul 2>&1
    echo   [!] Downloaded file is not valid Python. Try again.
    pause
    exit /b 1
)

move /y "%DEST%.tmp" "%DEST%" >nul
echo   [OK] Saved to %DEST%

REM ── Create achat.cmd wrapper ──────────────────────────────────
set WRAPPER=%INSTALL_DIR%\achat.cmd
echo @echo off > "%WRAPPER%"
echo python "%DEST%" %%* >> "%WRAPPER%"
echo   [OK] Created launcher: %WRAPPER%

REM ── Add to PATH ───────────────────────────────────────────────
echo.
echo   . Checking PATH...
echo %PATH% | find /i "%INSTALL_DIR%" >nul 2>&1
if errorlevel 1 (
    echo   [!] %INSTALL_DIR% is not in your PATH.
    echo.
    echo       Adding it for your user account now...
    setx PATH "%INSTALL_DIR%;%PATH%" >nul 2>&1
    if errorlevel 1 (
        echo   [!] Could not set PATH automatically.
        echo       Add this to your PATH manually:
        echo         %INSTALL_DIR%
    ) else (
        echo   [OK] Added to PATH (restart your terminal to apply)
    )
) else (
    echo   [OK] %INSTALL_DIR% is already in PATH
)

REM ── Done! ─────────────────────────────────────────────────────
echo.
echo   ============================================================
echo.
echo     AChat Exporter v%VERSION% installed!
echo.
echo     Run it with:  achat
echo     Or:           achat https://chat.deepseek.com/share/...
echo.
echo     GitHub: github.com/%REPO%
echo     by Raven RX - Founder of RX Network Security Labs
echo.
echo   ============================================================
echo.
pause
