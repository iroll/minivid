@echo off
setlocal

pushd "%~dp0" || exit /b 1
python3 "%~dp0minivid.py" %*
if errorlevel 1 pause
popd
