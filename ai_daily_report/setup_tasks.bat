@echo off
REM AI Daily Report - Windows Task Scheduler Setup Script
REM Run this script as Administrator

echo Creating Windows Scheduled Tasks for AI Daily Report...
echo.

REM Get Python path
set PYTHON_PATH=C:\Users\MACHENIKE\AppData\Local\Programs\Python\Python312\python.exe
set SCRIPT_PATH=d:\me\脚本\ai_daily_report\main.py

echo Python Path: %PYTHON_PATH%
echo Script Path: %SCRIPT_PATH%
echo.

REM Create 6:00 AM task
echo Creating 6:00 AM task...
schtasks /create /tn "AI_Daily_Report_06" /tr "\"%PYTHON_PATH%\" \"%SCRIPT_PATH%\"" /sc daily /st 06:00 /f
if %errorlevel% equ 0 (
    echo [OK] 6:00 AM task created successfully
) else (
    echo [ERROR] Failed to create 6:00 AM task
)
echo.

REM Create 8:00 AM task
echo Creating 8:00 AM task...
schtasks /create /tn "AI_Daily_Report_08" /tr "\"%PYTHON_PATH%\" \"%SCRIPT_PATH%\"" /sc daily /st 08:00 /f
if %errorlevel% equ 0 (
    echo [OK] 8:00 AM task created successfully
) else (
    echo [ERROR] Failed to create 8:00 AM task
)
echo.

REM Create 10:00 AM task
echo Creating 10:00 AM task...
schtasks /create /tn "AI_Daily_Report_10" /tr "\"%PYTHON_PATH%\" \"%SCRIPT_PATH%\"" /sc daily /st 10:00 /f
if %errorlevel% equ 0 (
    echo [OK] 10:00 AM task created successfully
) else (
    echo [ERROR] Failed to create 10:00 AM task
)
echo.

REM Create 12:00 PM task
echo Creating 12:00 PM task...
schtasks /create /tn "AI_Daily_Report_12" /tr "\"%PYTHON_PATH%\" \"%SCRIPT_PATH%\"" /sc daily /st 12:00 /f
if %errorlevel% equ 0 (
    echo [OK] 12:00 PM task created successfully
) else (
    echo [ERROR] Failed to create 12:00 PM task
)
echo.

REM Create 6:00 PM task
echo Creating 6:00 PM task...
schtasks /create /tn "AI_Daily_Report_18" /tr "\"%PYTHON_PATH%\" \"%SCRIPT_PATH%\"" /sc daily /st 18:00 /f
if %errorlevel% equ 0 (
    echo [OK] 6:00 PM task created successfully
) else (
    echo [ERROR] Failed to create 6:00 PM task
)
echo.

echo ============================================================
echo All tasks created! Verifying...
echo ============================================================
echo.

schtasks /query | findstr "AI_Daily_Report"

echo.
echo ============================================================
echo Setup complete!
echo ============================================================
echo.
echo To test a task manually, run:
echo   schtasks /run /tn "AI_Daily_Report_06"
echo.
echo To delete all tasks, run:
echo   schtasks /delete /tn "AI_Daily_Report_06" /f
echo   schtasks /delete /tn "AI_Daily_Report_08" /f
echo   schtasks /delete /tn "AI_Daily_Report_10" /f
echo   schtasks /delete /tn "AI_Daily_Report_12" /f
echo   schtasks /delete /tn "AI_Daily_Report_18" /f
echo.

pause
