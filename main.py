import psycopg2, requests
from fastapi import FastAPI
from pgvector.psycopg2 import register_vector

app = FastAPI()

DB_URL = "postgresql://postgres:postgres@localhost:5433/postgres"
OLLAMA_URL = "http://localhost:11434/api"

def get_db():
    conn = psycopg2.connect(DB_URL)
    register_vector(conn)
    return conn

def get_embedding(text):
    try:
        res = requests.post(
            f"{OLLAMA_URL}/embeddings",
            json={"model": "nomic-embed-text", "prompt": text},
            timeout=10,
        )
        return res.json().get("embedding", [0.0] * 768)
    except:
        return [0.0] * 768

@app.get("/api/rag/search")
async def search(query: str):
    emb = get_embedding(query)
    conn = get_db()
    cur = conn.cursor()

    # ✅ BUG FIX 1: Πρώτα text search (unaccent), μετά vector fallback
    cur.execute(
        """
        CREATE EXTENSION IF NOT EXISTS unaccent;
        SELECT description, image_url FROM sketches
        WHERE unaccent(description)   ILIKE unaccent(%s)
           OR unaccent(customer_name) ILIKE unaccent(%s)
        """,
        (f"%{query}%", f"%{query}%"),
    )
    rows = cur.fetchall()

    if not rows:
        cur.execute(
            "SELECT description, image_url FROM sketches "
            "ORDER BY embedding <=> %s::vector LIMIT 5",
            (emb,),
        )
        rows = cur.fetchall()

    cur.close()
    conn.close()

    # ✅ BUG FIX 2: Keys ταιριάζουν με αυτά που ζητάει το app.py (pageInfo, imageUrl)
    return [
        {"pageInfo": r[0], "imageUrl": r[1]}
        for r in rows
        if r[0] and "ΑΓΝΩΣΤΟ" not in r[0]
    ]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)