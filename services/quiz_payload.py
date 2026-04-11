import json
from typing import Any, Dict, List, Optional


def validate_quiz_payload(data: Any) -> Dict[str, List[dict]]:
    if not isinstance(data, dict):
        raise ValueError("payload не об'єкт")
    qs = data.get("questions")
    if not isinstance(qs, list) or len(qs) != 3:
        raise ValueError("має бути рівно 3 питання")
    out: List[dict] = []
    for q in qs:
        if not isinstance(q, dict):
            raise ValueError("невалідне питання")
        text = q.get("text")
        options = q.get("options")
        correct = q.get("correct")
        if not isinstance(text, str) or not text.strip():
            raise ValueError("порожній текст питання")
        if not isinstance(options, list) or len(options) != 4:
            raise ValueError("має бути 4 варіанти")
        if not all(isinstance(o, str) and o.strip() for o in options):
            raise ValueError("невалідні варіанти")
        if not isinstance(correct, int) or correct not in (0, 1, 2, 3):
            raise ValueError("correct має бути 0..3")
        out.append(
            {
                "text": text.strip(),
                "options": [o.strip() for o in options],
                "correct": correct,
            }
        )
    return {"questions": out}


def parse_stored_quiz(raw: Optional[str]) -> Optional[Dict[str, List[dict]]]:
    if not raw or not str(raw).strip():
        return None
    try:
        data = json.loads(raw)
        return validate_quiz_payload(data)
    except (json.JSONDecodeError, ValueError):
        return None


def payload_to_json_str(payload: Dict[str, List[dict]]) -> str:
    validate_quiz_payload(payload)
    return json.dumps(payload, ensure_ascii=False)
