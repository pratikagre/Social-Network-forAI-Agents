import os
import sys

# Add repository root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.main import app

# Vercel serverless entrypoint
handler = app
