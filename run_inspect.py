#!/usr/bin/env python3
"""
Test script to run inspect_html and capture output
"""
import subprocess
import sys

result = subprocess.run([sys.executable, "inspect_html.py"], capture_output=False, text=True)
sys.exit(result.returncode)
