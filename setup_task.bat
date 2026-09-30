@echo off
:: ============================================================
:: CampX Attendance Tracker - Task Scheduler Setup
:: Registers a robust scheduled task with multiple triggers
:: ============================================================

echo.
echo ========================================
echo  CampX Attendance Tracker - Task Setup
echo ========================================
echo.

:: Delete old task if exists
schtasks /delete /tn "CampX_Daily_Attendance_Reporter" /f >nul 2>&1

:: Create the task using XML for advanced options
schtasks /create /tn "CampX_Daily_Attendance_Reporter" /xml "%~dp0campx_task.xml" /f

if %errorlevel% equ 0 (
    echo.
    echo [SUCCESS] Task registered successfully!
    echo.
    echo Schedule:
    echo   - Every day at 8:30 AM IST (morning report)
    echo   - Every day at 6:30 PM IST (evening report)
    echo   - On every logon (catch-up if laptop was off)
    echo.
    echo Features:
    echo   - Runs even if a scheduled time was missed
    echo   - Retries up to 3 times on network errors
    echo   - Logs output to tracker.log
    echo.
) else (
    echo.
    echo [ERROR] Failed to register task. Try running as Administrator.
    echo.
)

pause
