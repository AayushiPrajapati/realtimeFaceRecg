import cv2
import pickle
import face_recognition
import sqlite3
from datetime import datetime
from detector import detect_faces, draw_boxes
import io

# Map folder labels to actual names
label_map = {
    "1": "Subha",
    "2": "Ayushi"
}

# Load known face encodings and labels
with open("encodings.pkl", "rb") as f:
    data = pickle.load(f)

# Initialize SQLite DB connection and create table if not exists
conn = sqlite3.connect('face_log.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''
CREATE TABLE IF NOT EXISTS face_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    frame BLOB NOT NULL
)
''')
conn.commit()

# Start video capture
cap = cv2.VideoCapture(0)

def frame_to_bytes(frame):
    # Encode frame as PNG in memory and return bytes
    success, encoded_image = cv2.imencode('.png', frame)
    if not success:
        raise ValueError("Could not encode frame")
    return encoded_image.tobytes()

try:
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        face_locations, face_encodings = detect_faces(frame)
        names = []

        for encoding in face_encodings:
            matches = face_recognition.compare_faces(data["encodings"], encoding, tolerance=0.5)
            name = "Unseen"
            if True in matches:
                idx = matches.index(True)
                raw_name = data["names"][idx]
                name = label_map.get(raw_name, raw_name)

            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Convert frame to bytes for BLOB storage
            frame_bytes = frame_to_bytes(frame)

            # Insert into DB: name, timestamp, frame blob
            cursor.execute(
                'INSERT INTO face_log (name, timestamp, frame) VALUES (?, ?, ?)',
                (name, timestamp, frame_bytes)
            )
            conn.commit()

            names.append(name)

        # Draw bounding boxes and names on the frame
        frame = draw_boxes(frame, face_locations, names)
        cv2.imshow("Face Recognition", frame)

        # Exit loop if 'q' pressed
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

finally:
    cap.release()
    cv2.destroyAllWindows()
    conn.close()
