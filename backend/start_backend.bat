@echo off
echo 🚀 Starting Music Platform Backend...

REM Check if database exists
if exist "music_platform.db" (
    echo ✅ Database file found: music_platform.db
) else (
    echo ❌ Database file not found, creating new one...
)

REM Set environment variables
set DATABASE_URL=sqlite:///./music_platform.db

echo 🗄️ Database URL: %DATABASE_URL%
echo 🌐 Starting server on http://localhost:8000
echo 📖 API docs: http://localhost:8000/docs
echo 🔍 Health check: http://localhost:8000/health

REM Start the server
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

pause
