import asyncio
import logging
import os

from dotenv import load_dotenv

from services.quiz_payload import parse_stored_quiz
from services.quiz_service import create_new_quiz_round
from services.wiki_api import save_attempt

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CLI_USER_ID = 0


def _letters():
    return ["А", "Б", "В", "Г"]


async def main():
    if not os.getenv("API_KEY"):
        print("Задай API_KEY у .env для Gemini.")
        return

    print("Консоль: кожен цикл — новий раунд (3 питання, варіанти 1–4).")
    while True:
        print("Створюю раунд (стаття + питання)...")
        try:
            session = await create_new_quiz_round()
        except Exception as e:
            logger.exception("create_new_quiz_round")
            print(f"Помилка: {e}")
            await asyncio.sleep(3)
            continue

        title = session["title"]
        print(f"\n--- {title} ---")

        payload = parse_stored_quiz(session["quiz"])
        if not payload:
            print("Невалідний payload, наступна спроба...")
            continue

        quiz_id = session["quiz_id"]
        letters = _letters()
        picks = []
        try:
            for i, q in enumerate(payload["questions"]):
                print(f"\n{i + 1}. {q['text']}")
                for j, opt in enumerate(q["options"]):
                    print(f"   {letters[j]}) {opt}")
                raw = input("Варіант (1–4 або A–D): ").strip().upper()
                if raw in ("ВИХІД", "Q", "QUIT"):
                    print("Виходимо...")
                    return
                if raw in ("1", "А", "A"):
                    picks.append(0)
                elif raw in ("2", "Б", "B"):
                    picks.append(1)
                elif raw in ("3", "В", "C"):
                    picks.append(2)
                elif raw in ("4", "Г", "D"):
                    picks.append(3)
                else:
                    print("Невідомий варіант, зараховано як помилку.")
                    picks.append(-1)

            correct = [q["correct"] for q in payload["questions"]]
            score = sum(1 for i, p in enumerate(picks) if p == correct[i])
            print(f"\nРезультат: {score} з 3")
            await save_attempt(quiz_id, CLI_USER_ID, score)
            print(f"Збережено: quiz_id={quiz_id}, score={score}")

        except Exception as e:
            logger.exception("quiz loop")
            print(f"Помилка: {e}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nПрограму зупинено вручну.")
