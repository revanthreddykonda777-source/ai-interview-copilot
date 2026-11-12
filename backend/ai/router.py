import os
import shutil

from backend.ai.ollama_client import ask_ollama


def _ollama_available():
    # Ollama only exists on a local machine; on hosts like Render it's absent.
    return bool(shutil.which("ollama") or os.getenv("OLLAMA_HOST"))


def evaluate_resume(prompt):
    """
    First try Gemini (which itself tries several models).
    If Gemini is unavailable for ANY reason and Ollama is installed locally,
    fall back to Ollama.
    """

    try:
        from backend.ai.gemini_client import ask_gemini

        result = ask_gemini(prompt)
        if result and result.strip():
            return result
        raise ValueError("Gemini returned an empty response")

    except Exception as e:
        print("Gemini failed:", str(e)[:300])
        if not _ollama_available():
            raise
        print("Switching to Ollama")
        return ask_ollama(prompt)
