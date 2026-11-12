import os
import re
import shutil
import subprocess
import time
import ollama

PREFERRED_MODELS = ("qwen2.5:3b", "qwen3:1.7b")


def _list_model_names():
    res = ollama.list()
    models = getattr(res, "models", None)
    if models is None and isinstance(res, dict):
        models = res.get("models", [])
    names = []
    for m in models or []:
        name = getattr(m, "model", None) or (m.get("model") or m.get("name") if isinstance(m, dict) else None)
        if name:
            names.append(name)
    return names


def _ensure_ollama_running(timeout=10.0):
    try:
        return _list_model_names()
    except Exception:
        pass

    ollama_bin = shutil.which("ollama")
    if not ollama_bin:
        raise RuntimeError("Ollama CLI not found. Please install Ollama from https://ollama.com/download")

    kwargs = {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS

    subprocess.Popen([ollama_bin, "serve"], **kwargs)

    deadline = time.time() + timeout
    last_err = None
    while time.time() < deadline:
        time.sleep(0.5)
        try:
            return _list_model_names()
        except Exception as e:
            last_err = e

    raise RuntimeError(f"Failed to start Ollama server: {last_err}")


def _pick_model(installed):
    env_model = (os.getenv("OLLAMA_MODEL") or "").strip()
    if env_model:
        if env_model in installed:
            return env_model
        for m in installed:
            if m.startswith(env_model):
                return m

    for preferred in PREFERRED_MODELS:
        if preferred in installed:
            return preferred

    if installed:
        return installed[0]

    raise RuntimeError("No Ollama models installed. Run: ollama pull qwen3:1.7b")


def ask_ollama(prompt):
    installed = _ensure_ollama_running()
    model = _pick_model(installed)
    print(f"Using Ollama ({model})...")

    messages = [{"role": "user", "content": prompt}]
    try:
        response = ollama.chat(model=model, messages=messages, think=False)
    except TypeError:
        response = ollama.chat(model=model, messages=messages)

    content = response["message"]["content"]
    content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
    print("Ollama Response Received")
    return content