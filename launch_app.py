import os
import sys
import subprocess

print("🚀 Launching Innovators United Web Application...")
print("Please wait while the server starts...")
print("")

try:
    # Check if Python is available
    result = subprocess.run([sys.executable, "--version"], capture_output=True, text=True)
    print(f"Using Python: {result.stdout.strip()}")
    
    # Run the Flask app
    print("Starting Flask application...")
    subprocess.run([sys.executable, "app.py"])
    
except FileNotFoundError:
    print("❌ Error: Python not found. Please install Python 3.7 or higher.")
    input("Press Enter to close...")
except Exception as e:
    print(f"❌ Error starting application: {e}")
    input("Press Enter to close...")