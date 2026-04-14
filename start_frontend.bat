@echo off
echo Starting Music Platform Frontend...
echo.

REM Check if we're in the right directory
if not exist "package.json" (
    echo Error: package.json not found. Please run this from the feishin directory.
    pause
    exit /b 1
)

REM Start the web development server
echo Starting web development server on http://localhost:5173
echo.
echo This will start the unified responsive UI with:
echo - Ethiopian music platform interface
echo - Working payment methods
echo - Responsive design for mobile, desktop, and Telegram
echo.
echo Press Ctrl+C to stop the server
echo.

npm run dev:remote

pause
