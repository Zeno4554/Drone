import subprocess
import sys
import time
import os

def main():
    print("Starting AeroCorridor Backend and Frontend...")
    
    # Use current directory (root) as working directory
    cwd = os.getcwd()
    
    # Start backend
    backend_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"],
        cwd=cwd
    )
    
    # Give backend a moment to start before frontend
    time.sleep(2)
    
    # Start frontend
    frontend_process = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "frontend/home.py"],
        cwd=cwd
    )
    
    try:
        # Wait for both processes
        backend_process.wait()
        frontend_process.wait()
    except KeyboardInterrupt:
        print("\nShutting down servers...")
        backend_process.terminate()
        frontend_process.terminate()
        backend_process.wait()
        frontend_process.wait()
        print("Servers stopped.")

if __name__ == "__main__":
    main()