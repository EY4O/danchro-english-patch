@echo off
rem DanChro English Patch installer (Windows). Put this folder inside the game folder (next to danchro.exe).
setlocal EnableDelayedExpansion
cd /d "%~dp0"
rem absolute game folder without "..", which keeps paths well under Windows' 260-character limit
for %%I in ("%~dp0..") do set "GAME=%%~fI"
set "HERE=%~dp0"
set "HERE=%HERE:~0,-1%"
set "FAILED="
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
echo   2 = Translation only: English text and images, gameplay unchanged
choice /c 12 /n /m "Press 1 or 2: "
if errorlevel 2 (set "LIST=files-translation.txt") else (set "LIST=files-full.txt")
if not exist backup (
  mkdir backup
  for /f "usebackq tokens=1,2 delims=|" %%A in ("files-all.txt") do (
    set "REL=%%B" & set "REL=!REL:/=\!"
    for %%F in ("%GAME%\!REL!") do set "DIR=%%~dpF"
    call :put "!DIR:~0,-1!" "%HERE%\backup" "%%A"
  )
  if defined FAILED (
    rmdir /s /q backup
    echo Backup failed, nothing was changed. Try moving the game to a shorter folder path.
    pause & exit /b 1
  )
  echo Backed up original files to %HERE%\backup
)
rem start from the originals so switching versions leaves nothing behind
for /f "usebackq tokens=1,2 delims=|" %%A in ("files-all.txt") do (
  set "REL=%%B" & set "REL=!REL:/=\!"
  for %%F in ("%GAME%\!REL!") do set "DIR=%%~dpF"
  call :put "%HERE%\backup" "!DIR:~0,-1!" "%%A"
)
for /f "usebackq tokens=1,2 delims=|" %%A in ("!LIST!") do (
  set "SRC=%%A" & set "SRC=!SRC:/=\!"
  set "REL=%%B" & set "REL=!REL:/=\!"
  for %%S in ("%HERE%\!SRC!") do set "SDIR=%%~dpS"
  for %%F in ("%GAME%\!REL!") do set "DIR=%%~dpF"
  for %%N in ("!REL!") do set "NAME=%%~nxN"
  call :put "!SDIR:~0,-1!" "!DIR:~0,-1!" "!NAME!"
)
if defined FAILED (
  echo Some files could not be copied ^(see above^). Try moving the game to a shorter folder path, then run this again.
) else (
  echo English patch installed. Start the game as usual.
)
pause
exit /b 0

:put
rem %1 source folder, %2 destination folder, %3 file name (the same at both ends)
copy /y "%~1\%~3" "%~2\%~3" >nul 2>&1 || (echo   Could not copy %~3 & set "FAILED=1")
exit /b 0
