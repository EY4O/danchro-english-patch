@echo off
rem Restores the original game files saved by install-windows.bat.
setlocal EnableDelayedExpansion
cd /d "%~dp0"
for %%I in ("%~dp0..") do set "GAME=%%~fI"
set "HERE=%~dp0"
set "HERE=%HERE:~0,-1%"
set "FAILED="
if not exist backup (
  echo No backup found - nothing to restore.
  pause & exit /b 1
)
for /f "usebackq tokens=1,2 delims=|" %%A in ("files-all.txt") do (
  set "REL=%%B" & set "REL=!REL:/=\!"
  for %%F in ("%GAME%\!REL!") do set "DIR=%%~dpF"
  if exist "backup\%%A" call :put "%HERE%\backup" "!DIR:~0,-1!" "%%A"
)
if defined FAILED (echo Some files could not be restored ^(see above^).) else (echo Original files restored.)
pause
exit /b 0

:put
copy /y "%~1\%~3" "%~2\%~3" >nul 2>&1 || (echo   Could not copy %~3 & set "FAILED=1")
exit /b 0
