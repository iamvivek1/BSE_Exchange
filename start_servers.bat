@echo off
echo Starting BSE Trading Application...
echo.

echo Starting Backend Server (Port 3002)...
start "BSE Backend" python server.py

echo Waiting for backend to initialize...
timeout /t 3 /nobreak > nul

echo Starting Frontend Server (Port 8080)...
start "BSE Frontend" python start_frontend.py --port 8080

echo.
echo ========================================
echo BSE Trading Application Started!
echo ========================================
echo Backend API: http://localhost:3002
echo Frontend App: http://localhost:8080
echo Backend Test: http://localhost:8080/test_backend.html
echo.
echo Press any key to open the application...
pause > nul

echo Opening application in browser...
start http://localhost:8080

echo.
echo Both servers are running!
echo Press Ctrl+C in each window to stop the servers.
echo.