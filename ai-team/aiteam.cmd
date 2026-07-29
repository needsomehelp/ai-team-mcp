@echo off
REM Call the AI team from any directory, like: aiteam "fix the failing test"
REM The agent works in whatever folder you run this from, not in ai-team's folder.
setlocal
set "AITEAM_HOME=%~dp0"
"%AITEAM_HOME%venv\Scripts\python.exe" "%AITEAM_HOME%aiteam.py" %*
endlocal
