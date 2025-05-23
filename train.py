# app/train.py

import face_recognition
import os
import pickle
import mlflow
import numpy as np
from collections import Counter
from datetime import datetime

def train():
    known_encodings = []
    known_names = []

    data_dir = "../data"
    total_images = 0

    print("[INFO] Starting training process...")

    with mlflow.start_run(run_name="train-" + datetime.now().strftime("%Y%m%d-%H%M%S")):
        for label in os.listdir(data_dir):
            person_dir = os.path.join(data_dir, label)
            if not os.path.isdir(person_dir):
                continue

            print(f"[INFO] Processing label '{label}'...")
            for img_name in os.listdir(person_dir):
                path = os.path.join(person_dir, img_name)
                image = face_recognition.load_image_file(path)
                encs = face_recognition.face_encodings(image)
                if encs:
                    known_encodings.append(encs[0])
                    known_names.append(label)
                    total_images += 1
                    print(f"[DEBUG] Encoded image {img_name}")
                else:
                    print(f"[WARNING] No faces found in image {img_name}")

        if total_images == 0:
            print("[ERROR] No faces found in the dataset. Exiting training.")
            return

        # Save encodings and names
        with open("encodings.pkl", "wb") as f:
            pickle.dump({"encodings": known_encodings, "names": known_names}, f)
        print(f"[INFO] Saved encodings.pkl with {total_images} images.")

        # Log model parameters and artifacts
        mlflow.log_param("classes", len(set(known_names)))
        mlflow.log_param("images", total_images)
        mlflow.log_artifact("encodings.pkl")

        # Compute and log encoding vector norm stats
        norms = [np.linalg.norm(enc) for enc in known_encodings]
        mlflow.log_metric("avg_encoding_vector_norm", float(np.mean(norms)))
        mlflow.log_metric("min_encoding_vector_norm", float(np.min(norms)))
        mlflow.log_metric("max_encoding_vector_norm", float(np.max(norms)))

        # Log per-class image counts
        class_counts = Counter(known_names)
        for label, count in class_counts.items():
            mlflow.log_metric(f"images_{label}", count)

    print(f"[INFO] Training complete on {total_images} images across {len(set(known_names))} classes.")

if __name__ == "__main__":
    train()

