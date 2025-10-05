#!/usr/bin/env python3
"""
Start the ModelGuard frontend server
"""
import subprocess
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    print("🦷 Starting ModelGuard Frontend Server...")
    print("🌐 UI will be available at: http://localhost:8501")
    print("⚠️  Make sure the backend is running on port 8000")
    print("\nPress Ctrl+C to stop the server")
    
    try:
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", 
            "frontend/app.py",
            "--server.port=8501",
            "--server.address=0.0.0.0",
            "--server.headless=true"
        ])
    except KeyboardInterrupt:
        print("\n👋 Frontend server stopped")
    except Exception as e:
        print(f"❌ Error starting frontend: {e}")
        sys.exit(1)
