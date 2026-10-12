@echo off
rem Batch files are read in the ANSI codepage, so keep this file pure ASCII.
rem Legacy conhost cannot render 256-color output, which hides the character
rem colors, so relaunch through Windows Terminal (or PowerShell) first.
rem The relaunch guard is an argument, not an env var: when wt is already
rem running, wt.exe only asks that process for a tab and our env never reaches it.
setlocal enabledelayedexpansion
cd /d "%~dp0"

if "%~1"=="/inner" goto STRIP

where wt >nul 2>nul
if not errorlevel 1 goto VIAWT
where powershell >nul 2>nul
if not errorlevel 1 goto VIAPS
set "PASS=%*"
goto RUN

:VIAWT
rem No -d here: "%~dp0" ends in a backslash, which wt reads as an escaped quote.
start "" wt.exe cmd /k "%~f0" /inner %*
exit /b

:VIAPS
start "" powershell -NoProfile -NoExit -Command "chcp 65001 > $null; Set-Location -LiteralPath '%~dp0'; cmd /c '%~f0' /inner %*"
exit /b

:STRIP
shift
set "PASS="
:COLLECT
if "%~1"=="" goto RUN
set "PASS=!PASS! %1"
shift
goto COLLECT

:RUN
chcp 65001 >nul
where py >nul 2>nul
if %errorlevel%==0 goto RUNPY
where python >nul 2>nul
if %errorlevel%==0 goto RUNPYTHON
echo Python not found.  winget install -e --id Python.Python.3.12
pause
exit /b 1
:RUNPY
py save_read.py --watch %PASS%
if errorlevel 1 pause
exit /b
:RUNPYTHON
python save_read.py --watch %PASS%
if errorlevel 1 pause
