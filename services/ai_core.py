import json
import logging
import os
import re
from typing import Any, Dict, Optional, Tuple

from dotenv import load_dotenv
import google.genai as genai

from services.quiz_payload import validate_quiz_payload
from services.rule_based_quiz import generate_rule_based_quiz

load_dotenv()

API = os.getenv("API_KEY")

client = genai.Client(api_key=API)


def _extract_json_object(text: str) -> Any:
    raw = (text or "").strip()
    if not raw:
        raise ValueError("порожня відповідь моделі")
    start = raw.index("{")
    end = raw.rindex("}") + 1
    return json.loads(raw[start:end])


async def generate_quiz_payload(page: str, title: str = "") -> Dict[str, list]:
    prompt = (
        "Ти — професійний укладач вікторин. Твоє завдання — створити цікавий та пізнавальний тест на основі наданої статті з Вікіпедії.\n"
        "Питання мають бути різноманітними: на знання фактів, дат, причинно-наслідкових зв'язків.\n\n"
        "Поверни ЛИШЕ один валідний JSON без markdown і без тексту навколо, формат:\n"
        '{"questions":[{"text":"<питання>","options":["варіант А","варіант Б","варіант В","варіант Г"],'
        '"correct":0}]}\n'
        "Вимоги:\n"
        "- рівно 3 об'єкти в масиві questions;\n"
        "- у кожного питання рівно 4 варіанти в options;\n"
        "- варіанти відповідей мають бути правдоподібними, але лише один правильний;\n"
        "- correct — індекс правильної відповіді: 0, 1, 2 або 3;\n"
        "- правильні відповіді мають чітко випливати з тексту статті;\n"
        "- мова вікторини — українська.\n\n"
        f"Текст статті:\n{page}"
    )

    last_err: Optional[Exception] = None
    for attempt in range(2):
        try:
            response = await client.aio.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt if attempt == 0 else prompt + "\n\nПопередня відповідь була невалідна. Виправ JSON.",
                config=genai.types.GenerateContentConfig(
                    temperature=0.8,
                ),
            )
            data = _extract_json_object(response.text)
            return validate_quiz_payload(data)
        except Exception as e:
            last_err = e
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                logger = logging.getLogger(__name__)
                logger.warning("AI Quota exhausted, using rule-based fallback algorithm")
                # Квота перевищена, повертаємо питання на основі правил
                return generate_rule_based_quiz(page, title)
                
    # Якщо всі спроби ШІ виявилися невдалими, використовуємо алгоритм на основі правил
    logger = logging.getLogger(__name__)
    logger.warning("AI failed to generate quiz, using rule-based fallback algorithm")
    return generate_rule_based_quiz(page, title)


_SCORE_RE = re.compile(r"\[ОЦІНКА:\s*(\d+)/3\]", re.I)


def _parse_score_payload(text: str) -> Tuple[str, Optional[int]]:
    raw = (text or "").strip()
    if not raw:
        return "Порожня відповідь моделі.", None

    try:
        start = raw.index("{")
        end = raw.rindex("}") + 1
        data = json.loads(raw[start:end])
        score = data.get("score")
        feedback = data.get("feedback")
        if isinstance(score, int) and 0 <= score <= 3:
            fb = feedback if isinstance(feedback, str) else raw
            return fb.strip() or raw, score
    except (ValueError, json.JSONDecodeError, TypeError):
        pass

    m = _SCORE_RE.search(raw)
    if m:
        score = int(m.group(1))
        score = max(0, min(3, score))
        return raw, score

    return raw, None


async def get_answers(page: str, quiz: str, answers: str) -> Tuple[str, Optional[int]]:
    prompt = (
        f"Ось стаття: {page}\n"
        f"Ось питання: {quiz}\n"
        f"Ось відповіді користувача: {answers}\n\n"
        "Перевір відповіді користувача. Поясни коротко, де він правий, а де помилився.\n"
        "У кінці поверни лише один JSON-об'єкт без markdown і без тексту навколо, формат:\n"
        '{"score": <ціле від 0 до 3>, "feedback": "<весь твій текст пояснення українською>"}\n'
        "Поле feedback має містити повне пояснення для людини; score — скільки з 3 відповідей правильні."
    )

    response = await client.aio.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt,
        config=genai.types.GenerateContentConfig(
            temperature=0.3,
        ),
    )
    return _parse_score_payload(response.text)
