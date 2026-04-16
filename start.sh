#!/bin/bash
# RouteIQ — Start Script
# Usage: chmod +x start.sh && ./start.sh

set -e

echo ""
echo "  ██████╗  ██████╗ ██╗   ██╗████████╗███████╗██╗ ██████╗ "
echo "  ██╔══██╗██╔═══██╗██║   ██║╚══██╔══╝██╔════╝██║██╔═══██╗"
echo "  ██████╔╝██║   ██║██║   ██║   ██║   █████╗  ██║██║   ██║"
echo "  ██╔══██╗██║   ██║██║   ██║   ██║   ██╔══╝  ██║██║▄▄ ██║"
echo "  ██║  ██║╚██████╔╝╚██████╔╝   ██║   ███████╗██║╚██████╔╝"
echo "  ╚═╝  ╚═╝ ╚═════╝  ╚═════╝    ╚═╝   ╚══════╝╚═╝ ╚══▀▀═╝ "
echo ""
echo "  Dynamic Programming Route Optimizer — Held-Karp TSP"
echo "  ─────────────────────────────────────────────────────"

# Step 1: Compile C++ engine
echo ""
echo "▶ Compiling Held-Karp C++ engine..."
cd "$(dirname "$0")/cpp_engine"
g++ -O2 -std=c++17 -o route_optimizer route_optimizer.cpp
echo "  ✓ C++ solver compiled successfully"

# Step 2: Install Python deps
cd "$(dirname "$0")/backend"
echo ""
echo "▶ Installing Python dependencies..."
pip install -q -r requirements.txt
echo "  ✓ Flask installed"

# Step 3: Launch Flask
echo ""
echo "▶ Starting Flask API server..."
echo "  ✓ Server: http://localhost:5000"
echo ""
echo "  Open http://localhost:5000 in your browser"
echo "  ─────────────────────────────────────────────────────"
echo ""

python app.py
