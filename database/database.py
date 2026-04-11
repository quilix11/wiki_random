import os
import sqlite3
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
# Дозволяємо перевизначити шлях до БД через змінну оточення DB_PATH (зручно для Docker/Cloud)
DEFAULT_DB_PATH = str(_ROOT / "wiki_quiz.db")
DB_PATH = os.getenv("DATABASE_URL", DEFAULT_DB_PATH)


def init_db():
    # Створюємо папку для бази даних, якщо вона не існує
    db_dir = Path(DB_PATH).parent
    db_dir.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS quizzes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            page_text TEXT NOT NULL,
            quiz_text TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            quiz_id INTEGER NOT NULL REFERENCES quizzes(id) ON DELETE CASCADE,
            user_id INTEGER NOT NULL,
            score INTEGER NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        )
        """
    )

    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_attempts_quiz_id ON attempts(quiz_id)"
    )

    conn.commit()
    conn.close()


def reset_db_dev():
    """Повне очищення БД; лише для розробки."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = OFF")
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS attempts")
    cursor.execute("DROP TABLE IF EXISTS quizzes")
    cursor.execute("DROP TABLE IF EXISTS wiki_quiz")
    conn.commit()
    conn.close()
    init_db()


if __name__ == "__main__":
    init_db()
