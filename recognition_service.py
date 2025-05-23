import cv2
import pickle
import face_recognition
import sqlite3
from datetime import datetime
import os
import io
import time
import signal
import sys
from flask import Flask
from prometheus_client import make_wsgi_app
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from werkzeug.serving import run_simple
import numpy as np
from prometheus_client import start_http_server, Counter, Summary  # METRIC: Import Prometheus client

# Set OpenCV to use GTK backend
os.environ['OPENCV_VIDEOIO_BACKEND'] = 'v4l2'
os.environ['OPENCV_VIDEOIO_PRIORITY_MSMF'] = '0'

# METRIC: Define Prometheus metrics
FRAMES_PROCESSED = Counter('face_frames_processed_total', 'Total frames processed')
RECOGNIZED_FACES = Counter('recognized_faces_total', 'Total recognized faces')
UNKNOWN_FACES = Counter('unknown_faces_total', 'Total unknown faces')
FRAME_PROCESSING_TIME = Summary('face_frame_processing_seconds', 'Time spent processing a frame')

from detector import detect_faces, draw_boxes

class FaceRecognizer:
    def __init__(self):
        start_http_server(8000)
        print("[METRICS] Prometheus metrics server started at http://localhost:8000")

        # Map folder labels to actual names
        self.label_map = {
            "1": "Subha",
            "2": "Ayushi"
        }

        self.models_dir = "/app/models"
        self.db_dir = "/app/db"
        
        # Ensure directories exist
        os.makedirs(self.db_dir, exist_ok=True)
        
        self.db_path = os.path.join(self.db_dir, "face_log.db")
        self.encodings_path = os.path.join(self.models_dir, "encodings.pkl")
        
        # Initialize SQLite DB connection and create table if not exists
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS face_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            frame BLOB NOT NULL
        )
        ''')
        self.conn.commit()
        
        # Load known face encodings and labels
        self.load_encodings()
        
        # Initialize video capture
        self.cap = None
        
        # Set up signal handling for graceful exit
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

    def load_encodings(self):
        if not os.path.exists(self.encodings_path):
            print(f"[ERROR] Encodings file not found at {self.encodings_path}")
            print("[INFO] Please run training first")
            self.data = {"encodings": [], "names": []}
            return False
            
        try:
            with open(self.encodings_path, "rb") as f:
                self.data = pickle.load(f)
            print(f"[INFO] Loaded {len(self.data['encodings'])} face encodings")
            return True
        except Exception as e:
            print(f"[ERROR] Failed to load encodings: {e}")
            self.data = {"encodings": [], "names": []}
            return False

    def frame_to_bytes(self, frame):
        try:
            success, encoded_image = cv2.imencode('.png', frame)
            if not success:
                raise ValueError("Could not encode frame")
            return encoded_image.tobytes()
        except Exception as e:
            print(f"[ERROR] Failed to convert frame to bytes: {e}")
            blank = np.zeros((100, 100, 3), np.uint8)
            success, encoded_image = cv2.imencode('.png', blank)
            return encoded_image.tobytes()

    def signal_handler(self, sig, frame):
        print("[INFO] Shutting down gracefully...")
        if self.cap is not None:
            self.cap.release()
        self.conn.close()
        sys.exit(0)

    def run(self, max_frames=None):
        print("[INFO] Starting face recognition...")
        print(f"[DEBUG] DISPLAY: {os.environ.get('DISPLAY')}")
        print(f"[DEBUG] QT_QPA_PLATFORM: {os.environ.get('QT_QPA_PLATFORM')}")
        print(f"[DEBUG] OPENCV_VIDEOIO_BACKEND: {os.environ.get('OPENCV_VIDEOIO_BACKEND')}")

        if len(self.data["encodings"]) == 0:
            print("[ERROR] No face encodings loaded. Please run training first.")
            return False

        try:
            print("[DEBUG] Attempting to open video capture device...")
            self.cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
            if not self.cap.isOpened():
                print("[ERROR] Could not open video capture device")
                print("[INFO] Ensure webcam is connected and available")
                return False

            width = self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)
            height = self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
            fps = self.cap.get(cv2.CAP_PROP_FPS)
            print(f"[DEBUG] Camera - Width: {width}, Height: {height}, FPS: {fps}")

        except Exception as e:
            print(f"[ERROR] Failed to initialize video capture: {e}")
            return False

        frames_processed = 0

        try:
            print("[DEBUG] Starting recognition loop...")
            while max_frames is None or frames_processed < max_frames:
                ret, frame = self.cap.read()
                if not ret:
                    print("[ERROR] Failed to capture frame")
                    break

                print(f"[DEBUG] Frame captured - Shape: {frame.shape}")
                face_locations, face_encodings = detect_faces(frame)
                names = []

                for encoding in face_encodings:
                    matches = face_recognition.compare_faces(self.data["encodings"], encoding, tolerance=0.5)
                    name = "Unseen"
                    if True in matches:
                        idx = matches.index(True)
                        raw_name = self.data["names"][idx]
                        name = self.label_map.get(raw_name, raw_name)
                        print(f"[INFO] Recognized: {name}")

                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    frame_bytes = self.frame_to_bytes(frame)

                    try:
                        self.cursor.execute(
                            'INSERT INTO face_log (name, timestamp, frame) VALUES (?, ?, ?)',
                            (name, timestamp, frame_bytes)
                        )
                        self.conn.commit()
                    except Exception as e:
                        print(f"[ERROR] Failed to insert into database: {e}")

                    names.append(name)

                for (top, right, bottom, left), name in zip(face_locations, names):
                    cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
                    cv2.putText(frame, name, (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 0), 2)

                cv2.namedWindow('Face Recognition', cv2.WINDOW_NORMAL)
                cv2.imshow('Face Recognition', frame)
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    print("[INFO] Quit key pressed")
                    break

                frames_processed += 1
                FRAMES_PROCESSED.inc()
                if "Unseen" in names:
                    UNKNOWN_FACES.inc()
                else:
                    RECOGNIZED_FACES.inc()

                if frames_processed % 10 == 0:
                    print(f"[DEBUG] Processed {frames_processed} frames")

            return True
        except Exception as e:
            print(f"[ERROR] Exception in recognition loop: {e}")
            return False
        finally:
            if self.cap is not None:
                self.cap.release()
            cv2.destroyAllWindows()
            print(f"[INFO] Recognition stopped after {frames_processed} frames")

def start_metrics_server():
    print("[METRICS] Starting Prometheus metrics server at http://0.0.0.0:5002/metrics")
    flask_app = Flask(__name__)
    application = DispatcherMiddleware(flask_app, {
        '/metrics': make_wsgi_app()
    })
    run_simple("0.0.0.0", 5002, application)

if __name__ == "__main__":
    import threading
    # Start Prometheus Flask metrics server (optional)
    threading.Thread(target=start_metrics_server, daemon=True).start()

    # Start face recognition
    recognizer = FaceRecognizer()
    recognizer.run()
