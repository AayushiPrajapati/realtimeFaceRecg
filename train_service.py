import face_recognition
import os
import pickle
import numpy as np
from collections import Counter
from datetime import datetime
import time
import sys
import re
import threading

from flask import Flask
from prometheus_client import make_wsgi_app, Counter as PromCounter, Gauge
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from werkzeug.serving import run_simple

# Prometheus metrics
images_processed = PromCounter('images_processed_total', 'Total number of face images processed')
training_success = Gauge('training_success', 'Training success status (1=success, 0=failure)')

app = Flask(__name__)
metrics_app = make_wsgi_app()

# Combine Flask and Prometheus WSGI apps
application = DispatcherMiddleware(app.wsgi_app, {
    '/metrics': metrics_app
})

def extract_label_from_dirname(dirname):
    match = re.match(r'^(\d+)', dirname)
    if match:
        return match.group(1)
    return None

def train():
    known_encodings = []
    known_names = []

    data_dir = "/app/data"
    output_dir = "/app/models"

    os.makedirs(output_dir, exist_ok=True)
    total_images = 0

    print("[INFO] Starting training process...")

    if not os.path.exists(data_dir):
        print(f"[ERROR] Data directory {data_dir} does not exist!")
        training_success.set(0)
        return False

    person_dirs = []
    for dirname in os.listdir(data_dir):
        person_dir = os.path.join(data_dir, dirname)
        if os.path.isdir(person_dir):
            label = extract_label_from_dirname(dirname)
            if label:
                person_dirs.append((label, person_dir))

    if not person_dirs:
        print(f"[ERROR] No valid person directories found in {data_dir}!")
        print("[INFO] Please create subdirectories for each person (e.g., data/1/, data/2/)")
        training_success.set(0)
        return False

    for label, person_dir in person_dirs:
        print(f"[INFO] Processing label '{label}'...")
        image_files = [f for f in os.listdir(person_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]

        if not image_files:
            print(f"[WARNING] No image files found in {person_dir}")
            continue

        for img_name in image_files:
            path = os.path.join(person_dir, img_name)
            try:
                print(f"[DEBUG] Processing image {img_name}")
                image = face_recognition.load_image_file(path)
                encs = face_recognition.face_encodings(image)
                if encs:
                    known_encodings.append(encs[0])
                    known_names.append(label)
                    total_images += 1
                    images_processed.inc()
                    print(f"[DEBUG] Encoded image {img_name}")
                else:
                    print(f"[WARNING] No faces found in image {img_name}")
            except Exception as e:
                print(f"[ERROR] Failed to process image {img_name}: {e}")

    if total_images == 0:
        print("[ERROR] No faces found in the dataset. Exiting training.")
        training_success.set(0)
        return False

    encodings_path = os.path.join(output_dir, "encodings.pkl")
    with open(encodings_path, "wb") as f:
        pickle.dump({"encodings": known_encodings, "names": known_names}, f)

    print(f"[INFO] Saved {encodings_path} with {total_images} images.")
    print(f"[INFO] Training complete on {total_images} images across {len(set(known_names))} classes.")

    class_counts = Counter(known_names)
    for label, count in class_counts.items():
        print(f"[INFO] Class '{label}': {count} images")

    training_success.set(1)
    return True

if __name__ == "__main__":
    # Start Prometheus metrics + Flask WSGI app on port 5000
    print("[INFO] Starting metrics server on http://0.0.0.0:5002/metrics")
    threading.Thread(target=lambda: run_simple('0.0.0.0', 5002,application), daemon=True).start()

    success = train()
    if not success:
        sys.exit(1)
