#!/usr/bin/env python3
"""
Startup script to run both backend and frontend servers
"""
import subprocess
import sys
import os
import time
import threading
import signal

def run_backend():
    """Run the FastAPI backend server"""
    backend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend')
    os.chdir(backend_dir)
    subprocess.run([sys.executable, 'main.py'])

def run_frontend():
    """Run the frontend server"""
    frontend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'frontend')
    os.chdir(frontend_dir)
    subprocess.run([sys.executable, 'server.py'])

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    print('\nShutting down servers...')
    sys.exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    
    print("Starting Google Sign-In Test App...")
    print("Backend will run on: http://localhost:8001")
    print("Frontend will run on: http://localhost:5175")
    print("Press Ctrl+C to stop both servers")
    print("-" * 50)
    
    # Start backend in a separate thread
    backend_thread = threading.Thread(target=run_backend, daemon=True)
    backend_thread.start()
    
    # Give backend time to start
    time.sleep(2)
    
    # Start frontend in the main thread
    try:
        run_frontend()
    except KeyboardInterrupt:
        print("\nShutting down...")
        sys.exit(0)
