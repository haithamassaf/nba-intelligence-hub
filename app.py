"""Root entry point for Streamlit Cloud deployment."""

import runpy
runpy.run_path("frontend/app.py", run_name="__main__")
