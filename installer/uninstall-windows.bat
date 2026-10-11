@echo off
rem Restores the original game files saved by install-windows.bat.
setlocal EnableDelayedExpansion
cd /d "%~dp0"
set "GAME=%~dp0.."
if not exist backup (
  echo No backup found - nothing to restore.
  pause & exit /b 1
)
for /f "usebackq tokens=1,2 delims=|" %%A in ("files-all.txt") do (
  set "REL=%%B" & set "REL=!REL:/=\!"
  if exist "backup\%%A" copy /y "backup\%%A" "%GAME%\!REL!" >nul
)
echo Original files restored.
pause
