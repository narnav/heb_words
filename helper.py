import sqlite3

def get_random_word():
    conn = sqlite3.connect("vocab.db")
    cursor = conn.cursor()
    cursor.execute("SELECT word FROM vocabulary ORDER BY RANDOM() LIMIT 1")
    word = cursor.fetchone()[0]
    conn.close()
    return word


def get_all_words():
    conn = sqlite3.connect("vocab.db")
    cursor = conn.cursor()
    cursor.execute("SELECT word FROM vocabulary ORDER BY word")
    all_words = [row[0] for row in cursor.fetchall()]
    conn.close()
    return all_words