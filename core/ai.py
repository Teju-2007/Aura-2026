"""ai.py - every conversation with the Groq AI model happens here.

Rule of this file: the AI's answers are treated as UNTRUSTED text. Everything it
returns as data (tasks, quizzes...) is checked and cleaned before the app uses it.
"""
import json
import re

from core import config


class AIError(Exception):
    """Raised with a friendly message the screen can show to the learner."""


_CLIENT = None
_CLIENT_KEY = None


def _get_client():
    global _CLIENT, _CLIENT_KEY
    api_key = getattr(config, "GROQ_API_KEY", None)
    if not api_key:
        raise AIError("No GROQ_API_KEY found. Check your configuration or Streamlit Secrets.")
    
    # Re-initialize client if key changes or client doesn't exist
    if _CLIENT is None or _CLIENT_KEY != api_key:
        from groq import Groq
        _CLIENT = Groq(api_key=api_key)
        _CLIENT_KEY = api_key
    return _CLIENT


def _friendly_error(exc: Exception) -> str:
    try:
        import groq
        if isinstance(exc, groq.AuthenticationError):
            return "The Groq API key was rejected. Check GROQ_API_KEY in your secrets/settings."
        if isinstance(exc, groq.RateLimitError):
            return "The AI is busy (rate limit reached). Please wait a minute and try again."
        if isinstance(exc, groq.APIConnectionError):
            return "Could not reach the AI service. Check your internet connection."
        if isinstance(exc, groq.NotFoundError):
            return f"Model not found on Groq. Check GROQ_MODEL setting. Details: {exc}"
        if isinstance(exc, groq.BadRequestError):
            return f"Bad request to Groq API: {exc}"
    except ImportError:
        pass
    return f"The AI service encountered an issue: {str(exc)}"


def _complete(messages, temperature=0.7, json_mode=False, max_tokens=2500) -> str:
    """The ONE function that calls the AI. Tests replace this with a fake."""
    client = _get_client()
    model = getattr(config, "GROQ_MODEL", "llama-3.3-70b-versatile")
    kwargs = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    
    try:
        response = client.chat.completions.create(**kwargs)
    except Exception as exc:  # noqa: BLE001 - convert failures to AIError
        raise AIError(_friendly_error(exc)) from exc
    
    content = response.choices[0].message.content if response.choices else None
    if not content or not content.strip():
        raise AIError("The AI sent an empty answer. Please try again.")
    return content


# ---------------------------------------------------------------- cleaning
def extract_json(text: str):
    """Find the first JSON object inside text (handles ```json fences). None if broken."""
    if not text:
        return None
    # Strip markdown code block wrappers
    text = re.sub(r"```(?:json)?", "", text, flags=re.IGNORECASE)
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        return None
    
    json_str = text[start : end + 1]
    try:
        data = json.loads(json_str, strict=False)
    except json.JSONDecodeError:
        try:
            # Fallback: scrub raw control characters and retry
            cleaned = re.sub(r"[\x00-\x1F\x7F]", " ", json_str)
            data = json.loads(cleaned, strict=False)
        except json.JSONDecodeError:
            return None
            
    return data if isinstance(data, dict) else None


def clean_tasks(raw, limit: int = 8):
    if not isinstance(raw, list):
        return []
    seen, result = set(), []
    for item in raw:
        if not isinstance(item, str):
            continue
        item = " ".join(item.split())[:200]
        if item and item.lower() not in seen:
            seen.add(item.lower())
            result.append(item)
    return result[:limit]


def clean_cards(raw, limit: int = 15):
    cards = []
    for item in raw if isinstance(raw, list) else []:
        if not isinstance(item, dict):
            continue
        front, back = item.get("front"), item.get("back")
        if isinstance(front, str) and isinstance(back, str) and front.strip() and back.strip():
            cards.append({"front": front.strip()[:400], "back": back.strip()[:800]})
    return cards[:limit]


def clean_quiz(raw, limit: int = 10):
    questions = []
    for item in raw if isinstance(raw, list) else []:
        if not isinstance(item, dict):
            continue
        question, options = item.get("question"), item.get("options")
        answer = item.get("answer_index")
        if isinstance(answer, str) and answer.strip().isdigit():
            answer = int(answer.strip())
        if not isinstance(question, str) or not question.strip():
            continue
        if not isinstance(options, list) or len(options) != 4:
            continue
        if not all(isinstance(o, str) and o.strip() for o in options):
            continue
        options = [o.strip()[:300] for o in options]
        if len(set(o.lower() for o in options)) != 4:
            continue
        if isinstance(answer, bool) or not isinstance(answer, int) or not 0 <= answer <= 3:
            continue
        explanation = item.get("explanation")
        questions.append({
            "question": question.strip()[:500],
            "options": options,
            "answer_index": answer,
            "explanation": explanation.strip()[:600] if isinstance(explanation, str) else "",
        })
    return questions[:limit]


