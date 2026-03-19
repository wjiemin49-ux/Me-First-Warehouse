@echo off
set ROOT=%~dp0
set LOGDIR=%ROOT%logs
set RUNTIMEDIR=%ROOT%runtime
if not exist "%LOGDIR%" mkdir "%LOGDIR%"
if not exist "%RUNTIMEDIR%" mkdir "%RUNTIMEDIR%"
:loop
echo %date%T%time% [INFO] batch demo alive>> "%LOGDIR%\app.log"
echo {"timestamp":"%date%T%time%","status":"alive","demo":"batch-loop"}> "%RUNTIMEDIR%\heartbeat.json"
timeout /t 15 >nul
goto loop
