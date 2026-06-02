@echo off
setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
set "HOST_SCRIPT=%SCRIPT_DIR%bbb-merge-host.bat"
set "HOST_NAME=com.bbb.merge"
set "EXTENSION_ID=%~1"

if "%EXTENSION_ID%"=="" (
  echo.
  echo === BBB Merge - Native Host Installation ===
  echo.
  echo To find your Extension ID:
  echo   1. Go to chrome://extensions
  echo   2. Enable Developer mode
  echo   3. Load the bbb-merge-extension folder (unpacked)
  echo   4. Copy the ID shown under the extension name
  echo.
  set /p EXTENSION_ID="Enter Chrome Extension ID: "
)

if "%EXTENSION_ID%"=="" (
  echo Error: Extension ID is required.
  exit /b 1
)

set "HOST_DIR=%LOCALAPPDATA%\Google\Chrome\User Data\NativeMessagingHosts"

if not exist "%HOST_DIR%" (
  mkdir "%HOST_DIR%"
)

(
  echo {
  echo   "name": "com.bbb.merge",
  echo   "description": "BBB Merge - Native host for merging BBB recording videos",
  echo   "path": "%HOST_SCRIPT:\=\\%",
  echo   "type": "stdio",
  echo   "allowed_origins": ["chrome-extension://%EXTENSION_ID%/"]
  echo }
) > "%HOST_DIR%\%HOST_NAME%.json"

echo Installed: %HOST_DIR%\%HOST_NAME%.json

echo.
echo === Installation complete ===
echo.
echo Make sure you have ffmpeg installed:
echo   winget install ffmpeg
echo.
echo Then reload the extension in chrome://extensions
echo.
pause