def clean_resources(raw, limit: int = 6):
    items = []
    for item in raw if isinstance(raw, list) else []:
        if not isinstance(item, dict):
            continue
        title, query = item.get("title"), item.get("search_query")
        if not (isinstance(title, str) and title.strip() and isinstance(query, str) and query.strip()):
            continue
        kind, why = item.get("kind"), item.get("why")
        items.append({
            "title": title.strip()[:200],
            "kind": kind.strip()[:30] if isinstance(kind, str) else "reading",
            "why": why.strip()[:300] if isinstance(why, str) else "",
            "search_query": query.strip()[:200],
        })
    return items[:limit]


# ----------------------------------------------------------------- prompts
def _profile_line(profile: dict) -> str:
    profile = profile or {}
    deadline = profile.get("deadline")
    return (
        f"level={profile.get('level', 'Beginner')}; "
        f"time per day={profile.get('daily_minutes', 30)} minutes; "
        f"goal type={profile.get('goal_type', 'Hobby / curiosity')}; "
        f"deadline={deadline if deadline else 'none given'}"
    )


def _language(profile: dict) -> str:
    return (profile or {}).get("language") or "English"


_ARCHITECT_PROMPT = """You are Aura, a warm, practical learning coach who helps ANY learner \
(students, professionals, hobbyists) design a realistic study roadmap.

Learner profile: {profile}. Preferred intensity: {intensity}. Energy today: {mood}.
Use the profile. Do NOT ask for information that is already in it.

How to behave:
1. While interviewing, ask at most TWO short questions per reply. Learn the topic, what the \
learner already knows, and why they want it.
2. When you have enough, write a clear Blueprint: a short overview, phases with a weekly focus, \
and the first concrete steps. Prefer reading-based resources (books, documentation, articles); \
treat video as optional. Be honest: you cannot browse the web, so never invent URLs, statistics \
or promises.
3. ONLY when the Blueprint is final, end your message with exactly this block (valid JSON):
---JSON---
{{"title": "Short goal title, max 8 words", "tasks": ["Task 1", "Task 2", "Task 3"]}}
---END---
Use 3 to 7 small, concrete tasks the learner can start this week, sized for their daily time.
4. Never output the JSON block while you are still interviewing.
Write everything the learner reads in {language}. Keep the JSON keys in English."""


def architect_reply(history, profile: dict, mood: str = "Neutral") -> dict:
    """history = list of {"role","content"}. Returns {"text","title","tasks","json_error"}."""
    profile = profile or {}
    system = _ARCHITECT_PROMPT.format(
        profile=_profile_line(profile),
        intensity=profile.get("intensity", "Balanced"),
        mood=mood,
        language=_language(profile),
    )
    raw = _complete([{"role": "system", "content": system}] + list(history), temperature=0.7)
    return parse_architect_output(raw)


def parse_architect_output(raw: str) -> dict:
    pattern = re.compile(r"---JSON---(.*?)---END---", re.DOTALL | re.IGNORECASE)
    match = pattern.search(raw)
    
    if match:
        text = raw[:match.start()]
        block = match.group(1)
        data = extract_json(block)
    elif "---JSON---" in raw:
        text, _, block = raw.partition("---JSON---")
        data = extract_json(block)
    else:
        return {"text": raw.strip(), "title": "", "tasks": [], "json_error": False}

    data = data if isinstance(data, dict) else {}
    tasks = clean_tasks(data.get("tasks"))
    title = data.get("title")
    title = " ".join(title.split())[:120] if isinstance(title, str) else ""
    return {"text": text.strip(), "title": title, "tasks": tasks, "json_error": not tasks}


def coach_answer(goal_title: str, roadmap_text: str, question: str, profile: dict) -> str:
    system = (
        "You are Aura, a supportive, technically accurate coach. Explain step by step in simple "
        "words and define every technical term the first time you use it. If you are not sure, "
        f"say so. Never invent links or statistics. Learner: {_profile_line(profile)}. "
        f"Write in {_language(profile)}."
    )
    user = f"Goal: {goal_title}\nRoadmap:\n{roadmap_text[:6000]}\n\nQuestion: {question}"
    return _complete([{"role": "system", "content": system}, {"role": "user", "content": user}])


