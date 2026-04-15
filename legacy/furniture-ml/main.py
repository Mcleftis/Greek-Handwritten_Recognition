from fastapi import FastAPI, UploadFile
import tensorflow as tf
import numpy as np
from PIL import Image
import io
import os

app = FastAPI()

# Φόρτωση του μοντέλου (με ασφάλεια σε περίπτωση που λείπει το αρχείο)
MODEL_PATH = "furniture_model.h5"
if os.path.exists(MODEL_PATH):
    model = tf.keras.models.load_model(MODEL_PATH)
    print("✅ Το μοντέλο φορτώθηκε επιτυχώς!")
else:
    print(f"⚠️ ΠΡΟΣΟΧΗ: Το αρχείο {MODEL_PATH} δεν βρέθηκε. Πρέπει να εκπαιδεύσεις πρώτα το μοντέλο.")
    model = None

CLASS_NAMES = ["kitchens", "sofas", "wardrobes"]

@app.post("/predict")
async def predict(file: UploadFile):
    if model is None:
        return {"error": "Το μοντέλο AI δεν έχει φορτωθεί."}
        
    img = Image.open(io.BytesIO(await file.read())).resize((224, 224))
    arr = tf.expand_dims(tf.keras.utils.img_to_array(img), 0)
    predictions = model.predict(arr, verbose=0)
    idx = np.argmax(predictions[0])
    
    return {
        "label": CLASS_NAMES[idx],
        "confidence": float(predictions[0][idx])
    }
