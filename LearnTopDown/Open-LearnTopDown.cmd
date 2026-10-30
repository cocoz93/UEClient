@echo off
setlocal
set "COUNTESS_PROJECT=%~dp0LearnTopDown.uproject"
set "COUNTESS_EDITOR=C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe"

if not exist "%COUNTESS_PROJECT%" goto missing_project
if not exist "%COUNTESS_EDITOR%" goto missing_editor
if /i "%~1"=="--check" (
    echo Editor: "%COUNTESS_EDITOR%"
    echo Project: "%COUNTESS_PROJECT%"
    exit /b 0
)

start "" "%COUNTESS_EDITOR%" "%COUNTESS_PROJECT%"
exit /b %errorlevel%

:missing_project
echo LearnTopDown.uproject was not found next to this launcher.
if /i not "%~1"=="--check" pause
exit /b 1

:missing_editor
echo Unreal Engine 5.8 was not found at "%COUNTESS_EDITOR%".
if /i not "%~1"=="--check" pause
exit /b 1
