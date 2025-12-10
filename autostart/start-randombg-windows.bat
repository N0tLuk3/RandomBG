@echo off
setlocal

:: Root-Ordner des Projekts
set "APP_DIR=C:\RandomBG"
set "VENV_DIR=%APP_DIR%\.venv"
set "PYTHONW=%VENV_DIR%\Scripts\pythonw.exe"

:: Falls ein virtuelles Environment existiert, verwende dessen pythonw.exe, sonst das System-Python
if exist "%PYTHONW%" (
    set "RUNNER=%PYTHONW%"
) else (
    set "RUNNER=pythonw.exe"
)

pushd "%APP_DIR%"
start "RandomBG" "%RUNNER%" -m random_bg.app
popd

endlocal
