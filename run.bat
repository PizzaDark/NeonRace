@echo off
chcp 65001 >nul
title NeonRace - Auto Install Script
color 0A

:: ============================================
:: Project Configuration
:: ============================================
set "PROJECT_NAME=NeonRace"
set "GITHUB_USER=PizzaDark"
set "GITHUB_REPO=%PROJECT_NAME%"
set "REPO_URL=https://github.com/%GITHUB_USER%/%GITHUB_REPO%.git"
set "REPO_ZIP_URL=https://github.com/%GITHUB_USER%/%GITHUB_REPO%/archive/refs/heads/main.zip"
set "REPO_DIR=%PROJECT_NAME%"

echo ========================================
echo   Auto Install Script
echo ========================================
echo.

:: ============================================
:: Step 1: Check Python 3.10+ environment
:: ============================================
echo [1/5] Checking Python environment...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed!
    echo.
    echo Please download and install Python 3.10 or higher (Ctrl+click or copy to browser):
    echo https://www.python.org/downloads/
    echo.
    echo Make sure to check "Add Python to PATH" during installation!
    echo.
    pause
    exit /b 1
)

:: Get Python version
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo Detected Python version: %PYTHON_VERSION%

:: Check if version meets requirements (3.10+)
for /f "tokens=1,2 delims=." %%a in ("%PYTHON_VERSION%") do (
    set MAJOR=%%a
    set MINOR=%%b
)

if %MAJOR% LSS 3 (
    goto :version_error
)
if %MAJOR% EQU 3 if %MINOR% LSS 10 (
    goto :version_error
)

echo [OK] Python version meets requirements (3.10+ needed)
echo.
goto :check_git

:version_error
echo [ERROR] Python version too old! Current: %PYTHON_VERSION%, required: 3.10 or higher
echo.
echo Please download Python 3.10 or higher (Ctrl+click or copy to browser):
echo https://www.python.org/downloads/
echo.
pause
exit /b 1

:: ============================================
:: Step 2: Check Git environment
:: ============================================
:check_git
echo [2/5] Checking Git environment...
git --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Git is not installed
    echo.
    echo You can:
    echo 1. Manually download the ZIP from GitHub and extract it (Ctrl+click or copy to browser):
    echo    Download: %REPO_ZIP_URL%
    echo.
    echo 2. Or install Git and re-run this script (Ctrl+click or copy to browser):
    echo    Git download: https://git-scm.com/install
    echo.
    echo If you have already downloaded and extracted the source code, press any key to continue...
    pause
    goto :setup_venv
) else (
    echo [OK] Git is available
    echo.
    
    :: Check if current directory name matches the project name
    for %%I in (.) do set CURRENT_DIR=%%~nxI
    if "%CURRENT_DIR%"=="%PROJECT_NAME%" (
        echo [INFO] Already inside the project directory, skipping clone
        echo.
        goto :setup_venv
    )
    
    :: Check if already a Git repository or project files exist
    if exist ".git" (
        echo [INFO] Existing Git repository detected, skipping clone
        echo.
        goto :setup_venv
    ) else if exist "main.py" (
        echo [INFO] Existing project files detected, skipping clone
        echo.
        goto :setup_venv
    ) else (
        goto :clone_repo
    )
)
goto :setup_venv

:: ============================================
:: Clone repository (with retry)
:: ============================================
:clone_repo
set RETRIES=3
set COUNT=0

:clone_try
set /a COUNT+=1
echo Attempting to clone repository (try %COUNT%/%RETRIES%)...
git clone "%REPO_URL%"
if %errorlevel% equ 0 (
    echo [OK] Clone successful
    goto :enter_project_dir
) else (
    echo [WARNING] Clone attempt %COUNT% failed.
    if %COUNT% lss %RETRIES% (
        echo Retrying in 2 seconds...
        timeout /t 2 >nul
        goto :clone_try
    ) else (
        echo.
        echo [INFO] Git clone failed, attempting to download ZIP via curl...
        goto :download_zip
    )
)

:: ============================================
:: Download and extract ZIP (fallback if clone fails)
:: ============================================
:download_zip
echo.
echo Downloading project archive...
curl -L -o project.zip "%REPO_ZIP_URL%"
if %errorlevel% neq 0 (
    echo [ERROR] Download failed!
    echo.
    echo Please manually download the ZIP and extract it:
    echo %REPO_ZIP_URL%
    echo.
    pause
    exit /b 1
)

echo [OK] Download successful, extracting...
tar -xf project.zip
if %errorlevel% neq 0 (
    echo [ERROR] Extraction failed! Please manually extract project.zip.
    pause
    exit /b 1
)

echo [OK] Extraction successful, renaming folder...
:: GitHub ZIP folders are usually named REPO-main or REPO-master
if exist "%PROJECT_NAME%-main" (
    ren "%PROJECT_NAME%-main" "%PROJECT_NAME%"
) else if exist "%PROJECT_NAME%-master" (
    ren "%PROJECT_NAME%-master" "%PROJECT_NAME%"
)

echo [OK] Cleaning up temporary files...
del /f /q project.zip

echo [OK] Project download and extraction complete
goto :enter_project_dir

:: ============================================
:: Enter project directory
:: ============================================
:enter_project_dir
if exist "%REPO_DIR%\main.py" (
    pushd "%REPO_DIR%"
    if %errorlevel% equ 0 (
        echo.
        echo [OK] Entered project directory: %REPO_DIR%
        echo.
        goto :setup_venv
    ) else (
        echo [WARNING] Could not enter project directory, checking files in current directory.
        goto :setup_venv
    )
) else if exist "%REPO_DIR%" (
    echo [INFO] main.py is missing from the project folder, please re-download the project.
    pause
    exit /b 1
) else (
    echo [INFO] Expected project directory not found, please re-download the project.
    pause
    exit /b 1
)

:: ============================================
:: Step 3: Create virtual environment
:: ============================================
:setup_venv
echo [3/5] Checking/creating virtual environment...
if exist ".venv\" (
    echo [INFO] Existing virtual environment detected
) else (
    echo Creating virtual environment...
    python -m venv .venv
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create virtual environment!
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created
)
echo.

:: ============================================
:: Step 4: Activate virtual environment
:: ============================================
echo [4/5] Activating virtual environment...
call .venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo [ERROR] Failed to activate virtual environment!
    pause
    exit /b 1
)
echo [OK] Virtual environment activated
echo.

:: ============================================
:: Step 5: Install dependencies
:: ============================================
echo [5/5] Installing/updating dependencies...
if not exist "requirements.txt" (
    echo [WARNING] requirements.txt not found!
    echo Attempting to run the program directly...
    echo.
    goto :run_program
)

echo Installing dependencies via Aliyun mirror, please wait...
pip install pip -i https://mirrors.aliyun.com/pypi/simple/ >nul 2>&1
pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/
if %errorlevel% neq 0 (
    echo [ERROR] Dependency installation failed!
    echo.
    echo You can try running manually:
    echo pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/
    echo.
    pause
    exit /b 1
)
echo [OK] Dependencies installed
echo.

:: ============================================
:: Run main program
:: ============================================
:run_program
echo ========================================
echo   Environment ready, launching program...
echo ========================================
echo.

if not exist "main.py" (
    echo [ERROR] main.py not found!
    echo.
    echo Please make sure you are running this script from the correct project directory.
    echo.
    pause
    exit /b 1
)

python main.py

:: Post-exit handling
echo.
echo ========================================
echo   Program has exited
echo ========================================

:: Restore original directory if pushd was used
popd 2>nul

pause
