import sqlite3

def init_db():
    conn = sqlite3.connect('database/wiki_quiz.db')
    cursor = conn.cursor()

    cursor.execute('DROP TABLE IF EXISTS wiki_quiz')

    cursor.execute('''
            CREATE TABLE IF NOT EXISTS wiki_quiz (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT UNIQUE,
            stats INTEGER
            )
        ''')

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()