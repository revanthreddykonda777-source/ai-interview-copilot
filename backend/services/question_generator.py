import json
import re

from backend.ai.router import evaluate_resume


def generate_interview_questions(resume_text, skills=None, job_description=None):
    skills_line = ", ".join(skills) if skills else "the skills mentioned in the resume"
    jd_block = ""
    if job_description and job_description.strip():
        jd_block = f"""
    Target Job Description / Role (focus 4-5 questions on bridging the candidate's skills with this role's requirements and potential skill gaps):
    \"\"\"
    {job_description.strip()[:2500]}
    \"\"\"
    """
    prompt = f"""
    You are a friendly, experienced human interviewer conducting a real interview.

    Look at the candidate's resume and their skills ({skills_line}).
    Generate exactly 10 interview questions based on the skills listed on their resume,
    ordered progressively from simple to difficult:
    - Questions 1-4 ("Beginner"): Basic, foundational questions about their core skills to warm up.
    - Questions 5-7 ("Intermediate"): Practical, everyday how-it-works and problem-solving questions on those skills.
    - Questions 8-10 ("Advanced"): Deeper architecture, optimization, edge-case, or trade-off questions.
    {jd_block}

    Style rules (VERY IMPORTANT):
    - Ask general, skill-focused questions (not hyper-specific trivia about one bullet point), phrased naturally and conversationally just like a human interviewer speaking out loud (e.g., "Can you explain...", "How do you usually handle...", "What's the difference between...").
    - Keep each question concise (1-2 sentences).
    - Write each sample "answer" naturally in plain, conversational language — the way a strong candidate would actually explain it in an interview (2-4 clear sentences, not a stiff textbook essay).
    - Mix "theoretical" and "coding" types where appropriate, and keep difficulty strictly one of "Beginner", "Intermediate", or "Advanced" in ascending order.

    Resume:
    \"\"\"
    {resume_text[:12000]}
    \"\"\"

    Return ONLY JSON, no markdown fences, no commentary. Exactly this shape:
    [
        {{
            "question":"...",
            "answer":"...",
            "hint":"...",
            "difficulty":"Beginner",
            "type":"theoretical"
        }}
    ]
    """
    
    response = evaluate_resume(prompt)

    response = re.sub(r"<think>.*?</think>", "", response, flags=re.DOTALL)
    response = re.sub(r"```json", "", response)
    response = re.sub(r"```", "", response)
    response = response.strip()
    
    start = response.find("[")
    end = response.rfind("]")
    
    if start == -1 or end == -1:
        raise Exception("AI did not return JSON")
    
    response = response[start:end+1]

    try:
        data = json.loads(response)
    except json.JSONDecodeError as e:
        raise Exception(f"AI returned invalid JSON: {e}")

    if not isinstance(data, list):
        raise Exception("AI response was not a list of questions")

    valid = [q for q in data if isinstance(q, dict) and q.get("question") and q.get("answer")]
    if not valid:
        raise Exception("AI response contained no usable questions")

    return valid