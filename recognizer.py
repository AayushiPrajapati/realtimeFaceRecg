import cv2
import pickle
import face_recognition
import sqlite3
from datetime import datetime
import os
import sys
import signal
import logging
import numpy as np  # Ensure numpy imported

from detector import detect_faces, draw_boxes

# Setup logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

class FaceRecognizer:
    def __init__(self):
        self.label_map = {
            "1": "Subha",
            "2": "Ayushi"
        }
        
        self.models_dir = "/app/models"
        self.db_dir = "/app/db"
        os.makedirs(self.db_dir, exist_ok=True)
        
        self.db_path = os.path.join(self.db_dir, "face_log.db")
        self.encodings_path = os.path.join(self.models_dir, "encodings.pkl")
        
        # Initialize DB
        try:
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
            logging.info(f"Database initialized at {self.db_path}")
        except Exception as e:
            logging.error(f"Failed to initialize database: {e}")
            sys.exit(1)
        
        self.load_encodings()
        self.cap = None
        
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

    def load_encodings(self):
        if not os.path.exists(self.encodings_path):
            logging.error(f"Encodings file not found at {self.encodings_path}")
            logging.info("Please run training first")
            self.data = {"encodings": [], "names": []}
            return False
        
        try:
            with open(self.encodings_path, "rb") as f:
                self.data = pickle.load(f)
            logging.info(f"Loaded {len(self.data['encodings'])} face encodings")
            return True
        except Exception as e:
            logging.error(f"Failed to load encodings: {e}")
            self.data = {"encodings": [], "names": []}
            return False

    def frame_to_bytes(self, frame):
        try:
            success, encoded_image = cv2.imencode('.png', frame)
            if not success:
                raise ValueError("Could not encode frame")
            return encoded_image.tobytes()
        except Exception as e:
            logging.error(f"Failed to convert frame to bytes: {e}")
            blank = np.zeros((100, 100, 3), np.uint8)
            success, encoded_image = cv2.imencode('.png', blank)
            return encoded_image.tobytes()

    def signal_handler(self, sig, frame):
        logging.info("Shutting down gracefully...")
        if self.cap is not None:
            self.cap.release()
        cv2.destroyAllWindows()
        self.conn.close()
        sys.exit(0)

    def run(self, max_frames=None):
        logging.info("Starting face recognition...")
        
        if len(self.data["encodings"]) == 0:
            logging.error("No face encodings loaded. Please run training first.")
            return False
        
        try:
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                logging.error("Could not open video capture device")
                logging.info("Make sure your webcam is connected and not in use by another application")
                return False
        except Exception as e:
            logging.error(f"Failed to initialize video capture: {e}")
            return False
            
        frames_processed = 0
        
        try:
            while max_frames is None or frames_processed < max_frames:
                ret, frame = self.cap.read()
                if not ret:
                    logging.error("Failed to capture frame")
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

                    frame_bytes = self.frame_to_bytes(frame)

                    try:
                        self.cursor.execute(
                            'INSERT INTO face_log (name, timestamp, frame) VALUES (?, ?, ?)',
                            (name, timestamp, frame_bytes)
                        )
                        self.conn.commit()
                        logging.debug(f"Logged face: {name} at {timestamp}")
                    except Exception as e:
                        logging.error(f"Failed to insert into database: {e}")

                    names.append(name)

                display_frame = draw_boxes(frame.copy(), face_locations, names)
                cv2.imshow("Face Recognition", display_frame)

                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    logging.info("Received quit command 'q'")
                    break
                    
                frames_processed += 1
                
            return True
        except Exception as e:
            logging.error(f"Exception in recognition loop: {e}")
            return False
        finally:
            if self.cap is not None:
                self.cap.release()
            cv2.destroyAllWindows()
            logging.info(f"Recognition stopped after processing {frames_processed} frames")

def main():
    recognizer = FaceRecognizer()
    success = recognizer.run()
    if not success:
        logging.error("Face recognition exited with errors.")
        sys.exit(1)

if __name__ == "__main__":
    main()
