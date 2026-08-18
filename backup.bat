@echo off
setlocal
cd /d "%~dp0"
set DEST=C:\Users\Lenovo\Desktop\LEADFLOW_backups
if not exist "%DEST%" mkdir "%DEST%"
for /f "tokens=1-3 delims=/ " %%a in ("%date%") do set DS=%%a-%%b-%%c
for /f "tokens=1-2 delims=: " %%a in ("%time%") do set TS=%%a-%%b
copy /Y "data\leadflow.db" "%DEST%\leadflow_%DS%_%TS%.db" >nul
echo Backup saved to %DEST%\leadflow_%DS%_%TS%.db