#!/usr/bin/env bash
# Start the OpenGa interface.
set -euo pipefail
cd "$(dirname "$0")"
python3 -m pip install -q -r requirements.txt
exec python3 -m streamlit run app/streamlit_app.py
