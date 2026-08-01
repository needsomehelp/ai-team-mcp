@echo off
REM Start the AI Team REST API server: api_server.cmd
REM Listens on 0.0.0.0:8642 by default (see .env / AITEAM_API_PORT to change).
setlocal
set "AITEAM_HOME=%~dp0"
"%AITEAM_HOME%venv\Scripts\python.exe" "%AITEAM_HOME%api_server.py" %*
endlocal
