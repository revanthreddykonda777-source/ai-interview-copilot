from difflib import SequenceMatcher

def evaluate_answer(user_answer, correct_answer):

    similarity = SequenceMatcher(
        None,
        user_answer.lower(),
        correct_answer.lower()
    ).ratio()

    score = round(similarity * 100)

    if score >= 80:
        feedback = "Excellent! You're on the right track."
        tips = "Very good answer."

    elif score >= 60:
        feedback = "Good attempt"
        tips = "Try to include more details."

    elif score >= 40:
        feedback = "Needs Improvement"
        tips = "Focus on key areas and improve explanations."

    else:
        feedback = "Incorrect"
        tips = "Review the fundamentals and practice again."

    return {
        "score": score,
        "feedback": feedback,
        "tips": tips,
        "correct_answer": correct_answer
    }