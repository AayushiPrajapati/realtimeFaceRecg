import cv2
import pickle
import face_recognition
import sqlite3
from datetime import datetime,timedelta
import os
import io
import time
import signal
import sys

from detector import detect_faces, draw_boxes

class FaceRecognizer:
    def __init__(self):
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
        # Check if encodings file exists
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
        # Encode frame as PNG in memory and return bytes
        try:
            success, encoded_image = cv2.imencode('.png', frame)
            if not success:
                raise ValueError("Could not encode frame")
            return encoded_image.tobytes()
        except Exception as e:
            print(f"[ERROR] Failed to convert frame to bytes: {e}")
            # Create a small placeholder image instead
            blank = np.zeros((100, 100, 3), np.uint8)
            success, encoded_image = cv2.imencode('.png', blank)
            return encoded_image.tobytes()

    def signal_handler(self, sig, frame):
        print("[INFO] Shutting down gracefully...")
        if self.cap is not None:
            self.cap.release()
        cv2.destroyAllWindows()
        self.conn.close()
        sys.exit(0)

    def run(self, max_frames=None):
        print("[INFO] Starting face recognition...")
        
        # Make sure encodings are loaded
        if len(self.data["encodings"]) == 0:
            print("[ERROR] No face encodings loaded. Please run training first.")
            return False
        
        # Initialize video capture
        try:
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                print("[ERROR] Could not open video capture device")
                print("[INFO] Make sure your webcam is connected and not in use by another application")
                return False
        except Exception as e:
            print(f"[ERROR] Failed to initialize video capture: {e}")
            return False
            
        frames_processed = 0
        
        try:
            while max_frames is None or frames_processed < max_frames:
                ret, frame = self.cap.read()
                if not ret:
                    print("[ERROR] Failed to capture frame")
                    break

                face_locations, face_encodings = detect_faces(frame)
                names = []

                for encoding in face_encodings:
                    matches = face_recognition.compare_faces(self.data["encodings"], encoding, tolerance=0.5)
                    name = "Unseen"
                    if True in matches:
                        idx = matches.index(True)
                        raw_name = self.data["names"][idx]
                        name = self.label_map.get(raw_name, raw_name)

                    from zoneinfo import ZoneInfo
                    timestamp = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M:%S")

                    # Convert frame to bytes for BLOB storage
                    frame_bytes = self.frame_to_bytes(frame)

                    # Insert into DB: name, timestamp, frame blob
                    try:
                        self.cursor.execute(
                            'INSERT INTO face_log (name, timestamp, frame) VALUES (?, ?, ?)',
                            (name, timestamp, frame_bytes)
                        )
                        self.conn.commit()
                    except Exception as e:
                        print(f"[ERROR] Failed to insert into database: {e}")

                    names.append(name)

                # Draw bounding boxes and names on the frame
                display_frame = draw_boxes(frame.copy(), face_locations, names)
                cv2.imshow("Face Recognition", display_frame)

                # Exit loop if 'q' pressed
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    break
                    
                frames_processed += 1
                
            return True
        except Exception as e:
            print(f"[ERROR] Exception in recognition loop: {e}")
            return False
        finally:
            if self.cap is not None:
                self.cap.release()
            cv2.destroyAllWindows()
            print(f"[INFO] Recognition stopped after processing {frames_processed} frames")

def main():
    import numpy as np  # Add missing import
    recognizer = FaceRecognizer()
    success = recognizer.run()
    if not success:
        sys.exit(1)  # Exit with error code on failure

if __name__ == "__main__":
    main()