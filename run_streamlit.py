#!/usr/bin/env python3
"""
Run script for RBH Weather AI Agent Streamlit App
"""
import subprocess
import sys
import os

def main():
    """Run the Streamlit application"""
    try:
        # Change to the streamlit_app directory
        os.chdir(os.path.join(os.path.dirname(__file__), 'streamlit_app'))
        
        # Run streamlit
        subprocess.run([
            sys.executable, '-m', 'streamlit', 'run', 'main.py',
            '--server.port', '8501',
            '--server.address', 'localhost',
            '--browser.gatherUsageStats', 'false'
        ])
    except KeyboardInterrupt:
        print("\n👋 Application stopped by user")
    except Exception as e:
        print(f"❌ Error running application: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

