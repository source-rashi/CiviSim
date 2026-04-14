#!/usr/bin/env python3
"""
CiviSim Dashboard Launcher

Run this script to start the modern Dash-based frontend for CiviSim.
"""

import os
import sys
import subprocess

def main():
    """Launch the CiviSim dashboard"""
    print("🚀 Starting CiviSim Dashboard...")
    print("📍 Dashboard will be available at: http://localhost:8050")
    print("❌ Press Ctrl+C to stop the server")
    print("-" * 50)

    try:
        # Run the dashboard
        subprocess.run([sys.executable, "dashboard.py"], check=True)
    except KeyboardInterrupt:
        print("\n👋 Dashboard stopped by user")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error starting dashboard: {e}")
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())