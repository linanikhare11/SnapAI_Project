#!/bin/bash
# SnapAI Quick Start Script
# Run this from the snapai/ root directory

set -e

echo ""
echo "============================================"
echo "  SnapAI — AI Event Photo Delivery Platform"
echo "============================================"
echo ""

# Check Python
if ! command -v python3 &>/dev/null; then
    echo "❌ Python 3 is required. Install it from https://python.org"
    exit 1
fi

echo "✓ Python $(python3 --version | cut -d' ' -f2) detected"

# Create venv
cd backend
if [ ! -d "venv" ]; then
    echo "→ Creating virtual environment…"
    python3 -m venv venv
fi

# Activate
source venv/bin/activate 2>/dev/null || . venv/Scripts/activate 2>/dev/null

echo "→ Installing Python dependencies (this may take a few minutes for dlib)…"
pip install -q --upgrade pip
pip install -r requirements.txt

echo ""
echo "✓ Dependencies installed"
echo ""
echo "→ Starting SnapAI server…"
echo ""
echo "  Landing page:  http://localhost:5000"
echo "  Dashboard:     http://localhost:5000/dashboard"
echo "  Login:         http://localhost:5000/login"
echo ""
echo "Press Ctrl+C to stop"
echo ""

python app.py
