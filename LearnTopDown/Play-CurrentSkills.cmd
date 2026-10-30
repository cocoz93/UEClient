@echo off
setlocal
set "SKILLS_PROJECT=%~dp0LearnTopDown.uproject"
set "SKILLS_EDITOR=C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Win64-DebugGame.exe"
set "SKILLS_MODULE=%~dp0Binaries\Win64\UnrealEditor-LearnTopDown-Win64-DebugGame.dll"

if not exist "%SKILLS_PROJECT%" goto missing_files
if not exist "%SKILLS_EDITOR%" goto missing_files
if not exist "%SKILLS_MODULE%" goto missing_files
if /i "%~1"=="--check" (
    echo Project: "%SKILLS_PROJECT%"
    echo Module: "%SKILLS_MODULE%"
    exit /b 0
)

set "UE-LocalDataCachePath=%~dp0Saved\CharacterPipelineDDC"
start "" "%SKILLS_EDITOR%" "%SKILLS_PROJECT%" /Game/TopDown/TrainingRoom/Maps/Lvl_DarkTrainingRoom -game -windowed -ResX=1600 -ResY=900 -NoLiveCoding -nosplash -ddc=InstalledNoZenLocalFallback -abslog="%~dp0Saved\Logs\CurrentSkillsReview.log"
exit /b %errorlevel%

:missing_files
echo The current skill review build or Unreal Engine 5.8 is missing.
if /i not "%~1"=="--check" pause
exit /b 1
