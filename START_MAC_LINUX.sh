#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
PYTHON="$(command -v python3)"
if [ -z "$PYTHON" ]; then echo 'Install Python 3.11+ first.'; exit 1; fi
if [ ! -f .venv/bin/python ]; then "$PYTHON" -m venv .venv; fi
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m streamlit run app.py --server.address 127.0.0.1 --browser.gatherUsageStats false
