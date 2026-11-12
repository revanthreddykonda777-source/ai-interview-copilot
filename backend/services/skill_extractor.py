import re

skills = [
    # Languages
    "Python",
    "Java",
    "C",
    "C++",
    "JavaScript",
    "TypeScript",
    "SQL",
    "HTML",
    "CSS",
    # Web & Backend
    "React",
    "Next.js",
    "Tailwind CSS",
    "Node.js",
    "Express",
    "Flask",
    "Django",
    "FastAPI",
    "REST API",
    "GraphQL",
    "Microservices",
    "Redis",
    "Kafka",
    # Databases
    "PostgreSQL",
    "MongoDB",
    "Vector Database",
    # AI & Machine Learning
    "Machine Learning",
    "Deep Learning",
    "Scikit-Learn",
    "Pandas",
    "NumPy",
    "TensorFlow",
    "PyTorch",
    "Hugging Face",
    "Generative AI",
    "LLMs",
    "Prompt Engineering",
    "Agentic AI",
    "LangChain",
    "LangGraph",
    "RAG",
    "Embeddings",
    "Fine-Tuning",
    "LoRA",
    "vLLM",
    "MLflow",
    "OpenAI API",
    "Gemini",
    "Ollama",
    # Cloud, DevOps & Testing
    "Git",
    "GitHub Actions",
    "CI/CD",
    "Docker",
    "Kubernetes",
    "Terraform",
    "AWS",
    "GCP",
    "Azure",
    "Linux",
    "Pytest",
]


def extract_skills(text):
    found = []

    for skill in skills:
        # Use word-boundary matching to avoid false positives
        # (e.g. "C" matching inside "Copilot")
        escaped = re.escape(skill)
        # For skills ending with non-word chars (like C++), don't require
        # a trailing word boundary since \b won't match after '+'
        if re.search(r"\w", skill[-1]):
            pattern = r"\b" + escaped + r"\b"
        else:
            pattern = r"\b" + escaped
        if re.search(pattern, text, re.IGNORECASE):
            found.append(skill)

    return found
