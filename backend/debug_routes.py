import sys
import os

# Add the current directory to sys.path so we can import app
sys.path.append(os.getcwd())

from app.main import app

print("Registered Routes:")
for route in app.routes:
    print(f"- {route.path} [{route.name}]")
