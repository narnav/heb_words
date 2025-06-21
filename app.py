import sqlite3
import numpy as np
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sentence_transformers import SentenceTransformer
from datetime import datetime
import os
import random
from fastapi import Form
from helper import get_all_words,get_random_word
from fastapi.staticfiles import StaticFiles
from build_DB import add_words

# Load model
model = SentenceTransformer('all-MiniLM-L6-v2')

# FastAPI app setup
app = FastAPI(title="Hebrew Word Similarity")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

currect=""
score =0

# Initialize DB for query history
def init_history_table():
    conn = sqlite3.connect("vocab.db")
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS query_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        query TEXT NOT NULL,
        timestamp TEXT NOT NULL
    )
    """)
    conn.commit()
    conn.close()

init_history_table()
# if you have a new word list or you want to refill DB (render delete db from time to time 
add_words()

# Helpers
def reverse_word(word: str) -> str:
    return word[::-1]

def cosine_similarity(vec1, vec2) -> float:
    return float(np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2)))

def find_similar_words(user_word: str, top_n: int = 4):
    global currect
    conn = sqlite3.connect("vocab.db")
    cursor = conn.cursor()
    # print(user_word)
    user_vec = model.encode(user_word)
    cursor.execute("SELECT word, definition, embedding FROM vocabulary")
    candidates = cursor.fetchall()

    similarities = []
    for word, definition, emb_blob in candidates:
        db_vec = np.frombuffer(emb_blob, dtype=np.float32)
        sim = cosine_similarity(user_vec, db_vec)
        similarities.append((word, definition, sim))

    conn.close()
# Sort to get the most similar
    similarities.sort(key=lambda x: x[2], reverse=True)
    # print(similarities[0])
    currect=similarities[0]
    # print(currect)
    # Get top N, then shuffle
    top_similar = similarities[:top_n]
    random.shuffle(top_similar)

    return top_similar

def save_query_to_history(query: str):
    conn = sqlite3.connect("vocab.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO query_history (query, timestamp) VALUES (?, ?)",
                   (query, datetime.now().isoformat()))
    conn.commit()
    conn.close()

# ROUTES

@app.get("/", response_class=HTMLResponse)
def form_get(request: Request):
    global score
    selected_word = get_random_word()
    save_query_to_history(selected_word)
    results = find_similar_words(selected_word)
    reversed_results = [(reverse_word(w), reverse_word(defn), round(sim, 2)) for w, defn, sim in results]
    
    return templates.TemplateResponse("form.html", {
        "request": request,
        "results": [(reverse_word(selected_word), reversed_results)],
        "currect":currect,
        "original_word": selected_word,
        "score":score
    })


def jinja_reverse(text: str) -> str:
    return text[::-1]

templates.env.filters["reverse"] = jinja_reverse

@app.post("/check/", response_class=HTMLResponse)
async def check_answer(
    request: Request,
    selected: str = Form(...),
    correct_answer: str = Form(...),
    original_word: str = Form(...)
):
    global score
    feedback = "✅ תשובה נכונה!" if selected == correct_answer else f"❌ טעות. המילה הכי דומה הייתה: {currect}"
    if selected == correct_answer:
        score+=10
    else:
        score-=10
    if score < 0 :
        score =0
    if score == 100:
        score = 0
        conn = sqlite3.connect("vocab.db")
        cursor = conn.cursor()
        cursor.execute("DELETE FROM query_history")
        conn.commit()
        conn.close()
        return templates.TemplateResponse("done.html",{"request": request})
    return templates.TemplateResponse("form.html", {
        "request": request,
        "feedback": feedback,
        "results": None,
        "original_word": original_word,
        "currect":currect,
        "score":score
    })


@app.post("/results/", response_class=HTMLResponse)
async def form_post(request: Request, selected_word: str = Form(...)):
    save_query_to_history(selected_word)
    results = find_similar_words(selected_word)
    reversed_results = [(reverse_word(w), reverse_word(defn), round(sim, 2)) for w, defn, sim in results]
    # print(currect)
    return templates.TemplateResponse("form.html", {
        "request": request,
        "results": [(reverse_word(selected_word), reversed_results)],
        "all_words": get_all_words(),
        "original_input": selected_word,
          "currect":currect
    })


@app.get("/clear_history/")
def clear_query_history(request: Request):
    global score
    score=0
    conn = sqlite3.connect("vocab.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM query_history")
    conn.commit()
    conn.close()
    return templates.TemplateResponse("form.html",{"request": request})
