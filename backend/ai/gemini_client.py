import os
from dotenv import load_dotenv
import google.generativeai as genai

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
load_dotenv(os.path.join(BASE_DIR, ".env"))

API_KEY = (os.getenv("GOOGLE_API_KEY") or "").strip()

if API_KEY:
    genai.configure(api_key=API_KEY)

# Fastest models first. Each model has its own free-tier quota, so when one is
# rate-limited (429) or unavailable we move straight on to the next one.
# Override with a comma-separated GEMINI_MODELS env var.
DEFAULT_MODELS = (
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash-lite",
    "gemini-flash-lite-latest",
    "gemini-3-flash-preview",
)
MODEL_NAMES = [
    m.strip() for m in (os.getenv("GEMINI_MODELS") or ",".join(DEFAULT_MODELS)).split(",") if m.strip()
]
_MODELS = {name: genai.GenerativeModel(name) for name in MODEL_NAMES}


def ask_gemini(prompt, timeout=20):
    if not API_KEY:
        raise RuntimeError("GOOGLE_API_KEY is not configured")
    errors = []
    for name in MODEL_NAMES:
        try:
            response = _MODELS[name].generate_content(prompt, request_options={"timeout": timeout})
            text = response.text
            if text and text.strip():
                return text
            errors.append(f"{name}: empty response")
        except Exception as e:
            print(f"Gemini model {name} failed: {str(e)[:200]}")
            errors.append(f"{name}: {str(e)[:120]}")
    raise RuntimeError("All Gemini models failed -> " + " | ".join(errors))
