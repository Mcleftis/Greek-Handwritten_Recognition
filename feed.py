import os, uuid, fitz, json, redis, psycopg2      # Εισαγωγή modules για filesystem, UUID, PDF επεξεργασία, JSON, Redis, Postgres

# --- Config ---
DB_URL = "postgresql://postgres:postgres@localhost:5433/postgres"   # Στοιχεία σύνδεσης στη βάση Postgres
REDIS_HOST = "localhost"                                            # Host του Redis server
REDIS_PORT = 6379                                                   # Port του Redis
QUEUE_NAME = "sketch_queue"                                         # Όνομα της ουράς εργασιών στο Redis
IMPORT_DIR = "imports"                                              # Φάκελος όπου βρίσκονται τα εισαγόμενα αρχεία
PDF_FILE = "orders.pdf"                                             # Το PDF που θα επεξεργαστεί

# 1. Ορισμός Redis στην αρχή (Global Scope)
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)  # Δημιουργία σύνδεσης με Redis

def get_db():
    return psycopg2.connect(DB_URL)                                  # Συνάρτηση που ανοίγει σύνδεση στη βάση Postgres

print("\n[Feeder] 🧹 Καθαρισμός Βάσης και Redis...")
try:
    # Καθαρισμός Postgres
    conn = get_db()                                                  # Άνοιγμα σύνδεσης στη βάση
    cur = conn.cursor()                                              # Δημιουργία cursor για queries
    cur.execute("TRUNCATE TABLE sketches;")                          # Διαγραφή όλων των εγγραφών από τον πίνακα sketches
    conn.commit()                                                    # Commit αλλαγών
    cur.close()                                                      # Κλείσιμο cursor
    conn.close()                                                     # Κλείσιμο σύνδεσης
    print("  [OK] Η βάση καθαρίστηκε.")
    
    # Καθαρισμός Redis
    r.delete(QUEUE_NAME)                                             # Διαγραφή της ουράς εργασιών
    r.delete("processed_images")                                     # Διαγραφή λίστας processed images
    print("  [OK] Η ουρά Redis καθαρίστηκε.")
except Exception as e:
    print(f"  [!] Προειδοποίηση: {e} (Συνεχίζω...)")                 # Αν υπάρξει σφάλμα, συνεχίζει χωρίς διακοπή

pdf_path = os.path.join(IMPORT_DIR, PDF_FILE)                        # Δημιουργία πλήρους path για το PDF
if not os.path.exists(pdf_path):                                     # Έλεγχος αν υπάρχει το PDF
    print(f"\n[ΣΦΑΛΜΑ] Το αρχείο {pdf_path} δεν υπάρχει!")
    exit(1)                                                          # Τερματισμός προγράμματος αν λείπει

print(f"[Feeder] 📖 Επεξεργασία: {pdf_path}")
doc = fitz.open(pdf_path)                                            # Άνοιγμα PDF με PyMuPDF

output_subdir = os.path.join(IMPORT_DIR, "current_order")            # Φάκελος όπου θα αποθηκευτούν οι εικόνες
os.makedirs(output_subdir, exist_ok=True)                            # Δημιουργία φακέλου αν δεν υπάρχει

print(f"[Feeder] ✂️ Σπάσιμο {len(doc)} σελίδων...")
for i in range(len(doc)):                                            # Loop για κάθε σελίδα του PDF
    page = doc.load_page(i)                                          # Φόρτωση σελίδας PDF
    pix = page.get_pixmap(dpi=300)                                   # Μετατροπή σε εικόνα υψηλής ανάλυσης
    img_name = f"page_{i+1}.jpg"                                     # Όνομα αρχείου εικόνας
    img_path = os.path.join(output_subdir, img_name)                 # Πλήρες path εικόνας
    pix.save(img_path)                                               # Αποθήκευση εικόνας στο δίσκο

    job = {
        "id": str(uuid.uuid4()),                                     # Μοναδικό ID εργασίας
        "customer_name": "DefaultPelatis",                           # Όνομα πελάτη (placeholder)
        "img_path": img_path,                                        # Τοπικό path εικόνας
        "img_url": f"/imports/current_order/{img_name}"              # URL για χρήση από API/UI
    }
    
    # Τώρα το 'r' είναι εγγυημένα ορισμένο
    r.rpush(QUEUE_NAME, json.dumps(job))                             # Προσθήκη της εργασίας στην ουρά Redis

print(f"\n[Feeder] ✅ ΕΠΙΤΥΧΙΑ! {len(doc)} σελίδες έτοιμες για OCR.")  # Τελικό μήνυμα επιτυχίας
