#!/usr/bin/env python
"""
Chess Game Runner - Launches all components needed for the chess demo.
"""
import os
import sys
import subprocess
import time

# Set environment variable for all child processes
os.environ["MCP_PROTOCOL"] = "sse"  # Use SSE which is more reliable for testing

# Create white player server in background
print("Starting White Player Server...")
white_process = subprocess.Popen(
    ["python", "WhiteAgent.py"], 
    env=os.environ.copy()
)

# Create black player server in background 
print("Starting Black Player Server...")
black_process = subprocess.Popen(
    ["python", "BlackAgent.py"], 
    env=os.environ.copy()
)

# Give servers time to start up
print("Waiting for servers to initialize (5 seconds)...")
time.sleep(5)

try:
    # Start the board agent (this will run in foreground)
    print("Starting Chess Board...")
    board_process = subprocess.run(
        ["python", "BoardAgent.py"],
        env=os.environ.copy()
    )
    
    # If we get here, the board has exited
    print("Chess game completed.")
    
except KeyboardInterrupt:
    print("\nGame interrupted by user.")
    
finally:
    # Clean up server processes
    print("Shutting down servers...")
    white_process.terminate()
    black_process.terminate()
    
    # Give them time to shut down
    time.sleep(1)
    
    # Force kill if they haven't exited
    try:
        white_process.kill()
    except OSError:
        pass
    
    try:
        black_process.kill()
    except OSError:
        pass
    
    print("All processes terminated.") 