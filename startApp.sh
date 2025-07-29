#!/bin/bash
source venv/bin/activate && kill -9 $(lsof -ti:8087) 2>/dev/null; python app.py