@echo off
rem DanChro English Patch installer (Windows). Put this folder inside the game folder (next to danchro.exe).
setlocal EnableDelayedExpansion
cd /d "%~dp0"
set "GAME=%~dp0.."
if not exist "%GAME%\danchro.exe" (
  echo Could not find danchro.exe. Put the DanChro-English-Patch folder inside the game folder and try again.
  pause & exit /b 1
)
for /f "usebackq tokens=1,2 delims=|" %%A in ("files-all.txt") do (
  set "REL=%%B" & set "REL=!REL:/=\!"
  if not exist "%GAME%\!REL!" (
    echo This patch is for a different game version: !REL! not found.
    pause & exit /b 1
  )
)
echo Which version do you want?
echo   1 = Full patch: English + fairer gacha, more crystals, less grind, smarter auto-battle, higher detail
echo   2 = Translation only: English text and tutorial images, gameplay unchanged
choice /c 12 /n /m "Press 1 or 2: "
if errorlevel 2 (set "LIST=files-translation.txt") else (set "LIST=files-full.txt")
if not exist backup (
  mkdir backup
  for /f "usebackq tokens=1,2 delims=|" %%A in ("files-all.txt") do (
    set "REL=%%B" & set "REL=!REL:/=\!"
    copy /y "%GAME%\!REL!" "backup\%%A" >nul
  )
  echo Backed up original files to %~dp0backup
)
rem start from the originals so switching versions leaves nothing behind
for /f "usebackq tokens=1,2 delims=|" %%A in ("files-all.txt") do (
  set "REL=%%B" & set "REL=!REL:/=\!"
  copy /y "backup\%%A" "%GAME%\!REL!" >nul
)
for /f "usebackq tokens=1,2 delims=|" %%A in ("!LIST!") do (
  set "SRC=%%A" & set "SRC=!SRC:/=\!"
  set "REL=%%B" & set "REL=!REL:/=\!"
  copy /y "!SRC!" "%GAME%\!REL!" >nul
)
echo English patch installed. Start the game as usual.
pause
