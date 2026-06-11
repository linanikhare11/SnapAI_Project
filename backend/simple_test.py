#!/usr/bin/env python3
"""Simple test to check if app.py loads."""
import sys
import time

print(f"[{time.time()}] Starting import test")
sys.stdout.flush()

try:
    print(f"[{time.time()}] Importing app...")
    sys.stdout.flush()
    import app
    print(f"[{time.time()}] ✓ App imported successfully")
    sys.stdout.flush()
except Exception as e:
    print(f"[{time.time()}] ✗ App import failed")
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
    sys.stdout.flush()
