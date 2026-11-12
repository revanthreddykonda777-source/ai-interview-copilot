import os
from dotenv import load_dotenv
import google.generativeai as genai

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
load_dotenv(os.path.join(BASE_DIR, ".env"))

API_KEY = (os.getenv("GOOGLE_API_KEY") or "").strip()

if API_KEY:
    genai.configure(api_key=API_KEY)

model = genai.GenerativeModel("gemini-3-flash-preview")

def ask_gemini(prompt):
    if not API_KEY:
        raise RuntimeError("GOOGLE_API_KEY is not configured")
    try:
        response = model.generate_content(prompt, request_options={"timeout": 30})
        return response.text
    except Exception as e:
        raise Exception(str(e))