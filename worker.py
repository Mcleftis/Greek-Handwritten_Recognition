import os, json, requests, time, warnings, base64
import psycopg2
import redis
from pgvector.psycopg2 import register_vector
import logging

warnings.filterwarnings("ignore")
logging.getLogger().setLevel(logging.ERROR)

DB_URL        = "postgresql://postgres:postgres@localhost:5433/postgres"
REDIS_HOST    = "localhost"
REDIS_PORT    = 6379
QUEUE_NAME    = "sketch_queue"
PROCESSED_SET = "processed_images"
OLLAMA_URL    = "http://localhost:11434/api"

# SENIOR FIX 1: Καθαρό Αγγλικό Prompt για μέγιστη απόδοση του llava-phi3
PROMPT = (
    "You are an expert at reading messy Greek handwriting from carpentry sketches. "
    "Look at this image and extract the Customer Name (usually at the top) and the Furniture type. "
    "Respond ONLY with these 2 lines in Greek:\n"
    "- ΠΕΛΑΤΗΣ: [Name]\n"
    "- ΕΠΙΠΛΟ: [Furniture]\n"
    "If you cannot read something, write ΑΓΝΩΣΤΟ."
)

print("[Worker] llava-phi3 ready -- English prompt loaded.")

def get_db():
    conn = psycopg2.connect(DB_URL)
    register_vector(conn)
    return conn

def get_embedding(text):
    try:
        res = requests.post(f"{OLLAMA_URL}/embeddings",
                            json={"model": "nomic-embed-text", "prompt": text},
                            timeout=15)
        return res.json().get("embedding", [0.0] * 768)
    except:
        return [0.0] * 768

def analyze_image(img_path):
    start = time.time()
    try:
        with open(img_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")

        res = requests.post(f"{OLLAMA_URL}/generate", json={
            "model": "llava-phi3",
            "prompt": PROMPT,
            "images": [b64],
            "stream": False,
            "options": {
                "temperature": 0.0,
                "num_predict": 60
            }
        }, timeout=120)

        response = res.json().get("response", "").strip()
        elapsed = time.time() - start

        clean = [l for l in response.split("\n")
                 if l.startswith("- ΠΕΛΑΤΗΣ:") or l.startswith("- ΕΠΙΠΛΟ:")]
        if len(clean) >= 2:
            return "\n".join(clean[:2]), elapsed

        return response[:200], elapsed
    except Exception as e:
        print(f"  [Vision Error] {e}")
        return "", time.time() - start

def process(job, r_client):
    path = job["img_path"]

    if r_client.sadd(PROCESSED_SET, path) == 0:
        print(f"  [SKIP] {path}")
        return

    print(f"\n[Worker] Processing: {path}")

    desc, vision_time = analyze_image(path)
    print(f"  [Vision] {vision_time:.2f}s | {desc.replace(chr(10), ' ')[:100]}")

    if not desc:
        print("  [WARN] Empty result, skipping save.")
        return
        
    # SENIOR FIX 2: Εξάγουμε το όνομα από το κείμενο του AI για να μπει σωστά στη βάση!
    customer_name = "ΑΓΝΩΣΤΟ"
    for line in desc.split("\n"):
        if line.startswith("- ΠΕΛΑΤΗΣ:"):
            customer_name = line.replace("- ΠΕΛΑΤΗΣ:", "").strip()
            break

    emb = get_embedding(desc)

    conn = get_db()
    cur = conn.cursor()
    # Τώρα σώζουμε το customer_name που βρήκε το AI, όχι αυτό του job!
    cur.execute(
        "INSERT INTO sketches(id,customer_name,image_url,description,embedding) "
        "VALUES(%s,%s,%s,%s,%s) "
        "ON CONFLICT(id) DO UPDATE SET customer_name=EXCLUDED.customer_name, description=EXCLUDED.description, embedding=EXCLUDED.embedding",
        [job["id"], customer_name, job["img_url"], desc, emb])
    conn.commit()
    cur.close()
    conn.close()
    print(f"  [OK] Saved -> Πελάτης: {customer_name}")

if __name__ == "__main__":
    r_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    print(f"[Worker] Ready. Cache: {r_client.scard(PROCESSED_SET)} images.")
    while True:
        item = r_client.blpop(QUEUE_NAME, timeout=5)
        if item:
            try:
                process(json.loads(item[1]), r_client)
            except Exception as e:
                print(f"[ERROR] {e}")