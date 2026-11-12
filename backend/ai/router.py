from backend.ai.ollama_client import ask_ollama

def evaluate_resume(prompt):
    """
    First try Gemini.
    If Gemini is unavailable for ANY reason (quota/limit, network, empty response),
    automatically use Ollama.
    """

    try:
        from backend.ai.gemini_client import ask_gemini

        print("Using Gemini...")
        result = ask_gemini(prompt)
        if result and result.strip():
            return result
        raise ValueError("Gemini returned an empty response")

    except Exception as e:
        print("=" * 60)
        print("Gemini Failed")
        print(e)
        print("Switching to Ollama")
        print("=" * 60)

        return ask_ollama(prompt)