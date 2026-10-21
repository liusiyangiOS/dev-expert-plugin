@echo off
setlocal
rem One-step Codex installation. Resolve files relative to this script.
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -ExecutionPolicy Bypass -File "%~dp0packages\codex\install.ps1"
set "expertExitCode=%ERRORLEVEL%"
if not "%expertExitCode%"=="0" echo Installation failed. Read the error above before retrying.
rem Keep results visible when opened from Explorer. CI can opt out of the pause.
if not defined EXPERT_INSTALL_NO_PAUSE pause
exit /b %expertExitCode%
