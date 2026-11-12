import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.ai.gemini_client import ask_gemini

response = ask_gemini("What is Python? Explain in one sentence.")

print(response)