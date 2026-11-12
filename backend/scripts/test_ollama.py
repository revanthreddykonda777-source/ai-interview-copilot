import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.ai.ollama_client import ask_ollama

print("Testing Ollama..")


response = ask_ollama("what is python ? Answer in one sentence.")

print(response)