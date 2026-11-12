"""Build backend/scripts/question_bank.json: 50 real interview questions per core track.

One-off authoring tool (run locally with GOOGLE_API_KEY in .env). The output JSON is
committed and used to seed the database, so the live app never calls the AI for it.

    python -m backend.scripts.build_question_bank            # all missing tracks
    python -m backend.scripts.build_question_bank sql react  # only these tracks
"""
import json
import os
import re
import sys
import time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.ai.gemini_client import ask_gemini  # noqa: E402

OUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "question_bank.json")

TRACKS = {
    "html": ("HTML", True, "semantic HTML, forms and validation, accessibility, SEO/meta tags, the DOM, media, web storage, performance"),
    "css": ("CSS", True, "box model, specificity and the cascade, flexbox, grid, positioning, responsive design, animations, custom properties"),
    "javascript": ("JavaScript", True, "closures, scope and hoisting, `this`, prototypes, the event loop, promises and async/await, ES modules, array methods, the DOM and events"),
    "react": ("React", True, "components and props, state, hooks (useState, useEffect, useMemo, useCallback, useRef, custom hooks), rendering and reconciliation, context, forms, performance, routing"),
    "typescript": ("TypeScript", True, "types vs interfaces, generics, unions and narrowing, utility types, mapped and conditional types, strictness, typing React and APIs"),
    "sql": ("SQL", True, "joins, GROUP BY/HAVING, subqueries and CTEs, window functions, indexes, normalization, transactions and isolation, query optimization"),
    "python": ("Python", True, "data structures, mutability, comprehensions, generators, decorators, OOP and dunder methods, exceptions, the GIL and concurrency, typing, standard library"),
    "nodejs": ("Node.js", True, "the event loop, async I/O, streams, Express middleware, error handling, modules, worker threads, security, performance"),
    "git": ("Git", True, "commits and the staging area, branching, merge vs rebase, resolving conflicts, reset vs revert, stash, reflog, cherry-pick, team workflows"),
    "dsa": ("Data Structures & Algorithms", True, "arrays and strings, hash maps, two pointers, sliding window, stacks and queues, linked lists, trees and BSTs, graphs (BFS/DFS), heaps, binary search, recursion, dynamic programming, Big-O"),
    "hotel_management": ("Hotel Management", False, "front office and reservations, housekeeping, F&B service, revenue and yield management, guest complaints, events and banqueting, PMS software, hospitality operations"),
    "marketing": ("Marketing", False, "SEO, content, social media, email, paid ads/PPC, branding, market research, funnels and conversion, analytics and ROI, A/B testing"),
    "hr": ("Human Resources", False, "recruitment and interviewing, onboarding, retention and engagement, performance management, payroll and benefits, employee relations and conflict, labor law and compliance, HRIS"),
    "project_management": ("Project Management", False, "Agile and Scrum, Kanban, Waterfall, planning and estimation, risk management, stakeholder communication, scope creep, budgeting, metrics and retrospectives"),
    "customer_service": ("Customer Service", False, "handling difficult customers, de-escalation, empathy and active listening, ticketing and CRM tools, SLAs, CSAT/NPS, first-contact resolution, multichannel support"),
}

PLAN = [("Beginner", 15), ("Intermediate", 20), ("Advanced", 15)]


def _prompt(label, is_tech, focus, difficulty, count, avoid):
    if is_tech:
        mix = (
            f"About a third should be type \"coding\" (write/explain a short snippet{', query' if label == 'SQL' else ''}, "
            "predict output, or fix a bug); the rest type \"theoretical\"."
        )
    else:
        mix = 'All type "theoretical". Mix knowledge questions with realistic situational ones ("A guest ... what do you do?").'
    avoid_block = ("\nDo NOT repeat or rephrase any of these existing questions:\n- " + "\n- ".join(avoid)) if avoid else ""
    return f"""You are writing a question bank for real {label} job interviews.

Write exactly {count} distinct {difficulty}-level interview questions for {label}.
Cover a spread of these areas: {focus}.
{mix}

Rules:
- Each question must be specific and something a real interviewer would ask, e.g. "What is the difference between == and === in JavaScript?" -- never a generic template like "Explain {{topic}} and why it is important".
- "answer": a correct, concrete model answer in 2-4 plain sentences, the way a strong candidate would say it. Include a tiny code example inline only when it genuinely helps.
- "hint": one short nudge that does not give the answer away.
- No numbering, no markdown fences.{avoid_block}

Return ONLY a JSON array of {count} objects with keys "question", "answer", "hint", "type"."""


def _parse(text):
    text = re.sub(r"```(?:json)?", "", text).strip()
    start, end = text.find("["), text.rfind("]")
    data = json.loads(text[start:end + 1])
    out = []
    for q in data:
        if not isinstance(q, dict):
            continue
        question, answer = (q.get("question") or "").strip(), (q.get("answer") or "").strip()
        question = re.sub(r"^(coding|theoretical)\s*:\s*", "", question, flags=re.I)
        if len(question) < 15 or len(answer) < 40 or "{" in question:
            continue
        out.append({
            "question": question,
            "answer": answer,
            "hint": (q.get("hint") or "").strip() or "Start from the core definition, then give an example.",
            "type": "coding" if q.get("type") == "coding" else "theoretical",
        })
    return out


def build_track(track_id):
    label, is_tech, focus = TRACKS[track_id]
    questions, seen = [], set()
    for difficulty, count in PLAN:
        got = []
        for attempt in range(8):
            need = count - len(got)
            if need <= 0:
                break
            try:
                batch = _parse(ask_gemini(_prompt(label, is_tech, focus, difficulty, need + 3,
                                                  [q["question"] for q in questions + got][-60:]), timeout=120))
            except Exception as e:  # rate limits, bad JSON: wait and retry
                print(f"  {track_id}/{difficulty} attempt {attempt + 1} failed: {str(e)[:120]}")
                time.sleep(20)
                continue
            for q in batch:
                key = re.sub(r"\W+", " ", q["question"].lower()).strip()
                if key not in seen and len(got) < count:
                    seen.add(key)
                    got.append({**q, "difficulty": difficulty})
            time.sleep(4)
        if len(got) < count:
            raise RuntimeError(f"{track_id}/{difficulty}: only {len(got)}/{count} questions")
        questions += got
    return questions


def main():
    bank = {}
    if os.path.exists(OUT_PATH):
        with open(OUT_PATH, encoding="utf-8") as fh:
            bank = json.load(fh)
    wanted = sys.argv[1:] or [t for t in TRACKS if len(bank.get(t, [])) != 50]
    for track_id in wanted:
        t0 = time.time()
        bank[track_id] = build_track(track_id)
        with open(OUT_PATH, "w", encoding="utf-8") as fh:
            json.dump({k: bank[k] for k in TRACKS if k in bank}, fh, ensure_ascii=False, indent=1)
        print(f"{track_id}: {len(bank[track_id])} questions in {time.time() - t0:.0f}s", flush=True)
    print("done:", {k: len(v) for k, v in bank.items()})


if __name__ == "__main__":
    main()
