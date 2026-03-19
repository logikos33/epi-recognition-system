#!/usr/bin/env python3
"""
Streamlit Cloud Entry Point
Main application file for Streamlit Cloud deployment

This is the entry point that Streamlit Cloud uses to run the dashboard.
It imports and runs the main dashboard from reporting_agent.
"""

import sys
import os

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import and run the dashboard
from agents.reporting_agent import dashboard_main

if __name__ == "__main__":
    dashboard_main.main()