def simplify_tasks(task_texts, reason: str, profile: dict):
    """Rewrite tasks smaller. Returns a clean list of strings (raises AIError if unusable)."""
    profile = profile or {}
    system = (
        "You shrink study tasks so a tired or busy learner can still make progress. Keep the same "
        "overall direction, but make every task smaller and more concrete. Return ONLY JSON like "
        '{"tasks": ["...", "..."]} with 3 to 7 tasks. '
        f"Write the tasks in {_language(profile)}."
    )
    user = (f"Reason: {reason}. Learner time per day: {profile.get('daily_minutes', 30)} minutes.\n"
            f"Current tasks: {json.dumps(list(task_texts), ensure_ascii=False)}")
    
    data = extract_json(_complete(
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=0.4, json_mode=True))
    
    tasks = clean_tasks(data.get("tasks")) if data else []
    if not tasks:
        raise AIError("The AI could not rewrite the tasks this time. Please try again.")
    return tasks


def make_flashcards(task: str, goal: str, profile: dict, n: int = 8):
    profile = profile or {}
    system = (
        "You write flashcards for active recall. Each card tests ONE idea with a short question "
        "(front) and a short, correct answer (back). Return ONLY JSON like "
        '{"cards": [{"front": "...", "back": "..."}]}. '
        f"Write in {_language(profile)}. Only include facts you are confident are correct."
    )
    user = f"Overall goal: {goal}\nTask: {task}\nLevel: {profile.get('level')}\nMake {n} cards."
    
    data = extract_json(_complete(
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=0.4, json_mode=True))
    
    cards = clean_cards(data.get("cards")) if data else []
    if not cards:
        raise AIError("The AI could not make usable flashcards this time. Please try again.")
    return cards


def make_quiz(task: str, goal: str, profile: dict, n: int = 5):
    profile = profile or {}
    system = (
        "You write multiple-choice quizzes. Each question has exactly 4 different options, one "
        "correct. Return ONLY JSON like "
        '{"questions": [{"question": "...", "options": ["A", "B", "C", "D"], '
        '"answer_index": 0, "explanation": "..."}]}. answer_index is 0 to 3. '
        f"Difficulty: {profile.get('level')}. Write in {_language(profile)}. "
        "Only ask things you are confident about."
    )
    user = f"Overall goal: {goal}\nTask: {task}\nMake {n} questions."
    
    data = extract_json(_complete(
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=0.4, json_mode=True))
    
    questions = clean_quiz(data.get("questions")) if data else []
    if not questions:
        raise AIError("The AI could not make a usable quiz this time. Please try again.")
    return questions


def suggest_resources(task: str, goal: str, profile: dict):
    profile = profile or {}
    system = (
        "You suggest READING-FIRST learning resources (books, official documentation, articles, "
        "practice sets). You cannot browse, so do NOT give URLs. Give well-known titles you are "
        "confident exist, plus a good search phrase. Return ONLY JSON like "
        '{"resources": [{"title": "...", "kind": "book|documentation|article|practice", '
        '"why": "one sentence", "search_query": "..."}]} with 3 to 5 items. '
        f"Write in {_language(profile)}."
    )
    user = f"Overall goal: {goal}\nTask: {task}\nLearner level: {profile.get('level')}"
    
    data = extract_json(_complete(
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=0.4, json_mode=True))
    
    items = clean_resources(data.get("resources")) if data else []
    if not items:
        raise AIError("The AI could not suggest resources this time. Please try again.")
    return items


def weekly_summary(stats: dict, goal_title: str, tasks_done: int, tasks_total: int,
                   streak: int, profile: dict) -> str:
    system = (
        "You write a friendly weekly review for a learner in under 180 words: one win, one honest "
        "observation, and two specific suggestions for next week. Use ONLY the numbers given; never "
        f"invent data. Write in {_language(profile)}."
    )
    facts = {
        **(stats or {}),
        "goal": goal_title,
        "tasks_done": tasks_done,
        "tasks_total": tasks_total,
        "current_streak_days": streak,
    }
    return _complete([{"role": "system", "content": system},
                      {"role": "user", "content": json.dumps(facts, ensure_ascii=False)}],
                     temperature=0.5, max_tokens=600)


def answer_from_notes(question: str, excerpts, profile: dict) -> str:
    numbered = "\n\n".join(f"[{i}] ({e.get('filename', 'note')}) {e.get('text', '')}" for i, e in enumerate(excerpts or [], 1))
    system = (
        "Answer the question using ONLY the excerpts from the learner's own notes. If the excerpts "
        "do not contain the answer, say clearly that the notes do not cover it. Mention which "
        f"excerpt numbers you used, like [1]. Write in {_language(profile)}."
    )
    user = f"Excerpts:\n{numbered}\n\nQuestion: {question}"
    return _complete([{"role": "system", "content": system}, {"role": "user", "content": user}],
                     temperature=0.2)
