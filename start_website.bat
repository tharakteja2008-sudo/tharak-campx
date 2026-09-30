@echo off
title CampX Live Dashboard - SVCE Tirupati
color 0A
echo.
echo  ========================================
echo   CampX Live Attendance Dashboard
echo   Sri Venkateswara College of Engineering
echo  ========================================
echo.
echo  Starting server...
echo  Dashboard will open at: http://localhost:5000
echo.
echo  Press Ctrl+C to stop the server.
echo.

:: Wait 2 seconds then open browser
start "" /b cmd /c "timeout /t 2 /nobreak >nul && start http://localhost:5000"

:: Start the Flask server
cd /d "c:\Users\thara\OneDrive\Desktop\MOUNISH\campx_attendance_tracker"
"C:\Users\thara\AppData\Local\Python\bin\python.exe" server.py
