#!/usr/bin/env python3
"""
Simple backend startup script to avoid Docker issues.
"""

import os
import sys
import uvicorn

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    print("🚀 Starting Music Platform Backend...")
    print(f"📁 Working directory: {os.getcwd()}")
    
    # Check database file
    db_path = "music_platform.db"
    if os.path.exists(db_path):
        print(f"✅ Database file found: {db_path}")
        print(f"📊 Database size: {os.path.getsize(db_path)} bytes")
    else:
        print(f"❌ Database file not found: {db_path}")
        print("🔧 Creating new database...")
    
    # Check environment
    database_url = os.getenv("DATABASE_URL", "sqlite:///./music_platform.db")
    print(f"🗄️ Database URL: {database_url}")
    
    # Start the server
    print("🌐 Starting FastAPI server on http://0.0.0.0:8000")
    print("📖 API docs will be available at http://localhost:8000/docs")
    print("🔍 Health check at http://localhost:8000/health")
    
    try:
        uvicorn.run(
            "app.main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info"
        )
    except Exception as e:
        print(f"❌ Failed to start server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
